#!/usr/bin/env python
"""
Various functions to execute moonlight-embedded
"""

import os
import re
import sys
import time
import codecs

import xbmc
import xbmcgui
from avahi import host_check
from moonlight_utils import subprocess_runner, wait_or_cancel


def install():
    """
    Executes the installer script to configure/download the moonlight-embedded
    :return: boolean for success of installation
    """
    script = os.path.join(os.path.dirname(__file__), "bin", "install_moonlight.sh")
    cmd = f"bash {script}"
    proc = subprocess_runner(cmd.split(" "), "install", wait=False)
    (status, _) = wait_or_cancel(
        proc, "Installation", "Running installation...this may take a few minutes"
    )
    return status == 0


def launch(res, fps, bitrate, quitafter, hostip, usercustom):
    """
    Launches moonlight-embedded as an external process and kills Kodi so display is available
    Kodi will be automatically relaunched after moonlight-embedded exits

    :param res: video resolution of streaming session
    :param fps: frames per second of streaming session
    :param bitrate: bitrate of streaming session
    :param quitafter: quit flag helpful for desktop sessions
    :param hostip: gamestream host ip (blank if using autodetect)
    :param usercustom: any custom flags the user wants to pass to moonlight
    """

    gameList = load_installed_games(hostip)
    if gameList == None:
        return
    dialog = xbmcgui.Dialog()
    gameIdx = dialog.select("Choose your Game:", gameList)
    if gameIdx == -1:
        sys.exit()
    # We split at the first blank to get rid of the number in the beginning
    # We also make sure to put the game name in quotation marks to ensure it to be treated as one arg
    selectedGame = gameList[gameIdx].split(" ", 1)[1].replace("\n", "")
    xbmc.log(
        f"Streaming {selectedGame} with moonlight-embedded, Kodi will now exit.",
        xbmc.LOGINFO,
    )
    # Send quit command from moonlight after existing (helpful for non-steam sessions):
    quitflag = "-q" if quitafter == "true" else ""
    # Custom host ip (moonlight will auto-detect if not specified)
    hostipflag = f"-i {hostip}" if hostip else ""
    # Custom user settings:
    customflag = f'-c "{usercustom}"' if usercustom else ""
    script = os.path.join(
        os.path.dirname(__file__), "bin", "launch_moonlight_native.sh"
    )
    launchCommand = f"systemd-run --user bash {script}"
    # pass optional flag arguments first because bash getopts is picky
    args = f'{hostipflag} {quitflag} {customflag} "{res}" "{fps}" "{bitrate}" "{selectedGame}"'.strip()
    os.system(launchCommand + " " + args)


def load_installed_games(hostip):
    """
    request available games from the Gamestream host

    :return: list of available games
    """
    proc = run_moonlight_native("list", hostip)
    if proc:
        (status, result) = wait_or_cancel(proc, "List", "Getting available games...")
        if status == 0 and result:
            ## We expect the list command to follow the pattern below:
            # =========================================
            # Searching for server...
            # Connect to 192.168.178.166...
            # 1. MarioKart8
            # 2. Dolphin
            # 3. Steam
            # =========================================
            # A return code=0 signals that we were successful in obtaining the list.
            gamelist = [
                game for game in result.splitlines() if re.search(r"^\d+\.", game)
            ]
            if gamelist:
                return gamelist
            else:
                xbmcgui.Dialog().ok("Error during fetching installed games", result)


def pair(hostip):
    """
    Generates pairing credentials with a gamestream host
    """
    opt = xbmcgui.Dialog().yesno(
        "Pairing", "Do you want to pair with a Gamestream host?"
    )
    if opt:
        pDialog = xbmcgui.DialogProgress()
        proc = run_moonlight_native("pair", hostip, wait=False, blockio=False)
        stdout = ""
        codeFlag = False
        if proc is None:
            xbmcgui.Dialog().ok("Pairing", "Failed to start Moonlight.")
            return
        fd=proc.stdout.fileno()
        pDialog.create("Pairing", f"Launching pairing with {hostip}...")
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        while proc and proc.poll() is None and not pDialog.iscanceled():
            # Drain whatever output is currently available.
            while True:
                try:
                    chunk = os.read(fd, 4096)
                except BlockingIOError:
                    # No output available right now.
                    break

                if not chunk:
                    # EOF: Moonlight closed its output.
                    break

                stdout += decoder.decode(chunk)
            if not codeFlag:
                code = re.search(
                    r"Please enter the following PIN on the target PC:\s*(\d+)", stdout
                )
                if code:
                    codeFlag = True
                    code = code.groups()[0]
                    pDialog.update(
                        50,
                        f"Please enter authentication code {code} on Gamestream host",
                    )
                else:
                    pDialog.update(
                        25,
                        stdout[-1000:] or "Waiting for Moonlight...",
                    )

        if not pDialog.iscanceled() and proc is not None and  proc.returncode == 0:
            pDialog.update(100, "Complete!")
            time.sleep(3)
        else:
            try:
                proc.terminate()
            except:
                proc.kill()
                proc.wait()
            finally:
                pDialog.close()
        if re.search(r"Failed to pair to server: Already paired", stdout):
            opt = xbmcgui.Dialog().ok(
                "Pairing", "Gamestream credentials already exist for this host."
            )

def run_moonlight_native(mode, hostip, wait=True, blockio=True):
    """
    execute moonlight in a local subproces swithout docker (won't work for streaming)

    :param mode: moonlight execution mode (pair/unpair/list etc)
    :param wait: wait for process to complete
    :param block: allow reading of stdout to block
    :return: subprocess object
    """
    if not hostip:
        xbmcgui.Dialog().ok(
            "Error",
            "No Gamestream host configured. Please add it in settings and retry.",
        )
        return None
    cmd = f"moonlight {mode} {hostip}"
    return subprocess_runner(
        cmd.rstrip().split(" "), "moonlight " + mode, wait, blockio
    )
