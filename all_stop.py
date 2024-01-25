#!/usr/bin/env python3
import argparse
import urllib3
import configparser
import asyncio
import aiohttp
import json
import shutil
import requests
from datetime import datetime
import os
import textwrap

# This script is used to place all client-facing protocols in Qumulo cluster in read-only mode

# Load the config file
config = configparser.ConfigParser()
config.read("all_stop.conf")
CLUSTER_ADDRESS = config["CLUSTER"]["CLUSTER_ADDRESS"]
TOKEN = config["CLUSTER"]["TOKEN"]
CONFIG_SAVE_FILE_LOCATION = os.path.join(os.getcwd(), "")
USE_SSL = config["CLUSTER"].getboolean("USE_SSL")

# Disable "Insecure HTTP" errors if certs are not available
if not USE_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Function to set the cluster in a read-only state and save the prior running config to file
def set_read_only():
    async def aiohttp_get(url, session):
        async with session.get(url, headers=HEADERS, ssl=USE_SSL) as response:
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
        config_json = [
            cluster_name,
            {"tenants": tenants["entries"]},
            {"smb_shares": smb_shares["entries"]},
            {"nfs_exports": nfs_exports["entries"]},
            {"s3_config": s3_config},
            {"ftp_config": ftp_config},
        ]
        file_location = (
            CONFIG_SAVE_FILE_LOCATION + cluster_name["cluster_name"] + "_config_backup.json"
        )

        # Check to see if --stop has been already run - We do not want to do this back-to-back!
        if not os.path.exists(file_location):
            try:
                print(f"Creating new config file at {file_location}")
                with open(file_location, "w") as json_file:
                    json.dump(config_json, json_file, indent=2)
            except:
                print(
                    textwrap.dedent(
                        f"""
                    ERROR! Operation Failed: Cannot write cluster config file to directory:
                    {CONFIG_SAVE_FILE_LOCATION}
                    Please make this directory writeable or relocate the all_stop executable to a
                    writeable location.
                """.strip()
                    )
                )
                exit()
        else:
            # Ask for confirmation before overwriting
            user_response = input(
                textwrap.dedent(
                    f"""
                *** WARNING !!!! ****
                The file '{file_location}' already exists!
                Overwriting this file could lead to the loss of your clusters original configuration!
                Are you sure you want to run --stop again? (yes/no):
                """
                ).strip()
            ).lower()

            if user_response == "yes":
                # Can we write the running config file?
                try:
                    with open(file_location, "w") as json_file:
                        json.dump(config_json, json_file, indent=2)
                    print(f"The file '{file_location}' has been overwritten.")
                except:
                    print(
                        textwrap.dedent(
                            f"""
                        ERROR! Operation Failed: Cannot write cluster config file to directory:
                        {CONFIG_SAVE_FILE_LOCATION}
                        Please make this directory writeable or relocate the all_stop executable to a
                        writeable location
                    """.strip()
                        )
                    )
                    exit()
            else:
                print(
                    f"Operation canceled. The file '{file_location}' has not been overwritten. Exiting."
                )
                exit()

        # Stop NFS and SMB on all tenants
        async with aiohttp.ClientSession() as session:
            stop_tasks = [stop_smb_nfs_per_tenant(key, session) for key in tenants["entries"]]
            await asyncio.gather(*stop_tasks)

        # Stop S3 and FTP service
        async with aiohttp.ClientSession() as session:
            await stop_s3_service(session)
            await stop_ftp_service(session)

        # Set all NFS Exports to Read-Only
        async with aiohttp.ClientSession() as session:
            stop_tasks = [set_nfs_to_read_only(key, session) for key in nfs_exports["entries"]]
            await asyncio.gather(*stop_tasks)

        # Set all SMB Shares to Read-Only
        async with aiohttp.ClientSession() as session:
            stop_tasks = [set_smb_to_read_only(key, session) for key in smb_shares["entries"]]
            await asyncio.gather(*stop_tasks)

        print("** Returning SMB and NFS services to tenants **")

        # Return NFS and SMB service to any tenants who had it enabled previously
        async with aiohttp.ClientSession() as session:
            start_tasks = [start_smb_nfs_per_tenant(key, session) for key in tenants["entries"]]
            await asyncio.gather(*start_tasks)

        # Tasks complete message.  Cluster should be now in Read-Only mode
        print(f"Cluster {cluster_name.get('cluster_name')} has been placed in Read-Only mode")

    # Async General Purpose API PATCH function
    async def aiohttp_patch(url, api_json, session, method):
        async with session.patch(url, json=api_json, headers=HEADERS, ssl=USE_SSL) as response:
            if response.status == 200:
                print(f"{method} request successful")
            else:
                print(f"{method} request error: {response.status}")
                print(await response.text())  # Print the error message or response content

    # Function to disable NFS and SMB service on a tenant
    async def stop_smb_nfs_per_tenant(key, session):
        method = f"Disabling tenant {key.get('name')}:"
        restrict_json = {"nfs_enabled": False, "smb_enabled": False}
        url = f"https://{CLUSTER_ADDRESS}/api/v1/multitenancy/tenants/{key.get('id')}"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to set NFS exports to Read-Only
    async def set_nfs_to_read_only(key, session):
        method = f"NFS export on path {key.get('export_path')} to Read-Only:"
        restrict_json = {
            "restrictions": [
                {"host_restrictions": [], "read_only": True, "user_mapping": "NFS_MAP_NONE"}
            ]
        }
        url = f"https://{CLUSTER_ADDRESS}/api/v3/nfs/exports/{key.get('id')}"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to set SMB Shares to Read-Only
    async def set_smb_to_read_only(key, session):
        method = (
            f"SMB Share {key.get('share_name')} on tenant id {key.get('tenant_id')} to Read-Only:"
        )
        restrict_json = {
            "network_permissions": [{"type": "ALLOWED", "address_ranges": [], "rights": ["READ"]}]
        }
        url = f"https://{CLUSTER_ADDRESS}/api/v3/smb/shares/{key.get('id')}"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to disable S3 service
    async def stop_s3_service(session):
        method = f"Disable S3 Service:"
        restrict_json = {"enabled": False}
        url = f"https://{CLUSTER_ADDRESS}/api/v1/s3/settings"
        await aiohttp_patch(url, restrict_json, session, method)

    # Async Function to disable FTP service
    async def stop_ftp_service(session):
        method = f"Disable FTP Service:"
        restrict_json = {"enabled": False}
        url = f"https://{CLUSTER_ADDRESS}/api/v0/ftp/settings"
        await aiohttp_patch(url, restrict_json, session, method)

    # Function to re-enable tenant's SMB and NFS service
    async def start_smb_nfs_per_tenant(key, session):
        data = key
        services = [
            key.upper().replace("_ENABLED", "")
            for key, value in data.items()
            if key.endswith("_enabled") and value
            if key.startswith("nfs") or key.startswith("smb")
        ]
        if services:
            services = " and ".join(services)
            method = f"Re-enabling {services} on tenant {key.get('name')}"
            url = f"https://{CLUSTER_ADDRESS}/api/v1/multitenancy/tenants/{key.get('id')}"
            restrict_json = key
            await aiohttp_patch(url, restrict_json, session, method)
        else:
            print(
                f"Skipping tenant {key.get('name')}, tenant did not have SMB or NFS services enabled"
            )

    asyncio.run(collect_and_stop())


