# All-Stop script - Place a Qumulo Cluster in Read-Only mode

**This script will stop all front-end traffic in a cluster and place all client accessible protocols in a read-only mode**

## Installation

- Copy the self contained `all_stop` binary for your OS type to your local machine and make it executable if required.
- Copy `all_stop.conf` and keep it in the same directory as the the binary executable

#### (Optional) Alternate mode from source:
- Copy `all_stop.py` Python script to your local machine and make it executable if required.

- Copy `all_stop.conf` and keep it in the same directory as the .py script
- Install the `requirements.txt` file

This script was built and tested with Python 3.11.6

## Configuration

Edit the `all_stop.conf` file with your values. This file MUST be kept in the same directory as `all_stop.py` or the `all_stop` binary

This script requires a valid Access Token for a user with the following RBAC privileges:

- NFS_EXPORT_READ: View configuration of NFS exports
- NFS_EXPORT_WRITE: Create, modify, and delete NFS exports
- TENANT_READ: View any tenant information
- TENANT_WRITE: Create, edit or delete tenants
- SMB_SHARE_READ: View configuration of SMB shares and SMB server settings
- SMB_SHARE_WRITE: Create, modify, and delete SMB shares and SMB server settings
- S3_SETTINGS_READ: View S3 server settings
- S3_SETTINGS_WRITE: Modify S3 server settings
- FTP_READ: View FTP status and settings
- FTP_WRITE: Modify FTP status and settings


To create a Role called `set_read_only` on your cluster via the Qumulo `qq` CLI copy the file called `read_only_privileges` from this repo to your `qq` CLI enabled machine and apply it with `qq auth_create_role -r set_read_only -p read_only_privileges`


### Helpful Qumulo Care Articles:

[How to get an Access Token](https://care.qumulo.com/hc/en-us/articles/360004600994-Authenticating-with-Qumulo-s-REST-API#acquiring-a-bearer-token-by-using-the-web-ui-0-3) 

[Qumulo Role Based Access Control](https://care.qumulo.com/hc/en-us/articles/360036591633-Role-Based-Access-Control-RBAC-with-Qumulo-Core#managing-roles-by-using-the-web-ui-0-7)

## Operation

### To place cluster in Read-Only mode:
- Run `all_stop --stop`

### To return the cluster to its previous config:
- Run `all_stop --resume`

### To restore the cluster from a specific running config file:

- Run `all_stop --resume --file /path/to/file`





