import os
import re

from fabric.api import env

try:
    from digitalocean import Manager
except ImportError:
    import sys
    print ("You are trying to connct to digital ocean but "
           "don't have python-digitalocean installed. Please install it.")
    sys.exit(27)


def get_roles(client_id=None, api_key=None, blacklist=None, ssh_port=22):
    ip_blacklist = blacklist or []
    client_id = client_id or os.getenv("DO_CLIENT_ID")
    api_key = api_key or os.getenv("DO_API_KEY")

    if not client_id or not api_key:
        print ("You have to provide the client ID and API key for Digital "
               "Ocean. Set DO_CLIENT_ID and DO_API_KEY environment variables.")
        sys.exit(28)

    if not env.server_name_regex:
        env.server_name_regex = re.compile(r'(?P<role>.+)')

    if not env.server_format:
        env.server_format = "{ip}:{port}"

    # Retrieve the app server IPs from the DO API
    manager = Manager(client_id=client_id, api_key=api_key)

    roles = {}
    for droplet in manager.get_all_droplets():
        if droplet.ip_address in ip_blacklist:
            continue

        match = env.server_name_regex.match(droplet.name)
        if not match:
            continue

        roles.setdefault(match.group('role'), []).append(
            env.server_format.format(ip=droplet.ip_address, port=ssh_port))
    return roles
