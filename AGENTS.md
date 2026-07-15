# Description
a collection of primarily docker-compose stacks for use with various portainer hosts

## General Context
1. I am using the Portainer Community Edition

# Rules
1. For Portainer Repository stacks, never use `env_file`: it requires `stack.env` in Git. Declare `${VAR}` explicitly and set values in Portainer's UI.

1. media apps are hosted on zfs.  their configs and data should be located in /mnt/tank/container-configs/<APP_NAME>

## examples/prior art
1. large amounts of homelab content can be found at https://github.com/JamesTurland/JimsGarage
1. self-hosted app listing can also be found at https://selfh.st/apps/
