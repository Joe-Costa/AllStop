#!/usr/bin/env python3
import argparse
import urllib3
import configparser
import set_read_only as set_read_only
import resume_cluster as resume_cluster

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
    parser = argparse.ArgumentParser(description="Script with --stop and --resume options")
    parser.add_argument("--stop", action="store_true", help="Run Stop class")
    parser.add_argument("--resume", action="store_true", help="Run Resume class")

    args = parser.parse_args()

    if args.stop:  
        set_read_only
        asyncio.run(collect_and_stop())
        # Add any additional logic related to the Stop class here

    elif args.resume:
        resume_cluster
        # Add any additional logic related to the Resume class here

    else:
        print("No valid option provided. Use --stop or --resume.")

if __name__ == "__main__":
    main()
