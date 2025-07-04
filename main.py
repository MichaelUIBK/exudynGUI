# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: main.py (Development launcher)
#
# Description:
#     Development entry point for launching the Exudyn GUI application.
#     This is a simple launcher that calls the package version to avoid
#     code duplication between development and installed package modes.
#
# Authors:  Michael Pieber
# Date:     2025-07-04
# License:  BSD-3 license 
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

"""Development entry point for Exudyn GUI."""

if __name__ == '__main__':
    try:
        from exudynGUI.main import launchGUI
        launchGUI()
    except Exception as e:
        print(f"❌ Fatal error in development launcher: {e}")
        import traceback
        traceback.print_exc()
        exit(1)