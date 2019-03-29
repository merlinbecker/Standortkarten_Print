#!/usr/bin/env python
# coding: utf-8

# Standortkarten Print Skript

# In[1]:


import sys
import os
import psycopg2
import time
import configparser
import requests
import json
import subprocess
from requests.auth import HTTPBasicAuth
import urllib2
from ipywidgets import FloatProgress
from IPython.display import display
import csv
from PIL import Image
import glob
import ftplib


# In[2]:


def process_exists(process_name):
    call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
    output = subprocess.check_output(call)
    last_line = output.strip().split('\r\n')[-1]
    return last_line.lower().startswith(process_name.lower())


# DatenbankServerFunktionen
# @todo: Auslagern in eine Klasse

# In[3]:


def openDataBaseServer(config):
    if not process_exists("postgres.exe"):
        print "Datenbank ist nicht offen!"
        processcall=config.get("postgres","bin_dir")+"/bin/postgres.exe "
        processcall+="-D "+config.get("postgres","db_dir")+" "
        processcall+="-p "+config.get("postgres","port")
        
        subprocess.Popen(processcall,shell=True)
        time.sleep(60)
        #@todo check if really open!
        print("Datenbank offen!")
def killDataBaseServer():
    p1=subprocess.Popen("TASKKILL /IM postgres.exe > NUL 2>&1",shell=True)
    p1.wait()
    print "Datenbankserver beendet"
def initDataBaseServer(config):
    if os.path.isdir(config.get("postgres","db_dir"))==False:
        print "Datenbank ist nicht eingerichtet, richte ein!"
        processcall=config.get("postgres","bin_dir")
        processcall+="/bin/initdb --locale=German_Germany.1252 --encoding=UTF8 "
        processcall+=config.get("postgres","db_dir")
        p1 = subprocess.Popen(processcall,shell=True)
        p1.wait()
        datenbank=openDataBaseServer(config)
        processcall=config.get("postgres","bin_dir")+"/bin/createuser.exe -s -d -w "+config.get("postgres","user")
        p1=subprocess.Popen(processcall,shell=True)
        p1.wait()
        print "Nutzer eingerichtet"


# In[4]:


