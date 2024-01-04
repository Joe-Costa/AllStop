import asyncio
import aiohttp
import json
import configparser
import urllib3

# Disable "Insecure HTTP" errors if certs are not available
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def main():
    async def aiohttp_get(url, session):
        async with session.get(url, headers=HEADERS, ssl=False) as response:
            return await response.json()

    async def collect_and_stop():
        async with aiohttp.ClientSession() as session:
            # Get Cluster Name
            url = f"https://{CLUSTER_ADDRESS}/api/v1/cluster/settings"
            cluster_name = await aiohttp_get(url, session)

            # Get MT config
            url = f"https://{CLUSTER_ADDRESS}/api/v1/multitenancy/tenants/"
            tenants = await aiohttp_get(url, session)

            # Get SMB Share config:
            url = f"https://{CLUSTER_ADDRESS}/api/v3/smb/shares/?populate-trustee-names=true"
            smb_shares = await aiohttp_get(url, session)

            # Get NFS exports:
            url = f"https://{CLUSTER_ADDRESS}/api/v3/nfs/exports/"
            nfs_exports = await aiohttp_get(url, session)

            # Get S3 Config:
            url = f"https://{CLUSTER_ADDRESS}/api/v1/s3/settings"
            s3_config = await aiohttp_get(url, session)

            # Get FTP Config:
            url = f"https://{CLUSTER_ADDRESS}/api/v0/ftp/settings"
            ftp_config = await aiohttp_get(url, session)

        # Save working config to file "cluster_name_config_backup.json"
        config_json = [cluster_name, { "tenants":tenants['entries'] }, { "smb_shares": smb_shares['entries'] }, { "nfs_exports": nfs_exports['entries'] }, { "s3_config": s3_config }, { "ftp_config": ftp_config }]
        file_location = CONFIG_SAVE_FILE_LOCATION + cluster_name["cluster_name"] + "_config_backup.json"

        # Check to see if --stop has been already run - We do not want to do this back-to-back!
        if not open(file_location):
            print(f"Creating new config file at {file_location}")
            with open(file_location, 'w') as json_file:
                json.dump(config_json, json_file, indent=2)
        else:
            # Ask for confirmation before overwriting
            user_response = input(f"\n*** WARNING !!!! ****\nThe file '{file_location}' already exists!\nOverwriting this file could lead to the loss of your clusters original configuration!\nAre you sure you want to run --stop again? (yes/no):\n").lower()

            if user_response == 'yes':
                with open(file_location, 'w') as json_file:
                    json.dump(config_json, json_file, indent=2)
                print(f"The file '{file_location}' has been overwritten.")
            else:
                print(f"Operation canceled. The file '{file_location}' has not been overwritten.")
                exit()

        # Stop NFS and SMB on all tenants
        async with aiohttp.ClientSession() as session:
            stop_tasks = [stop_smb_nfs_per_tenant(key, session) for key in tenants['entries']]
            await asyncio.gather(*stop_tasks)

        # Stop S3 and FTP service
        async with aiohttp.ClientSession() as session:
            await stop_s3_service(session)
            await stop_ftp_service(session)
        
        # Set all NFS Exports to Read-Only
        async with aiohttp.ClientSession() as session:
            stop_tasks = [set_nfs_to_read_only(key, session) for key in nfs_exports['entries']]
            await asyncio.gather(*stop_tasks)

        # Set all SMB Shares to Read-Only
        async with aiohttp.ClientSession() as session:
            stop_tasks = [set_smb_to_read_only(key, session) for key in smb_shares['entries']]
            await asyncio.gather(*stop_tasks)
        
        print("** Returning SMB and NFS services to tenants **")

        # Return NFS and SMB service to any tenants who had it enabled previously
        async with aiohttp.ClientSession() as session:
            start_tasks = [start_smb_nfs_per_tenant(key, session) for key in tenants['entries']]
            await asyncio.gather(*start_tasks)
        
        # Tasks complete message.  Cluster should be now in Read-Only mode
        print(f"Cluster {cluster_name.get('cluster_name')} has been placed in Read-Only mode")
        

    # Async General Purpose API patch function
    async def aiohttp_patch(url, api_json, session, method):
        async with session.patch(url, json=api_json, headers=HEADERS, ssl=False) as response:
            if response.status == 200:
                print(f'{method} request successful')
            else:
                print(f'{method} request error: {response.status}')
                print(await response.text())  # Print the error message or response content


    # Function to disable NFS and SMB service on a tenant
    async def stop_smb_nfs_per_tenant(key, session):
        method = f"Disabling tenant {key.get('name')}:"
        restrict_json = {
            "nfs_enabled": False,
            "smb_enabled": False
        }
        url = f"https://{CLUSTER_ADDRESS}/api/v1/multitenancy/tenants/{key.get('id')}"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to set NFS exports to Read-Only
    async def set_nfs_to_read_only(key, session):
        method = f"NFS export on path {key.get('export_path')} to Read-Only:"
        restrict_json = {
        "restrictions": [
            { "host_restrictions": [],
            "read_only": True,
            "user_mapping": "NFS_MAP_NONE" } ] }
        url = f"https://{CLUSTER_ADDRESS}/api/v3/nfs/exports/{key.get('id')}"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to set SMB Shares to Read-Only
    async def set_smb_to_read_only(key, session):
        method = f"SMB Share {key.get('share_name')} on tenant id {key.get('tenant_id')} to Read-Only:"
        restrict_json = { "network_permissions": [
            { "type": "ALLOWED",
            "address_ranges": [],
            "rights": [ "READ" ] }]}
        url = f"https://{CLUSTER_ADDRESS}/api/v3/smb/shares/{key.get('id')}"
        await aiohttp_patch(url, restrict_json, session, method)


    # Async Function to disable S3 service
    async def stop_s3_service(session):
        method = f"Disable S3 Service:"
        restrict_json = {
        "enabled": False
        }
        url = f"https://{CLUSTER_ADDRESS}/api/v1/s3/settings"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to disable FTP service
    async def stop_ftp_service(session):
        method = f"Disable FTP Service:"
        restrict_json = {
        "enabled": False
        }
        url = f"https://{CLUSTER_ADDRESS}/api/v0/ftp/settings"
        await aiohttp_patch(url, restrict_json, session, method)

    # Function to re-enable tenant's SMB and NFS service
    async def start_smb_nfs_per_tenant(key, session):
        data = key
        services = [key.upper().replace("_ENABLED", "") for key, value in data.items() if key.endswith("_enabled") and value if key.startswith("nfs") or key.startswith("smb")]
        if services:
            services = (' and '.join(services))
            method = f"Re-enabling {services} on tenant {key.get('name')}"
            url = f"https://{CLUSTER_ADDRESS}/api/v1/multitenancy/tenants/{key.get('id')}"
            restrict_json = key
            await aiohttp_patch(url, restrict_json, session, method)
        else:
            print(f"Skipping tenant {key.get('name')}, tenant did not have SMB or NFS services enabled")


    asyncio.run(collect_and_stop())

if __name__ == "__main__":
   main()

