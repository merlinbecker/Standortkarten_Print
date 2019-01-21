# Standortkarten_Print
A print based visualisation of geospatial data


requires a Mapnik installation  to run properly
install Mapnik and add the paths to the python scripts.

Lib Pfade
\\mapnik-v2.2.0\python\2.7\site-packages hinzufügen und 
\\mapnik-v2.2.0\lib

Bin Pfade
\\mapnik-v2.2.0\bin

Diese Pfade auch womöglich in die PATH Variable eintragen, noch vor C:\windows\

Datenquellen, die evtl. von Nutzen sind:
http://www.naturalearthdata.com : Shape- und Rasterdaten der Welt.
http://download.geofabrik.de/ : OSM Daten als Shape oder OSM Daten

Protokoll:
22.11.2017: 
- Mapnik installiert 
- https://github.com/mapnik/mapnik/wiki/WindowsInstallation
- https://github.com/mapnik/mapnik/wiki/GettingStartedInPython 

24.11.2017:
- Darstellung von OSM shp Dateien:
	gis.osm.places_a_free1.shp: fclass "region" oder "island" für boundaries