def download_file(osm_url,dest):
    if config.get("general","proxy_https")!="":
        urllib2.install_opener(
            urllib2.build_opener(
                urllib2.ProxyHandler({'https': config.get("general","proxy_https")})
            )
        )
        
    file_name = "tempdata/"+osm_url.split('/')[-1]
    print "downloading: "+osm_url
    print "in progress"
    u = urllib2.urlopen(osm_url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192

    progressbar = FloatProgress(min=0, max=100) # instantiate the bar
    display(progressbar) # display the bar

    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break
        file_size_dl += len(buffer)
        f.write(buffer)
        progressbar.value=file_size_dl * 100. / file_size
    f.close()


# In[5]:


def checkDataBase(config,osm_url,databasename):
    initDataBaseServer(config)
    openDataBaseServer(config)

    #beispielhaft für Baden_Württemberg
    #DB ist OSM_BW_1
    try:
        conn = psycopg2.connect("dbname='"+databasename+"' user='"
                                +config.get("postgres","user")
                                +"' host='"+config.get("postgres","host")
                                +"' password='"+config.get("postgres","password")+"'")
        print "Datenbank existiert"
        #todo: hier noch checken, ob entsprechende Tabellen wirklich existieren
        conn.close()
    except:
        print "Datenbank existiert nicht!"
        #download osm data if not existent
        if not os.path.exists("tempdata"):
            os.makedirs("tempdata")
        
        #create database
        processcall=config.get("postgres","bin_dir")
        processcall+="/bin/psql -w -U "+config.get("postgres","user")
        processcall+=" -p "+config.get("postgres","port")
        processcall+=" -d postgres -c \"CREATE DATABASE "+databasename+"\""

        print processcall
        p1 = subprocess.Popen(processcall,shell=True)
        p1.wait()

        processcall=config.get("postgres","bin_dir")
        processcall+="/bin/psql -w -U "+config.get("postgres","user")
        processcall+=" -d \""+databasename+"\""
        processcall+=" -c \"CREATE EXTENSION postgis;\""
        p1 = subprocess.Popen(processcall,shell=True)
        p1.wait()

        processcall=config.get("postgres","bin_dir")
        processcall+="/bin/psql -w -U "+config.get("postgres","user")
        processcall+=" -d \""+databasename+"\""
        processcall+=" -c \"CREATE EXTENSION postgis_sfcgal;\""
        p1 = subprocess.Popen(processcall,shell=True)
        p1.wait()

        processcall=config.get("postgres","bin_dir")
        processcall+="/bin/psql -w -U "+config.get("postgres","user")
        processcall+=" -d \""+databasename+"\""
        processcall+=" -c \"CREATE EXTENSION postgis_topology;\""
        p1 = subprocess.Popen(processcall,shell=True)
        p1.wait()

        processcall=config.get("postgres","bin_dir")
        processcall+="/bin/psql -w -U "+config.get("postgres","user")
        processcall+=" -d \""+databasename+"\""
        processcall+=" -c \"CREATE EXTENSION hstore;\""
        p1 = subprocess.Popen(processcall,shell=True)
        p1.wait()
        
        #update 05.02.2019 
        #multiple osm_urls possible, divided by semicolon
        osm_urls=osm_url.split(";")
        count=1
        for osm_url in osm_urls:
            if not os.path.isfile("tempdata/"+os.path.basename(osm_url)):
                print "downloading OSM file"
                download_file(osm_url,"tempdata/"+os.path.basename(osm_url))
                print "Download abgeschlossen"
            #import data
            processcall=config.get("osm2pgsql","bin_path")
            processcall+=" -d "+databasename
            processcall+=" -S "+config.get("osm2pgsql","schema")
            processcall+=" -k --hstore-match-only -r pbf -s"
            processcall+=" -H "+config.get("postgres","host")
            processcall+=" -P "+config.get("postgres","port")
            processcall+=" -U "+config.get("postgres","user")
            processcall+=" -C "+config.get("osm2pgsql","cachesize")
            if count==1:
                processcall+=" -c "
            else:
                processcall+=" -a "
            processcall+="\""+os.path.abspath("tempdata/"+os.path.basename(osm_url))+"\""
            print processcall
            print "importiere OSM Daten in Datenbank, die kann lange Zeit dauern. Bitte Fenster offenlassen!"
            p1 = subprocess.Popen(processcall,shell=True)
            p1.wait()
            print "Import beendet"
            count+=1


# In[6]:


def renderBounds(kartenscale,m,mapnik,lon,lat,lon2,lat2,name):
    bbox = mapnik.Box2d(lon, lat, lon2, lat2)
    m.zoom_to_box(bbox)
    mapnik.render_to_file(m,name+".png","png",kartenscale)

def printBounds(lon,lat,lon2,lat2):
    print str(lon)+","+str(lat)+","+str(lon2)+","+str(lat2)


# hole Standorte

# In[7]:


def schreibeInfos(infos):
    out=""
    for info in infos:
       if len(info)>1:
        out+=info+"\n"
    return out


# In[8]:


def holeStandorte(config,bundesland,branche,dataset):
    csvfile='tempdata/standorte.csv'
    textfile='tempdata/uploads/text'+dataset+'_'+bundesland+'_'+branche+'.txt'
    
    f = open(csvfile,"wb")
    st_text_file=open(textfile,"wb")
    st_text=""

    csv_file = csv.writer(f, quotechar='"', quoting=csv.QUOTE_ALL)
    r=requests.post(config.get("webservice","url"),
                    auth=HTTPBasicAuth(config.get("webservice","username"),config.get("webservice","password")),
                    data={"command":"fetchStandortData","suffix":dataset,"branche":branche,"bundesland":bundesland},
                    proxies={'https': config.get("general","proxy_https"),'http': config.get("general","proxy_https")}
                   )
    if r.status_code == 200:
        data=json.loads(r.text)
        count=0
        for standort in data['standorte']:
            if count==0:
                csv_file.writerow(standort.keys())
            csv_file.writerow(standort.values())
            st_text+="#"+str(standort['id'])+" "
            st_text+="("+getWerkeNachArt(standort['Art'])+")\n"
            st_text+=standort['Name1']+" "+standort['Name2']+" "+standort['Name3']+"\n"
            st_text+=standort['Strasse']+"\n"+standort['PLZStrasse']+" "+standort['Ort']+"\n"
            
            st_text+=schreibeInfos(
                [standort['Telefon'],
                 "Fax:"+standort['Telefax'],
                 standort['Email'],
                 standort['Internet'],
                 standort['FabrikantderAnlage'],
                 standort['LeistungderAnlage'],
                 standort['Zugabevorrichtung'],
                 standort['DurschnittlicheJahres'],
                 standort['SonstigeAngaben'],
                 standort['Mitgliedim'],
                 standort['MitgliedimLandesverband'],
                 standort['UeberwachtDurch'],
                 standort['ZertifiziertNach']])
            st_text+="\n"
            
            count+=1
    else:
        print "konnte Standorte nicht holen",r.status_code,r.text
    st_text_file.write(st_text)
    f.close()
    st_text_file.close()
    
    #update: nun auch Alphabetisch
    textfile_alpha='tempdata/uploads/text_alphabet'+dataset+'_'+bundesland+'_'+branche+'.txt'
    st_text_file=open(textfile_alpha,"wb")
    st_text=""
    r=requests.post(config.get("webservice","url"),
                    auth=HTTPBasicAuth(config.get("webservice","username"),config.get("webservice","password")),
                    data={"command":"fetchStandortData","sort_alphabetical":1,"suffix":dataset,"branche":branche,"bundesland":bundesland},
                    proxies={'https': config.get("general","proxy_https"),'http': config.get("general","proxy_https")}
                   )
    if r.status_code == 200:
        data=json.loads(r.text)
        for standort in data['standorte']:
            st_text+="#"+str(standort['id'])+" "
            st_text+="("+getWerkeNachArt(standort['Art'])+")\n"
            st_text+=standort['Name1']+" "+standort['Name2']+" "+standort['Name3']+"\n"
            st_text+=standort['Strasse']+"\n"+standort['PLZStrasse']+" "+standort['Ort']+"\n"
            st_text+=schreibeInfos(
                [standort['Telefon'],
                "Fax:"+standort['Telefax'],
                standort['Email'],
                standort['Internet'],
                standort['FabrikantderAnlage'],
                standort['LeistungderAnlage'],
                standort['Zugabevorrichtung'],
                standort['DurschnittlicheJahres'],
                standort['SonstigeAngaben'],
                standort['Mitgliedim'],
                standort['MitgliedimLandesverband'],
                standort['UeberwachtDurch'],
                standort['ZertifiziertNach']])
            st_text+="\n"
    else:
        print "konnte Standorte nicht holen",r.status_code,r.text
    st_text_file.write(st_text)
    st_text_file.close()
    
    print "Standort CSV und Text geschrieben"
    return os.path.abspath(csvfile),os.path.abspath(textfile)


# In[9]:


def getWerkeNachArt(werk):
    if werk=="HW":
        return "Hauptwerk"
    elif werk=="ZW":
        return "Zweigwerk"
    elif werk=="HZW":
        return "Haupt-/Zweigwerk"
    elif werk=="GH":
        return "Gebietshauptwerk"
    else:
        return "Hauptwerk"


# In[10]:


def getBrancheById(branche):
    branche=int(branche)
    if branche==1 or branche==7:
        return "Asphalt"
    elif branche==2 or branche==9:
        return "Baustoff-Recycling"
    elif branche==3:
        return "Kies und Sand"
    elif branche==4 or branche==8:
        return "Naturstein"
    elif branche==5 or branche==6:
        return "Transportbeton"


# In[11]:


def generateStyles(config,branche,bundesland,dataset):
    if not os.path.exists("tempdata/uploads") or not os.path.exists("tempdata"):
        os.makedirs("tempdata/uploads")
    
    databasename=config.get(bundesland,"db_name")
    osm_url=config.get(bundesland,"osm_url")
    bounds=config.get(bundesland,"bounds");
    iconGH=config.get(getBrancheById(branche),"iconGH")
    iconHZW=config.get(getBrancheById(branche),"iconHZW")
    iconZW=config.get(getBrancheById(branche),"iconZW")
    iconHW=config.get(getBrancheById(branche),"iconHW")
    standorte,textfile=holeStandorte(config,bundesland,branche,dataset)
    
    with open('layerdata/OSM_template.xml', 'r') as template_file:
      styledata = template_file.read()
    styledata=styledata.replace("$DATABASE",databasename)
    styledata=styledata.replace("$BOUNDSSHAPE",os.path.abspath("layerdata/"+bounds))
    styledata=styledata.replace("$PATH",os.path.abspath(os.path.dirname("tempdata/../")))
    styledata=styledata.replace("$ICON_GH",os.path.abspath("layerdata/"+iconGH))
    styledata=styledata.replace("$ICON_HZW",os.path.abspath("layerdata/"+iconHZW))
    styledata=styledata.replace("$ICON_ZW",os.path.abspath("layerdata/"+iconZW))
    styledata=styledata.replace("$ICON_HW",os.path.abspath("layerdata/"+iconHW))
    styledata=styledata.replace("$FILE_STANDORTE",os.path.abspath(standorte))

    outfile = open("tempdata/stylesheet.xml", "w")
    outfile.write(styledata)
    outfile.close()

    print "Stylefile written"  


# In[12]:


def checkAndClearFolder(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        for the_file in os.listdir(path):
            file_path = os.path.join(path, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                #elif os.path.isdir(file_path): shutil.rmtree(file_path)
            except Exception as e:
                print(e)


# In[13]:


def generateMap(config,dataset,bundesland,branche):
    
    checkDataBase(config,config.get(bundesland,"osm_url"),config.get(bundesland,"db_name"))
    openDataBaseServer(config)
    path_temp_files="tempdata/renderedFiles"
    checkAndClearFolder(path_temp_files)
    generateStyles(config,branche,bundesland,dataset)
    #import mapnik
    sys.path.append(config.get("mapnik","pythonPath")) 
    import mapnik
    kartenscale=6

    custom_fonts_dir = 'C:/Windows/Fonts/'
    mapnik.register_fonts(custom_fonts_dir)

    breitePx=1242
    hoehePx=1756

    teil_lon=8
    teil_lat=8

    minLon=int(config.get(bundesland,"minLon"))
    maxLon=int(config.get(bundesland,"maxLon"))
    minLat=int(config.get(bundesland,"minLat"))
    maxLat=int(config.get(bundesland,"maxLat"))

    stylesheet = "tempdata/stylesheet.xml"

    #search and replace the 
    print('Starte tile setup')

    m = mapnik.Map(breitePx,hoehePx)
    mapnik.load_map(m, stylesheet)
    m.background = mapnik.Color('white')
    #definiere die Spaltenbreite
    breiteLon=(maxLon-minLon)/teil_lon
    breiteLat=(maxLat-minLat)/teil_lat
    count=0

    startLat=minLat
    startLon=minLon

    for i in range(teil_lat):
        for i in range(teil_lon):
            #printBounds(startLat, startLon, (startLat+breiteLat), (startLon+breiteLon))
            renderBounds(kartenscale,m,mapnik,startLat, startLon, (startLat+breiteLat), (startLon+breiteLon),path_temp_files+"/"+str(count))
            startLat+=breiteLat
            count+=1
        startLat=minLat
        startLon+=breiteLon

    print "grosse Karte binished!"

    img = Image.new("RGB", (1242*8, 1756*8),(255, 255, 255, 0))
    breite,hoehe=img.size

    fileNames = sorted(glob.glob(path_temp_files+"/*.png"), key=lambda y: int(y.rsplit('\\', 2)[1].rsplit('.')[0]))

    count=0
    offset_x=0
    offset_y=hoehe
    for file in fileNames:
        count+=1
        imp_img = Image.open(file, 'r')
        img_w, img_h = imp_img.size
        offset = offset_x,offset_y-img_h
        #img.convert("CMYK")
        img.paste(imp_img, offset)
        offset_x+=img_w
        if count%8==0:
            offset_y-=img_h
            offset_x=0

    checkAndClearFolder(path_temp_files) 

    img.save('tempdata/uploads/din0'+dataset+'_'+bundesland+'_'+branche+'.png')
    print("saved!")

    size = 128, 128
    img.thumbnail(size,Image.ANTIALIAS)
    img.save('tempdata/uploads/preview'+dataset+'_'+bundesland+'_'+branche+'.png')
    
    #todo zoomstufen
    killDataBaseServer()
    


# In[14]:


def uploadFiles():
    session = ftplib.FTP(config.get("ftp","host"),config.get("ftp","user"),config.get("ftp","passwd"))
    print session.getwelcome()
    session.set_pasv(1)
    for datei in os.listdir("tempdata/uploads"):
        print datei
        d = open("tempdata/uploads/"+datei,'rb')
        session.storbinary("STOR "+datei,d,1)
        d.close()
        os.remove("tempdata/uploads/"+datei)
    session.quit()


# In[15]:


stdout = sys.stdout
reload(sys)
sys.setdefaultencoding("utf-8")
sys.stdout = stdout
#disable proxy for localhost
os.environ['NO_PROXY'] = '127.0.0.1'
config=configparser.ConfigParser()
try:
    config.read("printconfig.ini")
except:
    print "exception while reading config file"
print config.sections()


# In[16]:


if config.get("general","proxy_https")!="":
    urllib2.install_opener(
        urllib2.build_opener(
            urllib2.ProxyHandler({'http': config.get("general","proxy_https"),'https': config.get("general","proxy_https")})
        )
    )
print("fetching queue")
r=requests.post(config.get("webservice","url"),
                proxies={'https': config.get("general","proxy_https"),'http': config.get("general","proxy_https")},
                auth=HTTPBasicAuth(config.get("webservice","username"),config.get("webservice","password")),
                data={"command":"fetchAllPrintingQueue"},
               )
if r.status_code == 200:
    queue=json.loads(r.text)
    for job in queue:
        print job
        generateMap(config,job['dataset'],str(job['bundesland']),str(job['branche']))
        r=requests.post(config.get("webservice","url"),
                proxies={'http': config.get("general","proxy_https"),'https': config.get("general","proxy_https")},
                auth=HTTPBasicAuth(config.get("webservice","username"),config.get("webservice","password")),
                data={"command":"setPrintingDone","suffix":job['dataset'],"branche":job['branche'],"bundesland":job['bundesland']},
               )
        uploadFiles()
else:
    print "konnte Printqueue nicht holen",r.status_code,r.text
print "done"

