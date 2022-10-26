#!/usr/bin/env bash

# apt install -y python3 python3-pip libffi-dev libnacl-dev libopus0 ffmpeg
apt install -y python3.11-full python3.11-dev libffi-dev libnacl-dev libopus0 ffmpeg
curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
pip install --upgrade pip
pip install .
