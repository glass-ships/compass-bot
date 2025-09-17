import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import psutil
import typer

from compass.utils.utils import console, epoch_to_dt

app = typer.Typer(name="compass")
app_state = {
    "verbose": 0,
    "quiet": False,
}


@app.callback(invoke_without_command=True)
def version_callback(
    version: Optional[bool] = typer.Option(None, "--version", is_eager=True),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, help="Enable verbose logging"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Supress logging (except Errors)"),
):
    if version:
        from compass import __version__

        console.print(f"Compass Bot {__version__}")
        raise typer.Exit()
    app_state["log-level"] = (
        "INFO" if (verbose == 1) else "DEBUG" if (verbose >= 2) else "ERROR" if (quiet is True) else "WARNING"
    )
    app_state["quiet"] = quiet


@app.command()
def start(
    dev: bool = typer.Option(False, "--dev", "-d", help="Run the development version of the Bot locally"),
    update: bool = typer.Option(False, "--update", "-u", help="Update the Bot's dependencies"),
    pull: bool = typer.Option(False, "--pull", "-p", help="Pull the latest version of the Bot from GitHub"),
    debug: bool = typer.Option(False, "--debug", "-D", help="Run the Bot in debug mode (logs to stdout)"),
):
    """Starts the Bot"""

    console.print(
        f"""
:arrow_right: Starting {"main" if not dev else "dev"} bot...
    :arrow_right: Setting Compass log level to {app_state["log-level"]}
    :arrow_right: To stop the bot, use: uv run compass stop
"""
    )
    if not debug:
        console.print(f":arrow_right: For log output, see `logs/`")

    cmd = [f"{sys.executable}", "src/compass/bot.py", "--log-level", app_state["log-level"]]
    if dev:
        cmd.append("--dev")
    if update:
        cmd.append("--update")
    if app_state["quiet"]:
        cmd.append("--quiet")
    if pull:
        subprocess.call(
            ["git", "pull"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    if not debug:
        Path("logs").mkdir(parents=True, exist_ok=True)
        with open("logs/all.log", "w") as logfile:
            subprocess.Popen(cmd, stdout=logfile, stderr=logfile)
    else:
        subprocess.call(cmd)


@app.command()
def stop():
    """Stops the Bot"""
    try:
        subprocess.call(["pkill", "-f", "src/compass/bot.py"])
    except Exception as e:
        console.print("Error stopping bot: ", e)
        raise typer.Exit(1)
    console.print("Bot stopped successfully")
    raise typer.Exit()


@app.command()
def status():
    """Check if Compass is currently running"""
    processes = [p for p in psutil.process_iter(attrs=["name"]) if "python" in p.name()]
    for p in processes:
        if "src/compass/bot.py" in p.cmdline():
            start_time = epoch_to_dt(p.create_time()).strftime("%Y-%m-%d at %H:%M:%S")
            uptime = timedelta(seconds=(datetime.now() - epoch_to_dt(p.create_time())).total_seconds())
            console.print(
                f"""
Compass is currently running:
    PID: {p.pid}
    Command: "{" ".join(p.cmdline())}"
    Status: {p.status()}
    Started: {start_time}
    Uptime: {uptime.days} days, {uptime.seconds // 3600} hrs, {(uptime.seconds // 60) % 60} min, {uptime.seconds % 60} sec
"""
            )
            raise typer.Exit()
    console.print("\nCompass is not currently running\n")