# Function to revert the changes applies to the cluster's config by set_read_only()
def resume_cluster(file_name):

    # Load the pre-stop configuration of the cluster
    url = f"https://{CLUSTER_ADDRESS}/api/v1/cluster/settings"
    cluster_name = requests.get(url, headers=HEADERS, verify=USE_SSL).json()
    cluster_name = cluster_name["cluster_name"]
    if file_name:
        file_location = os.path.abspath(file_name)
        ran_from_file = True
    else:
        file_name = cluster_name + "_config_backup.json"
        file_location = CONFIG_SAVE_FILE_LOCATION + file_name
        ran_from_file = False

    # Load the config subsections
    if os.path.exists(file_location):
        with open(file_location, "r") as original_config:
            config_data = json.loads(original_config.read())
            tenant_info = config_data[1]["tenants"]
            smb_shares = config_data[2]["smb_shares"]
            nfs_exports = config_data[3]["nfs_exports"]
            s3_config = config_data[4]["s3_config"]
            ftp_config = config_data[5]["ftp_config"]
    else:
        print(
            f"Cluster config file {file_location} not found!\nOperation failed, unable to restore cluster"
        )
        exit()

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
        async with session.patch(url, json=api_json, headers=HEADERS, ssl=USE_SSL) as response:
            if response.status == 200:
                print(f"{method} request successful")
            else:
                print(f"{method} request error: {response.status}")
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

    # Only move Running Config file if not running with --file option
    if not ran_from_file:
        # Rename and move cluster running config file - We do not want this file around the next time --stop needs to run!
        ran_configs_dir = os.path.join(CONFIG_SAVE_FILE_LOCATION + "previously_ran_cofigs", "")
        if os.path.exists(file_location):
            # Checks to see if we have all the needed Write privileges
            if not os.path.exists(ran_configs_dir):
                try:
                    os.mkdir(ran_configs_dir)
                except:
                    print(
                        textwrap.dedent(
                            f"""
                        ERROR: Cannot create previously run config file directory at location: {ran_configs_dir}"
                        The script attempts to move the last run config file to the new location.
                        the parent directory writeable? Dir: {CONFIG_SAVE_FILE_LOCATION}
                        Please delete or move the file {file_location} before running --stop again.
                        *** Failure to do so will lead to your cluster requiring manual recovery from the Read-Only state! ***
                        """
                        ).strip()
                    )
            try:
                new_file_name = f"{str(datetime.now()).replace(':','.')}-{file_name}"
                shutil.move(file_location, f"{os.path.join(ran_configs_dir, new_file_name)}")
                print(
                    f"\nConfig file {file_location} has been moved to {ran_configs_dir}/{new_file_name}.\nJob is complete."
                )
            except Exception as error:
                print(
                    textwrap.dedent(
                        f"""
                    ERROR: {error}
                    Cannot move previously run config file to directory {ran_configs_dir} is this directory writeable?
                    This script attempts to move the last run config file to this new location
                    Please delete or move the file {file_location} before running --stop again
                    f"*** Failure to do so will lead to your cluster requiring manual recovery from the Read-Only state! ***
                    """.strip()
                    )
                )


def main():
    parser = argparse.ArgumentParser(
        description="Set Qumulo Cluster in Read-Only mode with --stop and recover it the --resume option"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stop", action="store_true", help="Set Cluster to Read-Only")
    group.add_argument("--resume", action="store_true", help="Restore Cluster from Read-Only mode")
    parser.add_argument("--file", help="Specify restore running config file", metavar="FILE")

    args = parser.parse_args()

    if args.stop:
        if args.stop and args.file:
            parser.error("--file option is not valid with --stop.")
        else:
            set_read_only()

    elif args.resume:
        resume_cluster(args.file)

    else:
        print("No valid option provided. Use --stop or --resume.")
        exit()


if __name__ == "__main__":
    main()
