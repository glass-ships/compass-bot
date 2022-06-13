#!/usr/bin/env bash

apt install -y libopus0

pip install --upgrade pip
pip install -r requirements.txt
pip install pymongo[srv]

python src/main.py