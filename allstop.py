#!/usr/bin/env python3
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# This is a perm token for QQ
#token = "access-v1:/FJ0Jbbm+JxMYOOsLUudYdx8MFyl1J4HOfIf4yGz7EwBAAAA9AEAAAAAAAD4JmZoZ2PG4757lGUAAAAAr+fGDg=="

# Perm token for QMT3
token = "access-v1:KK0ofAYQCjZWKjpPjob/Fewwcc6GopsOhDBCw5kq5mEBAAAA9AEAAAAAAABiTQn7aUwFZl99lGUAAAAAsYXNOg=="

cluster_address = "qmt3.qumulotest.local"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}



url = f"https://{cluster_address}/api/v1/multitenancy/tenants/"
tenants = requests.get(url, headers=headers, verify=False).json()


for key in tenants['entries']:
    print(key.get('id'))