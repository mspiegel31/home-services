# Description
a collection of primarily docker-compose stacks for use with various portainer hosts

## General Context
1. I am using the Portainer Community Edition

# Rules
1. For Portainer Repository stacks, never use `env_file`: it requires `stack.env` in Git. Declare `${VAR}` explicitly and set values in Portainer's UI.


## examples/prior art
1. large amounts of homelab content can be found at https://github.com/JamesTurland/JimsGarage
