import asyncio
import aiohttp
import json
import urllib3

# Disable "Insecure HTTP" errors if certs are not available
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Perm token for QMT3
token = "access-v1:KK0ofAYQCjZWKjpPjob/Fewwcc6GopsOhDBCw5kq5mEBAAAA9AEAAAAAAABiTQn7aUwFZl99lGUAAAAAsYXNOg=="
cluster_address = "qmt3.qumulotest.local"
config_save_file_location = "/Users/joe/Python_Projects/AllStop/"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

async def aiohttp_get(url, session):
    async with session.get(url, headers=headers, ssl=False) as response:
        return await response.json()

async def main():
    async with aiohttp.ClientSession() as session:
        # Get Cluster Name
        url = f"https://{cluster_address}/api/v1/cluster/settings"
        cluster_name = await aiohttp_get(url, session)

        # Get MT config
        url = f"https://{cluster_address}/api/v1/multitenancy/tenants/"
        tenants = await aiohttp_get(url, session)

        # Get SMB Share config:
        url = f"https://{cluster_address}/api/v3/smb/shares/?populate-trustee-names=true"
        smb_shares = await aiohttp_get(url, session)

        # Get NFS exports:
        url = f"https://{cluster_address}/api/v3/nfs/exports/"
        nfs_exports = await aiohttp_get(url, session)

        # Get S3 Config:
        url = f"https://{cluster_address}/api/v1/s3/settings"
        s3_config = await aiohttp_get(url, session)

        # Get FTP Config:
        url = f"https://{cluster_address}/api/v0/ftp/settings"
        ftp_config = await aiohttp_get(url, session)

    # Save working config to file "cluster_name_config_backup.json"
    config_json = [cluster_name, { "tenants":tenants['entries'] }, { "smb_shares": smb_shares['entries'] }, { "nfs_exports": nfs_exports['entries'] }, { "s3_config": s3_config }, { "ftp_config": ftp_config }]
    file_location = config_save_file_location + cluster_name["cluster_name"] + "_config_backup22.json"
    with open(file_location, 'w') as json_file:
        json.dump(config_json, json_file, indent=2)
    
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
        

# Async General Purpose API patch function
async def aiohttp_patch(url, api_json, session, method):
    async with session.patch(url, json=api_json, headers=headers, ssl=False) as response:
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
    url = f"https://{cluster_address}/api/v1/multitenancy/tenants/{key.get('id')}"
    await aiohttp_patch(url, restrict_json, session, method)

# Async Function to set NFS exports to Read-Only
async def set_nfs_to_read_only(key, session):
    method = f"NFS export on path {key.get('export_path')} to Read-Only:"
    restrict_json = {
    "restrictions": [
        { "host_restrictions": [],
        "read_only": True,
        "user_mapping": "NFS_MAP_NONE" } ] }
    url = f"https://{cluster_address}/api/v3/nfs/exports/{key.get('id')}"
    await aiohttp_patch(url, restrict_json, session, method)

# Async Function to set SMB Shares to Read-Only
async def set_smb_to_read_only(key, session):
    method = f"SMB Share {key.get('share_name')} on tenant id {key.get('tenant_id')} to Read-Only:"
    restrict_json = { "network_permissions": [
        { "type": "ALLOWED",
        "address_ranges": [],
        "rights": [ "READ" ] }]}
    url = f"https://{cluster_address}/api/v3/smb/shares/{key.get('id')}"
    await aiohttp_patch(url, restrict_json, session, method)


# Async Function to disable S3 service
async def stop_s3_service(session):
    method = f"Disable S3 Service:"
    restrict_json = {
    "enabled": False
    }
    url = f"https://{cluster_address}/api/v1/s3/settings"
    await aiohttp_patch(url, restrict_json, session, method)

# Async Function to disable FTP service
async def stop_ftp_service(session):
    method = f"Disable FTP Service:"
    restrict_json = {
    "enabled": False
    }
    url = f"https://{cluster_address}/api/v0/ftp/settings"
    await aiohttp_patch(url, restrict_json, session, method)

asyncio.run(main())
