# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: functions/graphicsVisualizations.py
#
# Description:
#     Stores default graphicsData configurations used by the Exudyn GUI.
#     Each entry corresponds to a specific Create* or Add* constructor and
#     provides default visual representations (e.g., spheres, checkerboards).
#     These settings are editable in the GUI and restored when reloading items.
#
# Authors:  Michael Pieber
# Date:     2025-05-12
# Notes:    Automatically updated when users add or edit visualizations.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
graphicsDataRegistry = {
    'CreateGround': [],
    'CreateMassPoint':  [],
    'CreateForce': [],
    'CreateCartesianSpringDamper': [],
    'CreateRevoluteJoint': [],
    'CreateRigidBody':  [],
    'CreateRigidBodySpringDamper': [],
    'CreateTorque': [],
    'CreatePrismaticJoint': [],
    'NodePoint': [],
    'ObjectGround': [],
    'Node1D': [],
    'NodePoint2D': [],
    'ObjectMassPoint': [],
    'CreateGenericJoint': [],
    'NodePointGround': [],
    'MarkerNodeCoordinate': [],
    'ObjectConnectorCoordinateSpringDamper': [],
    'LoadCoordinate': [],
    'LoadForceVector': [],
}
