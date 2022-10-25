#!/usr/bin/env bash

# apt install -y python3 python3-pip libffi-dev libnacl-dev libopus0
apt install -y python3.11 python3.11-dev python3.11-pip libffi-dev libnacl-dev libopus0
pip install --upgrade pip
pip install .
# pip install pymongo[srv]
