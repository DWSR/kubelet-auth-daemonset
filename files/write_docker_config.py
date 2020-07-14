#!/usr/bin/env python3

# This script reads the contents of files on the disk in order to construct a
# Docker config containing authentication information for private Docker
# registries. This script writes the rendered config to disk so that the
# kubelet running on the node can use it.
#
# For more information about this pattern, see here:
# https://v1-16.docs.kubernetes.io/docs/concepts/containers/#configuring-nodes-to-authenticate-to-a-private-registry
#
# This script uses files and not environment variables because Kubernetes
# Secrets that are projected into the container as files are updated when the
# value of the Secret is updated. When Secrets are projected as environment
# variables, they are not updated automatically.
#
# This script is configured entirely by environment variables as described:
#
# SECRET_FILE_PATH: The path to the files that contain the username, password
# and registry addresses. This will correspond with the Secret volumeMount
# DOCKER_CONFIG: The path to write the Docker config to. This will correspond
# with the hostPath volumeMount.
# SLEEP_INTERVAL: The number of seconds to sleep between regenerating the
# Docker config. The default is 120 (2m)
# DEBUG: Enables debug logging. Optional.

import base64
import json
import logging
import os
import signal
from time import sleep
from typing import Set

SECRET_PATH = os.environ["SECRET_FILE_PATH"]


def term_handler(signum, frame):
    # Do this in order to immediately exit instead of waiting for the sleep to
    # finish
    logging.info("Caught SIGTERM, exiting")
    exit(0)


def read_file(filename: str) -> str:
    logging.debug(f"Opening {filename} for reading")
    with open(filename, "r") as f:
        return f.read()


def get_username() -> str:
    username = read_file(f"{SECRET_PATH}/username")
    logging.debug(f"Username is: {username}")
    return username


def get_password() -> str:
    password = read_file(f"{SECRET_PATH}/password")
    logging.debug(f"Password starts with: {password[0:4]}")
    return password


def get_registry_addresses() -> Set[str]:
    registries = read_file(f"{SECRET_PATH}/registries")
    logging.debug(f"Registries string is: {registries}")
    # Use a set to de-duplicate, just in case
    addresses = set(registries.split(","))
    logging.debug(f"Addresses are: {addresses}")
    return addresses


def generate_docker_config(
    username: str, password: str, registries: set
) -> dict:
    base64_creds = base64.b64encode(
        f"{username}:{password}".encode()
    ).decode("utf-8")
    config = {
      "auths": {}
    }
    for r in registries:
        config["auths"][r] = {
          "auth": base64_creds,
          "email": ""
        }
    return config


def get_docker_config_location() -> str:
    loc = os.environ["DOCKER_CONFIG"]
    logging.info(f"Config location: {loc}")
    return loc


def get_sleep_interval() -> int:
    interval = os.environ.get("SLEEP_INTERVAL", 120)
    logging.info(f"Sleep interval is: {interval}")
    return int(interval)


def set_log_level():
    if "DEBUG" in os.environ.keys():
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


if __name__ == "__main__":
    logging.basicConfig()
    set_log_level()
    logging.debug("Setting SIGTERM handler")
    signal.signal(signal.SIGTERM, term_handler)
    logging.info("Getting location to write the Docker config")
    config_location = get_docker_config_location()
    logging.info("Getting the sleep interval")
    sleep_interval = get_sleep_interval()
    # Loop forever in case the credentials are changed
    while True:
        logging.debug("Getting username")
        username = get_username()
        logging.debug("Getting password")
        password = get_password()
        logging.debug("Getting registries")
        registries = get_registry_addresses()
        logging.debug("Generating Docker config")
        docker_config = generate_docker_config(username, password, registries)
        logging.info("Writing new Docker config")
        with open(config_location, "w") as f:
            f.write(json.dumps(docker_config, indent=2))
        logging.info("Sleeping...")
        sleep(sleep_interval)
