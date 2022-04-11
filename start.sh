#!/usr/bin/env bash

pip install --upgrade pip
pip install -r requirements.txt
pip install pymongo[srv]
python src/main.py