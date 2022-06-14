# Compass

| [Documentation](https://glass-ships.gitlab.io/compass-bot) | [Invite Compass](https://discord.com/oauth2/authorize?client_id=932737557836468297&scope=bot&permissions=8&scope=applications.commands%20bot) |

Compass is a general Discord bot written in Python and hosted on Heroku. 

If you have any questions, suggestions, or feedback, please feel free to create an issue, or message me on Discord directly (glass.ships#4517)!

For guided instructions on creating a Discord bot in C# or Python, see [Fatcatnine's Thinbotnine repository](https://gitlab.com/fatcatnine/thinbotnine) (soon TM)

#### Dependencies
- Python >= 3.8
- libopus0

### Contents

A few boring files:
- [requirements.txt](requirements.txt) - List of Python dependencies 
- [Procfile](Procfile) - Heroku file - Specifies scripts for the separate web and worker access points
- [dashboard.py](dashboard.py) - Heroku file - can be used to serve a web interface for the bot, but currently blank.
- [start.sh](start.sh) - Heroku file - installs deps and runs the bot.

The code: [src](src/)
- [main.py](src/main.py) - Imports the [cogs](src/cogs/) and initiates the bot connection.  
- [helper.py](src/helper.py) - Contains some helper functions to be used in commands in [cogs](src/cogs/)  
- [database.py](src/database.py) - Commands for interacting with the database  
- [cogs](src/cogs/) - The good stuff. Commands and listeners organized into separate files for general use, chat moderation, debugging utilities, etc.   
    - I've included a [template](src/cogs/template) for new cogs. Just change "CogName" to something appropriate.  
  
You can safely ignore the [archive](archive/), it's mostly just outdated or unused code that I may find handy for reference later. 
