from datetime import datetime, timedelta
import sys
import subprocess
from pathlib import Path
from typing import Optional

import psutil
import typer

from compass_bot.utils.utils import epoch_to_dt
from compass_bot.utils.utils import console


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
    :arrow_right: To stop the bot, use: poetry run compass stop
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
        console.print("Error stopping bot: ", e)
        raise typer.Exit(1)
    console.print("Bot stopped successfully")
    raise typer.Exit()


@app.command()
def status():
    """Checks the status of the Bot"""
    processes = [p for p in psutil.process_iter(attrs=['name']) if 'python' in p.name()]
    for p in processes:
        if 'src/compass_bot/bot.py' in p.cmdline():
            start_time = epoch_to_dt(p.create_time()).strftime("%Y-%m-%d at %H:%M:%S")
            uptime = timedelta(seconds=(datetime.now() - epoch_to_dt(p.create_time())).total_seconds())
            console.print(f"""
    Compass is currently running:
        PID: {p.pid}
        Command: "{' '.join(p.cmdline())}"
        Status: {p.status()}
        Started: {start_time}
        Uptime: {uptime.days} days, {uptime.seconds//3600} hours, {(uptime.seconds//60)%60} minutes, {uptime.seconds%60} seconds
    """)
            raise typer.Exit()
    console.print("\n\tCompass is not currently running")


# if __name__ == "__main__":
#     app()

