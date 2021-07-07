import json
import settings
import logging
import traceback
import requests
from wfs_client import WFSClient
"""This is modelled after https://docs.easydb.de/en/technical/plugins/
section "Example (Server Callback)
"""

TRANSACTION_ATTRIBUTES = {"version": "1.1.0",
                          "service": "WFS",
                          "xmlns": "http://esx-80.gbv.de:8080/geoserver/gbv",
                          "xmlns:gbv": "gbv",
                          "xmlns:gml": "http://www.opengis.net/gml",
                          "xmlns:ogc": "http://www.opengis.net/ogc",
                          "xmlns:wfs": "http://www.opengis.net/wfs",
                          "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                          "xsi:schemaLocation": """http://esx-80.gbv.de:8080/geoserver/
                                                   http://www.opengis.net/wfs
                                                   ../wfs/1.1.0/WFS.xsd"""
                          }


#GEO_SERVER_URL = "http://esx-80.gbv.de:8080/geoserver/wfs"
WFS = WFSClient(settings.GEO_SERVER_URL,
                TRANSACTION_ATTRIBUTES,
                settings.OBJECT_TYPE,
                settings.ATTRIBUTES,
                settings.GEOMETRY)

SERVICER_URL = "servicer:5000"


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_wfs'})
    easydb_context.register_callback('db_pre_update', {'callback': 'redirect_to_servicer'})

    logging.basicConfig(filename="/var/tmp/plugin.log", level=logging.DEBUG)
    logging.info("Loaded plugin")


def redirect_to_servicer(easydb_context, easydb_info):
    session = easydb_context.get_session()
    logging.info("\n".join(["Redirecting:", str(session), str(easydb_info)]))
    response = requests.post("http://" + SERVICER_URL + "/dump",
                             json={'session': session, "info": easydb_info},
                             headers={'Content-type': 'application/json'})
    logging.info("Servicer says: " + str(response.content))
    return response.json()


def dump_to_wfs(easydb_context, easydb_info):
    try:
        payload = easydb_info['data']

        relevant_objects = filter(lambda o: settings.OBJECT_TYPE in o.keys(), payload)
        if not relevant_objects:
            return payload

        for relevant_object in relevant_objects:
            index = payload.index(relevant_object)
            unpacked = relevant_object[settings.OBJECT_TYPE]
            logging.debug('Handling relevant object: ' + settings.OBJECT_TYPE + str(unpacked))
            keys = unpacked.keys()
            has_geometry = settings.GEOMETRY in keys
            created = unpacked.get("_id") is None
            if created and has_geometry:
                logging.debug("Attempting CREATE")
                id = WFS.create_feature(unpacked)
                payload[index][settings.OBJECT_TYPE][settings.RETURN] = id
            else:
                logging.debug("Attempting UPDATE")
                wfs_id = get_wfs_id(settings.OBJECT_TYPE, unpacked['_id'], easydb_context)
                data = WFS.update_feature(unpacked, wfs_id)
                logging.debug(data)


        return payload
    except Exception as e:
        logging.error(str(e))
        logging.error(traceback.format_exc(e))
        raise e


def get_wfs_id(object_name, edb_id, context):
    sql = "select feature_id from " + object_name + ' where "id:pkey"=' + str(edb_id) + ";"
    logging.debug(sql)
    db_cursor = context.get_db_cursor()
    db_cursor.execute(sql)
    if db_cursor.rowcount:
        return db_cursor.fetchone()["feature_id"]


if __name__ == '__main__':
    plate_xml = """<?xml version="1.0"?>
         <wfs:Transaction version="1.1.0" service="WFS"
                               xmlns="http://esx-80.gbv.de:8080/geoserver/gbv"
                               xmlns:gbv="gbv"
                               xmlns:gml="http://www.opengis.net/gml"
                               xmlns:ogc="http://www.opengis.net/ogc"
                               xmlns:wfs="http://www.opengis.net/wfs"
                               xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                               xsi:schemaLocation="http://esx-80.gbv.de:8080/geoserver/
                               http://www.opengis.net/wfs ../wfs/1.1.0/WFS.xsd">
           <wfs:Insert>
             <gbv:teller>
               <text>Moinsen!</text>
               <found_at>
                 <gml:PointPropertyType srsName="EPSG:4326">
                   <gml:pos>-98.5485 24.2633</gml:pos> 
                 </gml:PointPropertyType>
               </found_at>
             </gbv:teller>
           </wfs:Insert>
         </wfs:Transaction>
         """
    plate_json = """{
    "_idx_in_objects": 1, 
    "teller": {
      "text": "Liebe!", 
      "_id": null, 
      "_version": 1, 
      "location": {
        "mapPosition": {
          "position": {
            "lat": 53.52725, 
            "lng": 10.02173
          }, 
          "iconColor": "#b8bfc4", 
          "iconName": "fa-map-marker"
        }, 
        "displayValue": {
          "de-DE": "Whatevs", 
          "en-US": ""
        }, 
        "_fulltext": {
          "text": "Whatevs", 
          "string": "Whatevs", 
          "l10ntext": {
            "de-DE": "Whatevs", 
            "en-US": ""
          }
        }
      }
    }, 
    "_mask": "_all_fields", 
    "_objecttype": "teller"
  }"""
    plate = json.loads(plate_json)