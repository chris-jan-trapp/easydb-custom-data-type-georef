import json


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_disk'})


def dump_to_disk(easydb_context, easydb_info):
    payload = dir(easydb_context)
    with open('/var/tmp/plugin.json', 'w') as tmp:
        json.dump(payload, tmp, indent=2)
    return payload
