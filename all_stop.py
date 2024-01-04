#!/usr/bin/env python3
import argparse
import urllib3
import configparser
import set_read_only
import resume_cluster

# Load the config file
config = configparser.ConfigParser()
config.read('all_stop.conf')
CLUSTER_ADDRESS = config['CLUSTER']['CLUSTER_ADDRESS']
TOKEN = config['CLUSTER']['TOKEN']
CONFIG_SAVE_FILE_LOCATION = config['CLUSTER']['CONFIG_SAVE_FILE_LOCATION']

# Disable "Insecure HTTP" errors if certs are not available
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

def main():
    parser = argparse.ArgumentParser(description="Set Qumulo Cluster in Read-Only mode and recover it with --stop and --resume options")
    parser.add_argument("--stop", action="store_true", help="Set Cluster to Read-Only")
    parser.add_argument("--resume", action="store_true", help="Restore Cluster from Read-Only mode")

    args = parser.parse_args()

    if args.stop:  
        set_read_only.main()

    elif args.resume:
        resume_cluster.main()


    else:
        print("No valid option provided. Use --stop or --resume.")
        exit()

if __name__ == "__main__":
    main()
