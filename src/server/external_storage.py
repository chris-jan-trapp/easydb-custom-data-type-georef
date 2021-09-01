import json
import settings
import logging
import traceback
import requests
from wfs_client import WFSClient
"""This is modelled after https://docs.easydb.de/en/technical/plugins/
section "Example (Server Callback)
"""

SERVICER_URL = "servicer:5000"


def easydb_server_start(easydb_context):
    # easydb_context.register_callback('db_pre_update', {'callback': 'dump_to_wfs'})
    # easydb_context.register_callback('db_pre_update', {'callback': 'redirect_to_servicer'})
    easydb_context.register_callback('db_post_update_one', {'callback': 'minimal_callback'})

    logging.basicConfig(filename="/var/tmp/plugin.log", level=logging.DEBUG)
    logging.info("Loaded plugin")


def redirect_to_servicer(easydb_context, easydb_info):
    session = easydb_context.get_session()
    logging.info("\n".join(["Redirecting:", str(session), str(easydb_info)]))
    response = requests.post("http://" + SERVICER_URL + "/pre-update",
                             json={'session': session, "info": easydb_info},
                             headers={'Content-type': 'application/json'})
    logging.info("Servicer says: " + str(response.content))
    data = response.json()['data']
    logging.info("Servicer data: " + json.dumps(data, indent=2))
    return data

def catch_post_update(*args):
    logging.info("\n".join(["Post update:", str(args)]))
    return args


def minimal_callback(easydb_context, easydb_info):
    try:
        # unpack payload and do stuff:
        info = easydb_info['data']
        logging.info('Got info: ' + str(info))
    except Exception as exception:
        logging.error(str(exception))
    finally:
        return info

