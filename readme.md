# All-Stop script - Place a Qumulo Cluster in Read-Only mode

**This script will stop all traffic in a cluster and place it in a read-only mode**

## Installation

Copy all files to your local machine.

Make `all_stop.py` executable

## Configuration

Edit the `all_stop.conf` file with your values.

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

## Operation

### To place cluster in Read-Only mode:
- Run `all_stop.py --stop`

### To return the cluster to its previous config:
- Run `all_stop.py --resume`





