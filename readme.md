All Stop Cluster script

This script will stop all traffci in a cluster and place it in a read-only mode

Steps:

1. Collect current running config:
- Multi tenancy
    - Copy all tenants and configs
- NFS exports
    - Save all export restrictions to file
- SMB shares
    - Save all Share permissions to file
- FTP state
- S3 buckets

2. Save state to file in JSON
- Command line option for location

3. Stop all services
- Multi-tenancy disable NFS & SMB 
- Disable S3 service (S3 will be completely offline)
  - The ability to set bucket policies is not yet available, but is coming
- Disable FTP

4. Convert all exports and shares to read only

5. Re-enable protocols on all relevant tenants
- Cluster is now NFS and SMB read-only

6. Create method to put things back from saved file


