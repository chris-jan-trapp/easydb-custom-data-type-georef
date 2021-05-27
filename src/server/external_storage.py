import json
from datetime import datetime as d
import settings
import hashlib
import xml.etree.ElementTree as ET
import requests
import logging
import traceback

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
RESPONSE_NAMESPACE = {"wfs": "http://www.opengis.net/wfs",
                      "ogc":"http://www.opengis.net/ogc"
                      }
GEO_SERVER_URL = "http://geoserver:8080/geoserver/wfs"
#GEO_SERVER_URL = "http://esx-80.gbv.de:8080/geoserver/wfs"


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_wfs'})
    logging.basicConfig(filename="/var/tmp/plugin.log", level=logging.DEBUG)
    logging.info("Loaded plugin")


def create_transaction(feature_type, feature):
    logging.debug('building insert transaction')
    transaction = ET.Element("wfs:Transaction", **TRANSACTION_ATTRIBUTES)
    insert = ET.SubElement(transaction, "wfs:Insert")
    to_insert = ET.SubElement(insert, ":".join((TRANSACTION_ATTRIBUTES["xmlns:gbv"], feature_type)))
    text = ET.SubElement(to_insert, 'text')
    text.text = feature["text"]
    found_at = ET.SubElement(to_insert, "found_at")
    point_property_type = ET.SubElement(found_at, 'gml:PointPropertyType', srsName="EPSG:4326")
    pos = ET.SubElement(point_property_type, 'gml:pos')
    concept_uri = json.loads(feature['found_at']['conceptURI'])
    coordinates = concept_uri['geometry']['coordinates']
    pos.text = str(coordinates[0]) + ' ' + str(coordinates[1])

    return ET.tostring(transaction)


def update_transaction(feature_type, feature, feature_id):
    logging.debug('building update transaction')
    transaction = ET.Element("wfs:Transaction", **TRANSACTION_ATTRIBUTES)
    type_name = "gbv:" + feature_type
    update = ET.SubElement(transaction, "wfs:Update", typeName=type_name)
    populated_fields = filter(lambda k: k in feature.keys(), settings.ATTRIBUTES)
    logging.debug("fields: " + str(feature.keys()) + str(populated_fields))
    for field in populated_fields:
        property = ET.SubElement(update, "wfs:Property")
        name = ET.SubElement(property, "wfs:Name")
        name.text = field
        value = ET.SubElement(property, "wfs:Value")
        value.text = feature[field]
    selector = ET.SubElement(update, "ogc:Filter")
    ET.SubElement(selector, "ogc:FeatureId", fid=feature_id)
    return ET.tostring(transaction)


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
                logging.debug("Attempting POST")
                id = wfs(settings.OBJECT_TYPE, unpacked, requests.post)
                payload[index][settings.OBJECT_TYPE][settings.RETURN] = id
            else:
                logging.debug("Attempting PUT")
                wfs_id = get_wfs_id(settings.OBJECT_TYPE, unpacked['_id'], easydb_context)
                logging.debug("Got: " + str(wfs_id))
                data = update_transaction(settings.OBJECT_TYPE, unpacked, wfs_id)
                logging.debug(data)
                response = requests.put(GEO_SERVER_URL, data=data, headers={"Content-type": "text/xml"})

        return payload
    except Exception as e:
        logging.error(str(e))
        logging.error(traceback.format_exc(e))
        raise e


def wfs(feature_type, feature, method):
    data = create_transaction(feature_type, feature)
    logging.debug("Created XML: " + data)
    response = method(GEO_SERVER_URL,
                      data=data,
                      headers={"Content-type": "text/xml"})

    if response.status_code == 200:
        logging.debug("Received: " + response.content)
        transaction_result = ET.fromstring(response.content)
        feature_id = transaction_result.find("**/ogc:FeatureId", RESPONSE_NAMESPACE)
        return feature_id.get('fid')
    else:
        logging.debug("Request failed with: " + str(response.content))


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
    id = wfs(settings.OBJECT_TYPE, plate[settings.OBJECT_TYPE])
    print(id)
