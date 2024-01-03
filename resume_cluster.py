import json
import requests
import asyncio
import aiohttp
import configparser

# Load the config file
config = configparser.ConfigParser()
config.read('all_stop.conf')
CLUSTER_ADDRESS = config['CLUSTER']['CLUSTER_ADDRESS']
TOKEN = config['CLUSTER']['TOKEN']
CONFIG_SAVE_FILE_LOCATION = config['CLUSTER']['CONFIG_SAVE_FILE_LOCATION']

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

url = f"https://{CLUSTER_ADDRESS}/api/v1/cluster/settings"

# Load the pre-stop configuration of the cluster
cluster_name = requests.get(url, headers=HEADERS, verify=False).json()
cluster_name = cluster_name['cluster_name']
file_location = CONFIG_SAVE_FILE_LOCATION + cluster_name + ".json"
with open(file_location, 'r') as original_config:
    config_data = json.loads(original_config.read())
    tenant_info = config_data[1]['tenant_info']
    smb_shares = config_data[2]['smb_shares']
    nfs_exports = config_data[3]['nfs_exports']
    s3_config = config_data[4]['s3_config']
    ftp_config = config_data[5]['ftp_config']

# Async General Purpose API patch function
async def aiohttp_patch(url, api_json, session, method):
    async with session.patch(url, json=api_json, headers=HEADERS, ssl=False) as response:
        if response.status == 200:
            print(f'{method} request successful')
        else:
            print(f'{method} request error: {response.status}')
            print(await response.text())  # Print the error message or response content