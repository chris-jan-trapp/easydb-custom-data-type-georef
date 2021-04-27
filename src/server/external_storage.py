import json
from datetime import datetime as d
from . import settings
import hashlib

"""This is modelled after https://docs.easydb.de/en/technical/plugins/
section "Example (Server Callback)
"""


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_disk'})


def dump_to_disk(easydb_context, easydb_info):
    payload = easydb_info['data']

    relevant_objects = filter(lambda o: settings.OBJECT_TYPE in o.keys(), payload)
    if not relevant_objects:
        return payload

    for relevant_object in relevant_objects:
        index = payload.index(relevant_object)
        geometry = relevant_object[settings.GEOMETRY]
        attributes = dict([(attribute, relevant_object.get(attribute, None)) for attribute in settings.ATTRIBUTES])
        hash = pseudo_wfs({"geometry": geometry,
                           "attributes": attributes})
        payload[index][settings.RETURN] = hash


def pseudo_wfs(feature):
    hash = hashlib.sha224(json.dumps(feature)).hexdigest()[:12]
    with open('/var/tmp/plugin.json', 'r') as tmp:
        try:
            store = json.load(tmp)
        except IOError:
            store = {}
    store[hash] = feature
    with open('/var/tmp/plugin.json', 'w') as tmp:
        json.dump(store, indent=2)
    return hash
