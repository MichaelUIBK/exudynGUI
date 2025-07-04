# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project
#
# Filename: core/output_discovery_worker.py
#
# Description:
#     Standalone script used to discover supported output variables for a specific
#     component type (object, node, etc.) in an Exudyn system. This is typically
#     invoked as a subprocess to safely probe output capabilities without 
#     affecting the main simulation state.
#
#     Inputs (via command-line arguments):
#       1. SystemContainer identifier or mbs reference (as serialized handle or ID)
#       2. Entity type (e.g., 'object', 'node')
#       3. Entity index (integer)
#       4. Sensor type (e.g., 'Displacement', 'Velocity')
#
#     Output:
#       JSON string listing all supported output variable types
#
# Authors:  Michael Pieber, [Your Name Here if modified]
# Date:     2025-07-03
# License:  BSD-3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from exudyn import SystemContainer
from exudynGUI.core.outputDiscovery import discover_supported_outputs_via_assembly_test
import sys
import json
def main():
    mbs = sys.argv[1]
    entity_type = sys.argv[2]
    entity_index = int(sys.argv[3])
    sensor_type = sys.argv[4]
    outputs = discover_supported_outputs_via_assembly_test(
        mbs, entity_type=entity_type, entity_index=entity_index, sensor_type=sensor_type
    )
    json.dumps(outputs)

if __name__ == "__main__":
    main()