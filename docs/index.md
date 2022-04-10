# Fragment

| [Documentation](docs/) | [Invite to your server](https://discord.com/api/oauth2/authorize?client_id=932737557836468297&scope=bot&permissions=1) |

Fragment is a general Discord bot written in Python and hosted on Heroku. 

If you have any questions, suggestions, or feedback, please feel free to create an issue, or message me on Discord directly (glass.ships#4517)!

For guided instructions on creating a Discord bot in C# or Python, see [Fatcatnine's Thinbotnine repository](https://gitlab.com/fatcatnine/thinbotnine) (soon TM)

### Contents

A few boring files:  
- [requirements.txt](requirements.txt) - List of Python dependencies.  
- [Procfile](Procfile) - Heroku file - Specifies scripts for the separate web and worker access points.  
- [dashboard.py](dashboard.py) - Heroku file - can be used to serve a web interface for the bot, but currently blank.  
- [start.sh](start.sh) - Heroku file - installs deps and runs the bot.  

The code [(src)](src/):  
- [main.py](main.py) - Imports the [cogs](cogs/) and initiates the bot connection.  
- [helper.py](helper.py) - Contains some helper functions to be used in commands in [cogs](cogs/)  
- [database.py](database.py) - Commands for interacting with the database  
- [cogs](cogs/) - The good stuff. Commands and listeners organized into separate files for general use, chat moderation, debugging utilities, etc.   
    - I've included a [template](cogs/template) for new cogs. Just change "CogName" to something appropriate.  
  
You can safely ignore the [archive](archive/), it's mostly just outdated or unused code that I may find handy for reference later. 
