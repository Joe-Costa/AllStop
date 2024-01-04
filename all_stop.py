#!/usr/bin/env python3
import argparse
import urllib3
import configparser
import set_read_only
import resume_cluster

# This script is used to place a Qumulo cluster in read-only mode


def main():
    parser = argparse.ArgumentParser(
        description="Set Qumulo Cluster in Read-Only mode with --stop and recover it the --resume option"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--stop", action="store_true", help="Set Cluster to Read-Only")
    group.add_argument("--resume", action="store_false", help="Restore Cluster from Read-Only mode")

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
