import json
from datetime import datetime as d

"""This is modelled after https://docs.easydb.de/en/technical/plugins/
section "Example (Server Callback)
"""


def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_disk'})


def dump_to_disk(easydb_context, easydb_info):
    payload = easydb_info['data']
    with open('/var/tmp/plugin.json', 'w') as tmp:

        tmp.write("\n" + str(d.utcnow()) + "\n" + "context:\n")
        json.dump(dir(easydb_context), tmp, indent=2)
        tmp.write("\ninfo:\n")
        json.dump(dir(easydb_info), tmp, indent=2)
        tmp.write("\ninfo content:\n")
        for k, v in easydb_info.items():
            tmp.write(str(k) + ": " + str(v) + "\n")
        tmp.write("\n Identified payload:\n")
        json.dump(payload, tmp, indent=2)
    payload[0]["teller"]["text"] += " modified"
    return payload

