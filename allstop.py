#!/usr/bin/env python3
import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# This is a perm token for QQ
#token = "access-v1:/FJ0Jbbm+JxMYOOsLUudYdx8MFyl1J4HOfIf4yGz7EwBAAAA9AEAAAAAAAD4JmZoZ2PG4757lGUAAAAAr+fGDg=="

# Perm token for QMT3
token = "access-v1:KK0ofAYQCjZWKjpPjob/Fewwcc6GopsOhDBCw5kq5mEBAAAA9AEAAAAAAABiTQn7aUwFZl99lGUAAAAAsYXNOg=="
cluster_address = "qmt3.qumulotest.local"
config_save_file_location = "/Users/joe/Python_Projects/AllStop/"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Get Cluster Name
url = f"https://{cluster_address}/api/v1/cluster/settings"
cluster_name = requests.get(url, headers=headers, verify=False).json()

# Get MT config
url = f"https://{cluster_address}/api/v1/multitenancy/tenants/"
tenants = requests.get(url, headers=headers, verify=False).json()

#Get SMB Share config:
url = f"https://{cluster_address}/api/v3/smb/shares/?populate-trustee-names=true"
smb_shares = requests.get(url, headers=headers, verify=False).json()

# Get NFS exports:
url = f"https://{cluster_address}/api/v3/nfs/exports/"
nfs_exports = requests.get(url, headers=headers, verify=False).json()

# Get S3 Config:
url = f"https://{cluster_address}/api/v1/s3/settings"
s3_config = requests.get(url, headers=headers, verify=False).json()

# Get FTP Config:
url = f"https://{cluster_address}/api/v0/ftp/settings"
ftp_config = requests.get(url, headers=headers, verify=False).json()

# Save working config to file "cluster_name_config_backup.json"
config_json = [cluster_name, { "tenants":tenants['entries'] }, { "smb_shares": smb_shares['entries'] }, { "nfs_exports": nfs_exports['entries'] }, { "s3_config": s3_config }, { "ftp_config": ftp_config }]
file_location = config_save_file_location + cluster_name["cluster_name"] + "_config_backup.json"
with open(file_location, 'w') as json_file:
    json.dump(config_json, json_file, indent=2)

# This is the GP API calling function
def api_caller(url, api_json, method):
    response = requests.patch(url, json=api_json, headers=headers, verify=False)
    if response.status_code == 200:
        print(f'{method} request successful')
    else:
        print(f'{method} request error: {response.status_code}')
        print(response.text)  # Print the error message or response content
    return


# Stop SMB and NFS services on all Tenants
for key in tenants['entries']:
    method = f"Disabling tenant {key.get('name')}:"
    restrict_json = {
    "nfs_enabled": False,
    "smb_enabled": False
    }
    url = f"https://{cluster_address}/api/v1/multitenancy/tenants/{key.get('id')}"
    api_caller(url,restrict_json, method)

# Set all SMB Shares to Read-Only via Network Restrictions
restrict_json = {
  "network_permissions": [
    {
      "type": "ALLOWED",
      "address_ranges": [
      ],
      "rights": [
        "READ"
      ]
    }
  ]
}
for key in smb_shares['entries']:
    method = f"SMB Share {key.get('share_name')} to Read-Only:"
    url = f"https://{cluster_address}/api/v3/smb/shares/{key.get('id')}"
    api_caller(url,restrict_json, method)

# Set all NFS exports to Read-Only:
restrict_json = {
  "restrictions": [
    {
      "host_restrictions": [
      ],
      "read_only": True,
      "user_mapping": "NFS_MAP_NONE"
   }
  ]
}
for key in nfs_exports['entries']:
    method = f"NFS export on path {key.get('export_path')} to Read-Only:"
    url = f"https://{cluster_address}/api/v3/nfs/exports/{key.get('id')}"
    api_caller(url,restrict_json, method)


# Disable S3 Service if needed
if s3_config.get('enabled'):
    restrict_json = {
  "enabled": False
}
    url = f"https://{cluster_address}/api/v1/s3/settings"
    method = f"Disable S3 Service:"
    api_caller(url,restrict_json, method)
else:
    print("S3 service already disabled")

# Disable FTP Service if needed:
method = "Disable FTP Service:"
if ftp_config['enabled']:
    restrict_json = {
    "enabled": True
    }
    url = f"https://{cluster_address}/api/v0/ftp/settings"
    api_caller(url,restrict_json, method)
else:
    print("FTP Service already disabled")

# Bring all tenants who previously had SMB and NFS services back online:
for key in tenants['entries']:
    if key.get('nfs_enabled') and key.get('smb_enabled'):
        method = f"Re-enabling SMB and NFS on tenant {key.get('name')}:"
        restrict_json = {
        "nfs_enabled": True,
        "smb_enabled": True
        }
        url = f"https://{cluster_address}/api/v1/multitenancy/tenants/{key.get('id')}"
        api_caller(url,restrict_json, method)
    elif not key.get('nfs_enabled') and key.get('smb_enabled'):
        method = f"Re-enabling SMB on tenant {key.get('name')}:"
        restrict_json = {
        "nfs_enabled": False,
        "smb_enabled": True
        }
        url = f"https://{cluster_address}/api/v1/multitenancy/tenants/{key.get('id')}"
        api_caller(url,restrict_json, method)
    elif not key.get('smb_enabled') and key.get('nfs_enabled'):
        method = f"Re-enabling NFS on tenant {key.get('name')}:"
        restrict_json = {
        "nfs_enabled": True,
        "smb_enabled": False
        }
        url = f"https://{cluster_address}/api/v1/multitenancy/tenants/{key.get('id')}"
        api_caller(url,restrict_json, method)
    else:
        print(f"Skipping tenant {key.get('name')} - Tenant did not have NFS or SMB enabled originally")