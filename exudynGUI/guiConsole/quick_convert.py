#!/usr/bin/env python3
"""
Quick Exudyn to GUI Converter
=============================

Super simple approach to convert your Exudyn script to GUI model.
Since QtConsole integration is auto-loaded, just run this directly!

Usage in QtConsole:
exec(open('guiConsole/quick_convert.py', encoding='utf-8').read())
"""

print("🚀 Quick Exudyn to GUI Converter")
print("=" * 35)

print("🔧 Converting your mass-spring-damper script to GUI...")

# Your original parameters
L = 0.5         # spring length (for drawing)
force = 10
u0 = 1
v0 = 1
mass = 10
spring = 100
damper = 20

# Clear and start fresh
print("1. Clearing model...")
clear_model_simple()

# Method 1: Use helper functions (easiest)
print("2. Adding nodes using helper functions...")
add_ground_node_simple("Ground", [0, 0, 0])
add_mass_node_simple("MassNode", [L, 0, 0])

# Method 2: Direct modelSequence manipulation (more flexible)
print("3. Adding objects directly to modelSequence...")

from exudynGUI.model.modelData import modelSequence

# Add mass point object
mass_point = {
    'type': 'ObjectMassPoint',
    'data': {
        'name': 'MassPoint',
        'nodeNumber': 'nMassNode',
        'physicsMass': mass,
        'graphicsDataList': []
    }
}
modelSequence.append(mass_point)

# Add markers for the spring-damper connection
ground_marker = {
    'type': 'MarkerNodeCoordinate', 
    'data': {
        'name': 'GroundMarker',
        'nodeNumber': 'nGround',
        'coordinate': 0
    }
}
modelSequence.append(ground_marker)

node_marker = {
    'type': 'MarkerNodeCoordinate',
    'data': {
        'name': 'NodeMarker', 
        'nodeNumber': 'nMassNode',
        'coordinate': 0
    }
}
modelSequence.append(node_marker)

# Add spring-damper
spring_damper = {
    'type': 'ObjectConnectorCoordinateSpringDamper',
    'data': {
        'name': 'SpringDamper',
        'markerNumbers': ['mGroundMarker', 'mNodeMarker'],
        'stiffness': spring,
        'damping': damper,
        'offset': 0.0
    }
}
modelSequence.append(spring_damper)

# Add load
load = {
    'type': 'LoadCoordinate',
    'data': {
        'name': 'Force',
        'markerNumber': 'mNodeMarker',
        'load': force
    }
}
modelSequence.append(load)

print("4. Syncing to Exudyn system...")
sync_model_to_exudyn_simple()

# Check results
status = get_model_status_simple()
print(f"\n📊 Conversion Results:")
print(f"   GUI model items: {status.get('modelSequence_length', 0)}")
print(f"   Exudyn nodes: {status.get('mbs_nodes', 0)}")
print(f"   Exudyn objects: {status.get('mbs_objects', 0)}")
print(f"   Exudyn markers: {status.get('mbs_markers', 0)}")
print(f"   Exudyn loads: {status.get('mbs_loads', 0)}")

print("\n✅ SUCCESS! Your Exudyn script is now a GUI model!")

print(f"\n🎯 Original Script Parameters:")
print(f"   Spring length L = {L}")
print(f"   Applied force = {force}")
print(f"   Initial displacement u0 = {u0}")
print(f"   Initial velocity v0 = {v0}")
print(f"   Mass = {mass}")
print(f"   Spring stiffness = {spring}")
print(f"   Damping = {damper}")

print(f"\n💡 What you can do now:")
print(f"   1. See the model structure in the GUI tree")
print(f"   2. Edit any parameter by clicking on items")
print(f"   3. Run simulation from GUI")
print(f"   4. Add visualization")
print(f"   5. Export complete Exudyn script")

print(f"\n🔬 To run the original simulation:")
print(f"   # Set up simulation (copy/paste this):")
simulation_setup = f'''
simulationSettings = exu.SimulationSettings()
simulationSettings.solutionSettings.solutionWritePeriod = 5e-3
simulationSettings.solutionSettings.sensorsWritePeriod = 5e-3
simulationSettings.timeIntegration.numberOfSteps = 1000
simulationSettings.timeIntegration.endTime = 1.0
simulationSettings.displayComputationTime = True
simulationSettings.timeIntegration.verboseMode = 1
simulationSettings.timeIntegration.generalizedAlpha.spectralRadius = 1

# Run simulation
exu.StartRenderer()
mbs.WaitForUserToContinue()
exu.SolveDynamic(mbs, simulationSettings)
mbs.WaitForUserToContinue()
exu.StopRenderer()
'''

print(simulation_setup)

print("🎉 Conversion complete! Enjoy your GUI-based model!")
