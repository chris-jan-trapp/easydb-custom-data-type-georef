import json
from datetime import datetime as d
import settings
import hashlib
import xml.etree.ElementTree as ET
import requests

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
GEO_SERVER_URL = "http://esx-80.gbv.de:8080/geoserver/wfs"


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_disk'})


def create_transaction(feature_type, feature):
    transaction = ET.Element("wfs:Transaction", **TRANSACTION_ATTRIBUTES)
    insert = ET.SubElement(transaction, "wfs:Insert")
    to_insert = ET.SubElement(insert, ":".join((TRANSACTION_ATTRIBUTES["xmlns:gbv"], feature_type)))
    text = ET.SubElement(to_insert, 'text')
    text.text = feature["text"]
    found_at = ET.SubElement(to_insert, "found_at")
    point_property_type = ET.SubElement(found_at, 'gml:PointPropertyType', srsName="EPSG:4326")
    pos = ET.SubElement(point_property_type, 'gml:pos')
    coordinates = feature['location']['mapPosition']['position']
    pos.text = str(coordinates['lat']) + ' ' + str(coordinates['lon'])

    return ET.tostring(transaction)


def dump_to_disk(easydb_context, easydb_info):
    payload = easydb_info['data']

    relevant_objects = filter(lambda o: settings.OBJECT_TYPE in o.keys(), payload)
    if not relevant_objects:
        return payload

    for relevant_object in relevant_objects:
        index = payload.index(relevant_object)
        unpacked = relevant_object[settings.OBJECT_TYPE]

        id = wfs(settings.OBJECT_TYPE, unpacked)
        payload[index][settings.OBJECT_TYPE][settings.RETURN] = id
    return payload


def pseudo_wfs(feature):
    hash = hashlib.sha224(json.dumps(feature)).hexdigest()[:12]
    try:
        with open('/var/tmp/plugin.json', 'r') as tmp:
            try:
                store = json.load(tmp)
            except:
                raise IOError
    except IOError:
        store = {}
    store[hash] = feature
    with open('/var/tmp/plugin.json', 'w') as tmp:
        json.dump(store, tmp, indent=2)
    return hash


def wfs(feature_type, feature):
    data = create_transaction(feature_type, feature)
    response = requests.post(GEO_SERVER_URL,
                             data=data,
                             headers={"Content-type": "text/xml"})

    if response.status_code == 200:
        transaction_result = ET.fromstring(response.content)
        feature_id = transaction_result.find("**/ogc:FeatureId", RESPONSE_NAMESPACE)
        return feature_id.get('fid')
