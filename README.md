# Compass Bot

[![GitLab](https://gitlab.com/glass-ships/compass-bot/badges/main/pipeline.svg)](https://gitlab.com/glass-ships/compass-bot/-/pipelines)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://gitlab.com/glass-ships/compass-bot/-/raw/main/LICENSE)

[![Documentation Badge](https://img.shields.io/badge/Documentation-8A2BE2)](https://glass-ships.gitlab.io/compass-bot)
[![Invite Badge](https://img.shields.io/badge/Invite%20Compass-8A2BE2)](https://discord.com/oauth2/authorize?client_id=932737557836468297&scope=bot&permissions=8&scope=applications.commands%20bot)

Compass is a general Discord bot written in Python and hosted on DigitalOcean.

This repository contains the source code for Compass, as well as the documentation for the bot,
and can be used as a template for creating your own Discord bot.  
(If you use this repository as a template, please give credit to the original author(s))

If you have any questions, suggestions, or feedback, please feel free to create an issue, or message me on Discord directly (glass.ships#4517)!

For guided instructions on creating a Discord bot in C# or Python, see [Fatcatnine's Thinbotnine repository](https://gitlab.com/fatcatnine/thinbotnine) (soon TM)

#### Requirements

- [Python](https://python.org) >= 3.12
- [uv](https://astral.sh/uv)
- libffi-dev
- libnacl-dev
- libopus0

### Development - Running the bot

- Install system dependencies (for example, on Ubuntu):
   ```bash
   sudo apt install -y \
      build-essential \
      libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev \  
      libffi-dev libnacl-dev libopus0
   ```

- Install [uv](https://astral.sh/uv)

- Clone the repository:  
   ```bash
   git clone https://gitlab.com/glass-ships/compass-bot.git
   ```

- Install Compass and its dependencies:  
   ```bash
   uv venv && uv pip install .
   ```

- Start the bot:
   ```bash
   uv run compass [OPTIONS] start [ARGS]
   ```

For more information, see the [documentation](https://glass-ships.gitlab.io/compass-bot),
or run `uv run compass --help` for a list of available commands.

### Contributing

| [Issues](https://gitlab.com/glass-ships/compass-bot/-/issues/) |

We'd love to have you contribute to Compass!  
Feel free to create an issue or pull request if you have any questions, suggestions, or feedback.

[![DigitalOcean Referral Badge](https://web-platforms.sfo2.cdn.digitaloceanspaces.com/WWW/Badge%201.svg)](https://www.digitalocean.com/?refcode=2c48df5114ee&utm_campaign=Referral_Invite&utm_medium=Referral_Program&utm_source=badge)
