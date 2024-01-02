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
config_json = [cluster_name, { "tenant_info":tenants['entries'] }, { "smb_shares": smb_shares['entries'] }, { "nfs_exports": nfs_exports['entries'] }, { "s3_config": s3_config }, { "ftp_config": ftp_config }]
file_location = config_save_file_location + cluster_name["cluster_name"] + "_config_backup.json"
with open(file_location, 'w') as json_file:
    json.dump(config_json, json_file, indent=2)

# The plan is to use SMB Share permissions to set all to Read Only without having tomuck around with SMB share permissions
# This will still require that all services are bumped for changes to be enforced

