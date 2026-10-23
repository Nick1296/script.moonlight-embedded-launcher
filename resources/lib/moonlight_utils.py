#!/usr/bin/env python
"""
Utility functions for subprocesses and docker containers
"""

import fcntl
import os
import subprocess
import time

import xbmcgui
import codecs


def subprocess_runner(cmd, desc, wait=True, blockio=True):
    """
    execute command in a local subprocess

    :param cmd: command to execute in list format
    :param desc: description of command being run (for error messages)
    :param wait: wait for process to complete
    :param block: allow reading of stdout to block
    :return: subprocess object if non-waiting, None or bytes if waiting
    """
    if wait:
        try:
            proc = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as procError:
            msg = procError.output
            xbmcgui.Dialog().ok(f"Error during {desc}", msg)
            return None
    else:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if not blockio:
            fd = proc.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    return proc


def wait_or_cancel(proc, title, message):
    """
    Display status dialog while process is running and allow user to cancel
    Assumes proc is returned from subprocess_runner with wait=True

    :param proc: subprocess object
    :param title: title for status dialog
    :param message: message for status dialog
    :return: (process exit code, stdout output or None)
    """
    pDialog = xbmcgui.DialogProgress()
    pDialog.create(title, "")
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    while (proc and not isinstance(proc,bytes) and proc.poll() is None) and not pDialog.iscanceled():
        pDialog.update(50, message)
    try:
        if not pDialog.iscanceled():
            exitcode = 0
            stdout = decoder.decode(proc)
            pDialog.update(100, "Complete!")
            time.sleep(3)
    except subprocess.CalledProcessError as procError:
            msg = procError.output
            xbmcgui.Dialog().ok(f"Error during {title.lower()}", msg)
            stdout = None
            exitcode = 1
    finally:
        pDialog.close()
    return (exitcode, stdout)
