import json
from datetime import datetime as d


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_disk'})


def dump_to_disk(easydb_context, easydb_info):
    payload = dir(easydb_context)
    with open('/var/tmp/plugin.json', 'w') as tmp:

        tmp.write("\n" + str(d.utcnow()) + "\n" + "context:\n")
        json.dump(payload, tmp, indent=2)
        tmp.write("\ninfo:\n")
        json.dump(dir(easydb_info), tmp, indent=2)
    return payload
