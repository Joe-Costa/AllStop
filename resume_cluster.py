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
file_location = CONFIG_SAVE_FILE_LOCATION + cluster_name + "_config_backup.json"

def main():

    # Load the config subsections
    with open(file_location, 'r') as original_config:
        config_data = json.loads(original_config.read())
        tenant_info = config_data[1]['tenant_info']
        smb_shares = config_data[2]['smb_shares']
        nfs_exports = config_data[3]['nfs_exports']
        s3_config = config_data[4]['s3_config']
        ftp_config = config_data[5]['ftp_config']

    # This function runs all the async restore methods
    async def resume_service():

        # Restore Tenant Config
        async with aiohttp.ClientSession() as session:
            start_tasks = [restore_tenant(key, session) for key in tenant_info]
            await asyncio.gather(*start_tasks)

        # Restore SMB Config
        async with aiohttp.ClientSession() as session:
            start_tasks = [restore_smb(key, session) for key in smb_shares]
            await asyncio.gather(*start_tasks)

        # Restore NFS Config
        async with aiohttp.ClientSession() as session:
            start_tasks = [restore_nfs(key, session) for key in nfs_exports]
            await asyncio.gather(*start_tasks)

        # Restore S3 and FTP Config
        async with aiohttp.ClientSession() as session:
            await resume_s3_service(s3_config, session)
            await resume_ftp_service(ftp_config, session)
        
        print(f"Services have been restored on cluster {cluster_name}")

    # Async General Purpose API patch function
    async def aiohttp_patch(url, api_json, session, method):
        async with session.patch(url, json=api_json, headers=HEADERS, ssl=False) as response:
            if response.status == 200:
                print(f'{method} request successful')
            else:
                print(f'{method} request error: {response.status}')
                print(await response.text())  # Print the error message or response content

    # Function to re-enable NFS and SMB services on a tenant
    async def restore_tenant(key, session):
        method = f"Re-enabling services on tenant {key.get('name')}:"
        url = f"https://{CLUSTER_ADDRESS}/api/v1/multitenancy/tenants/{key.get('id')}"
        await aiohttp_patch(url, key, session, method)

    # Async Function to restore NFS exports
    async def restore_nfs(key, session):
        method = f"Restoring config of NFS export on path {key.get('export_path')}:"
        url = f"https://{CLUSTER_ADDRESS}/api/v3/nfs/exports/{key.get('id')}"
        await aiohttp_patch(url, key, session, method)
    
    # Async Function to restore SMB Shares
    async def restore_smb(key, session):
        method = f"Restoring config of SMB share {key.get('share_name')}:"
        url = f"https://{CLUSTER_ADDRESS}/api/v3/smb/shares/{key.get('id')}"
        await aiohttp_patch(url, key, session, method)

    # Async Function to re-enable FTP service
    async def resume_ftp_service(ftp_config, session):
        method = f"Re-Enable FTP Service:"
        url = f"https://{CLUSTER_ADDRESS}/api/v0/ftp/settings"
        await aiohttp_patch(url, ftp_config, session, method)

    # Async Function to re-enable FTP service
    async def resume_s3_service(ftp_config, session):
        method = f"Re-Enable S3 Service:"
        url = f"https://{CLUSTER_ADDRESS}/api/v1/s3/settings"
        await aiohttp_patch(url, s3_config, session, method)

    asyncio.run(resume_service())


if __name__ == "__main__":
   main()