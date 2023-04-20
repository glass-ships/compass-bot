import sys
import subprocess
from pathlib import Path
from typing import Optional

from compass_bot.utils.log_utils import get_logger
from compass_bot.utils.utils import console

import typer
app = typer.Typer(name="compass")
app_state = {"verbose": None}

@app.callback(invoke_without_command=True)
def version_callback(
    version: Optional[bool] = typer.Option(None, "--version", is_eager=True),
    verbose: Optional[bool] = typer.Option(None, "--verbose/--quiet", "-v/-q", help="Use verbose to set logging level to DEBUG, quiet to suppress"),
    ):
    if version:
        from compass_bot import __version__
        console.print(f"\n:arrow_right: Compass Bot version: {__version__}")
        raise typer.Exit()
    app_state["verbose"] = verbose


@app.command()
def start(
        dev: bool = typer.Option(False, "--dev", "-d", help="Run the development version of the Bot locally"),
        update: bool = typer.Option(False, "--update", "-u", help="Update the Bot's dependencies"),
        pull: bool = typer.Option(False, "--pull", "-p", help="Pull the latest version of the Bot from GitHub"),
    ):
    """Starts the Bot

    Args:
        dev (bool, optional): Run the development version of the Bot locally. Defaults to False.
        update (bool, optional): Update the Bot's dependencies. Defaults to False.
        pull (bool, optional): Pull the latest version of the Bot from GitHub. Defaults to False.    
    """
    # if app_state['verbose'] is None:

    log_level = "INFO" if (app_state['verbose'] is None) else "DEBUG" if (app_state['verbose'] == True) else "WARNING"
    console.print(f"""
:arrow_right: Starting {'main' if not dev else 'dev'} bot...
    :arrow_right: Setting Compass log level to {log_level}
    :arrow_right: Top stop the bot, use: poetry run compass stop
    :arrow_right: For log output, see `logs/`
""")
    cmd = ["python", "src/compass_bot/bot.py"]
    if app_state['verbose'] == False: cmd.append("--quiet")
    if app_state['verbose'] == True: cmd.append("--verbose")
    if dev: cmd.append("--dev")
    if update: cmd.append("--update")
    # if pull: cmd.append("--pull")
    if pull: subprocess.call(["git", "pull"], stdout=sys.stdout, stderr=sys.stderr,)

    Path("logs").mkdir(parents=True, exist_ok=True)
    logfile = open("logs/all.log", "w")
    subprocess.Popen(cmd, stdout=logfile, stderr=logfile,)
    logfile.close()


@app.command()
def stop():
    """Stops the Bot"""
    try:
        subprocess.call(["pkill", "-f", "python src/compass_bot/bot.py"])
    except Exception as e:
        print("Error stopping bot: ", e)
        raise typer.Exit(1)
    print("Bot stopped successfully")
    raise typer.Exit()

    
# if __name__ == "__main__":
#     app()

