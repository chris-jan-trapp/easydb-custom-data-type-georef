import json
import settings
import logging
import traceback
import requests
from wfs_client import WFSClient
"""This is modelled after https://docs.easydb.de/en/technical/plugins/
section "Example (Server Callback)
"""

SERVICER_URL = "http://servicer:5000"

class ServicerClient:
    def __init__(self, url):
        if url.startswith('http'):
            self.url = url
        else:
            raise ValueError('Protocol information required in servicer url (e.g. "http:...")')
    
    def redirect(self, endpoint, easydb_context, easydb_info):
        session = easydb_context.get_session()
        data = easydb_info.get('data')
        try:
            logging.info("\n".join(["Redirecting:", endpoint, str(session), str(data)]))

            response = requests.post(self.url + endpoint,
                                    json={'session': session, "data": data},
                                    headers={'Content-type': 'application/json'})
            
            if response.ok:
                data = response.json()['data']
                logging.debug("Servicer returned data: " + json.dumps(data, indent=2))
            else:
                logging.error("Servicer failed with: " + str(response.content))  
        except Exception as exception:
            logging.error(str(exception))
        finally:
            return data

client = ServicerClient(SERVICER_URL)

def easydb_server_start(easydb_context):
    easydb_context.register_callback('db_pre_update', {'callback': 'submit_to_wfs'})
    # easydb_context.register_callback('db_pre_update', {'callback': 'redirect_to_servicer'})
    easydb_context.register_callback('db_post_update_one', {'callback': 'extract_shapefiles'})

    logging.basicConfig(filename="/var/tmp/plugin.log", level=logging.DEBUG)
    logging.info("Loaded plugin")



def submit_to_wfs(easydb_context, easydb_info):
    return client.redirect('/pre-update', easydb_context, easydb_info)

def extract_shapefiles(easydb_context, easydb_info):
    return client.redirect('/post-update', easydb_context, easydb_info)

def minimal_callback(easydb_context, easydb_info):
    try:
        # unpack payload and do stuff:
        info = easydb_info['data']
        logging.info('Got info: ' + str(info))
    except Exception as exception:
        logging.error(str(exception))
    finally:
        return info

