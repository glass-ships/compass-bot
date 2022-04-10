#!/usr/bin/env bash

pip install pymongo pytz python-dateutil
pip install pymongo[srv]
pip install git+https://github.com/Rapptz/discord.py.git
python src/main.py