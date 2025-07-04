# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: functions/inertiaDefinitions.py
#
# Description:
#     Contains user-defined Python functions (UF*) for use in the Exudyn GUI.
#     These functions can be assigned to fields like load, offset, or sensor
#     callbacks and are dynamically loaded by the GUI at startup.
#
# Authors:  Michael Pieber
# Date:     2025-05-12
# Notes:    Extend this file with additional UF* functions as needed.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
inertiaRegistry = {
    "InertiaSphere": {
        "name": "InertiaSphere",
        "args": "mass=1.0, radius=0.1"
    },
    "InertiaMassPoint": {
        "name": "InertiaMassPoint",
        "args": "mass=1"
    },
}