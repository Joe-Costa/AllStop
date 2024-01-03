#!/usr/bin/env python3
import argparse
import urllib3
import set_read_only

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

def main():
    parser = argparse.ArgumentParser(description="Script with --stop and --resume options")
    parser.add_argument("--stop", action="store_true", help="Run Stop class")
    parser.add_argument("--resume", action="store_true", help="Run Resume class")

    args = parser.parse_args()

    if args.stop:  
        all_stop_4gpt
        # Add any additional logic related to the Stop class here

    elif args.resume:
        resume_cluster
        # Add any additional logic related to the Resume class here

    else:
        print("No valid option provided. Use --stop or --resume.")

if __name__ == "__main__":
    main()
