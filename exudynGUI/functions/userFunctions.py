# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: functions/userFunctions.py
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
def UFload(mbs, t, load):
    import numpy as np
    return [100* np.sin(10 * (2*np.pi) * t),0,0]

def UFspringForce(mbs, t, load):
    import numpy as np
    return [100* np.sin(10 * (2*np.pi) * t),0,0]

userFunctions = {
    "UFload": UFload,
    "UFspringForce": UFspringForce,
}