# Compass
[![GitLab](https://gitlab.com/glass-ships/compass-bot/badges/main/pipeline.svg)](https://gitlab.com/glass-ships/compass-bot/-/pipelines)
[![License](https://img.shields.io/github/license/glass-ships/compass-bot)](https://gitlab.com/glass-ships/compass-bot/-/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)
[![Poetry](https://img.shields.io/badge/poetry-1.1.11-blue)](https://python-poetry.org/docs/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.0.0a-blue)](https://discordpy.readthedocs.io/en/latest/)  

| [Documentation](https://glass-ships.gitlab.io/compass-bot) | [Invite Compass](https://discord.com/oauth2/authorize?client_id=932737557836468297&scope=bot&permissions=8&scope=applications.commands%20bot) |

Compass is a general Discord bot written in Python and hosted on DigitalOcean. 

This repository contains the source code for Compass, as well as the documentation for the bot, 
and can be used as a template for creating your own Discord bot.  
(If you use this repository as a template, please give credit to the original author(s))

If you have any questions, suggestions, or feedback, please feel free to create an issue, or message me on Discord directly (glass.ships#4517)!

For guided instructions on creating a Discord bot in C# or Python, see [Fatcatnine's Thinbotnine repository](https://gitlab.com/fatcatnine/thinbotnine) (soon TM)

#### Dependencies
- Python >= 3.11
- Poetry
- libffi-dev
- libnacl-dev
- libopus0


### Development - Running the bot

- Install system dependencies:  
    `sudo apt install -y libffi-dev libnacl-dev libopus0 build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev`  
    (or equivalent for your system)

- Install [Poetry](https://python-poetry.org/docs/#installation) and [Python](https://www.python.org/downloads/) (if you haven't already)

- Clone the repository:  
    `git clone https://gitlab.com/glass-ships/compass-bot.git`

- Install Compass and its dependencies:  
    `poetry install`

- Start the bot:  
    `poetry run compass [OPTIONS] start [ARGS]`

For more information, see the [documentation](https://glass-ships.gitlab.io/compass-bot), 
or run `poetry run compass --help` for a list of available commands.

### Contributing

We'd love to have you contribute to Compass!  
Feel free to create an issue or pull request if you have any questions, suggestions, or feedback.

[![DigitalOcean Referral Badge](https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg)](https://www.digitalocean.com/?refcode=2c48df5114ee&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge)

