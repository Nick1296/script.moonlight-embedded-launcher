#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Avahi functions to check for gamstream hosts etc
"""
from moonlight_utils import subprocess_runner

import xbmcgui

def host_check():
    """
    Check if gamestream host is available on local network

    :return: boolean for host availability
    """
    check = subprocess_runner("avahi-browse -t _nvstream._tcp".split(" "), "host check")
    if check and "nvstream" in str(check):
        return True
    else:
        return False
