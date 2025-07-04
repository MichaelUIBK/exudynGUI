# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core\graphicsUtils.py
#
# Description:
#     Helper functions for analyzing object dependencies before creation.
#
# Authors:  Michael Pieber
# Date:     2025-05-16
# Notes:    Dynamically infers required elements (markers, bodies, etc.)
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


import os
import importlib.util
from exudyn.utilities import *
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the exudynGUI package directory (parent of core/)
PACKAGE_DIR = os.path.dirname(SCRIPT_DIR)
GRAPHICS_FILE = os.path.join(PACKAGE_DIR, 'graphicsDataLibrary.py')

def loadGraphicsLibrary():
    spec = importlib.util.spec_from_file_location("graphicsDataLibrary", GRAPHICS_FILE)
    graphicsLib = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(graphicsLib)
    return graphicsLib

def getNextSymbolicName(constructorName):
    base = constructorName.replace("GraphicsData", "")
    index = 0
    if os.path.exists(GRAPHICS_FILE):
        with open(GRAPHICS_FILE, 'r') as f:
            for line in f:
                if line.startswith(f"graphics{base}"):
                    try:
                        i = int(line[len(f"graphics{base}"):].split('=')[0])
                        index = max(index, i+1)
                    except:
                        continue
    return f"graphics{base}{index}"

def appendGraphicsEntry(symbolicName, constructorString):
    if not os.path.exists(GRAPHICS_FILE):
        Path(GRAPHICS_FILE).touch()
    with open(GRAPHICS_FILE, 'a') as f:
        f.write(f"{symbolicName} = {constructorString}\n")
