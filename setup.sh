#!/usr/bin/env bash

apt install -y python3 python3-pip libffi-dev libnacl-dev libopus0
pip install --upgrade pip
pip install -r requirements.txt
pip install pymongo[srv]
