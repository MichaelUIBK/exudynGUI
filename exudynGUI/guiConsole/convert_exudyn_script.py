#!/usr/bin/env python3
"""
Convert Exudyn Script to GUI Model
==================================

This script shows how to take an existing Exudyn script (like your mass-spring-damper)
and inject it into the GUI as individual model items that can be edited and managed.

Usage in QtConsole (after GUI startup):
exec(open('guiConsole/convert_exudyn_script.py', encoding='utf-8').read())
"""

def create_mass_spring_damper_model():
    """
    Convert the mass-spring-damper Exudyn script into GUI model items.
    """
    print("🔧 Converting Exudyn script to GUI model...")
    
    # Parameters from your script
    L = 0.5         # spring length (for drawing)
    force = 10
    u0 = 1
    v0 = 1
    mass = 10
    spring = 100
    damper = 20
    
    try:
        # Clear existing model
        print("1. Clearing existing model...")
        clear_model_simple()
        
        # Add ground node
        print("2. Adding ground node...")
        add_ground_node_simple("GroundNode", position=[0, 0, 0])
        
        # Add mass node (Point node with initial conditions)
        print("3. Adding mass node...")
        from model.modelData import modelSequence
        
        mass_node_data = {
            'name': 'MassNode',
            'nodeType': 'NodePoint',
            'referenceCoordinates': [L, 0, 0],
            'initialCoordinates': [u0, 0, 0],
            'initialVelocities': [v0, 0, 0],
        }
        
        mass_node_item = {
            'type': 'NodePoint',
            'data': mass_node_data
        }
        
        modelSequence.append(mass_node_item)
        print(f"   ✅ Added mass node at [{L}, 0, 0] with initial displacement [{u0}, 0, 0]")
        
        # Add mass point object
        print("4. Adding mass point object...")
        mass_object_data = {
            'name': 'MassPoint',
            'nodeNumber': 'nMassNode',  # Reference to the mass node
            'physicsMass': mass,
            'graphicsDataList': [],
        }
        
        mass_object_item = {
            'type': 'ObjectMassPoint',
            'data': mass_object_data
        }
        
        modelSequence.append(mass_object_item)
        print(f"   ✅ Added mass point with mass = {mass}")
        
        # Add markers
        print("5. Adding markers...")
        
        # Ground marker
        ground_marker_data = {
            'name': 'GroundMarker',
            'markerType': 'MarkerNodeCoordinate',
            'nodeNumber': 'nGroundNode',
            'coordinate': 0,  # x-coordinate
        }
        
        ground_marker_item = {
            'type': 'MarkerNodeCoordinate',
            'data': ground_marker_data
        }
        
        modelSequence.append(ground_marker_item)
        
        # Node marker
        node_marker_data = {
            'name': 'NodeMarker',
            'markerType': 'MarkerNodeCoordinate',
            'nodeNumber': 'nMassNode',
            'coordinate': 0,  # x-coordinate
        }
        
        node_marker_item = {
            'type': 'MarkerNodeCoordinate',
            'data': node_marker_data
        }
        
        modelSequence.append(node_marker_item)
        print(f"   ✅ Added ground and node markers")
        
        # Add spring-damper
        print("6. Adding spring-damper...")
        spring_damper_data = {
            'name': 'SpringDamper',
            'markerNumbers': ['mGroundMarker', 'mNodeMarker'],
            'stiffness': spring,
            'damping': damper,
            'offset': 0.0,
        }
        
        spring_damper_item = {
            'type': 'ObjectConnectorCoordinateSpringDamper',
            'data': spring_damper_data
        }
        
        modelSequence.append(spring_damper_item)
        print(f"   ✅ Added spring-damper with k={spring}, d={damper}")
        
        # Add load
        print("7. Adding load...")
        load_data = {
            'name': 'AppliedForce',
            'markerNumber': 'mNodeMarker',
            'load': force,
        }
        
        load_item = {
            'type': 'LoadCoordinate',
            'data': load_data
        }
        
        modelSequence.append(load_item)
        print(f"   ✅ Added load with force = {force}")
        
        # Sync to Exudyn system
        print("8. Syncing to Exudyn system...")
        sync_model_to_exudyn_simple()
        
        # Check results
        status = get_model_status_simple()
        print(f"\n📊 Model Creation Results:")
        print(f"   GUI items: {status.get('modelSequence_length', 0)}")
        print(f"   MBS nodes: {status.get('mbs_nodes', 0)}")
        print(f"   MBS objects: {status.get('mbs_objects', 0)}")
        print(f"   MBS markers: {status.get('mbs_markers', 0)}")
        print(f"   MBS loads: {status.get('mbs_loads', 0)}")
        
        if status.get('mbs_nodes', 0) >= 2 and status.get('mbs_objects', 0) >= 2:
            print("✅ SUCCESS! Mass-spring-damper model created in GUI!")
            print("\n💡 You can now:")
            print("   - Edit parameters in the GUI tree")
            print("   - Add visualization")
            print("   - Run simulation from GUI")
            print("   - Export as complete Exudyn script")
        else:
            print("❌ Model creation had issues - check the GUI tree")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating model: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_simulation_parameters():
    """
    Show how to set up simulation parameters that match the original script.
    """
    print("\n🎯 Simulation Parameters from Original Script:")
    print("=" * 50)
    
    simulation_code = '''
# Simulation settings from your original script:
simulationSettings = exu.SimulationSettings()
simulationSettings.solutionSettings.solutionWritePeriod = 5e-3
simulationSettings.solutionSettings.sensorsWritePeriod = 5e-3
simulationSettings.timeIntegration.numberOfSteps = 1000
simulationSettings.timeIntegration.endTime = 1.0
simulationSettings.displayComputationTime = True
simulationSettings.timeIntegration.verboseMode = 1
simulationSettings.timeIntegration.generalizedAlpha.spectralRadius = 1

# To run simulation with these settings:
exu.StartRenderer()
mbs.WaitForUserToContinue()
exu.SolveDynamic(mbs, simulationSettings)
mbs.WaitForUserToContinue()
exu.StopRenderer()
'''
    
    print(simulation_code)
    print("\n💡 You can run this simulation code in QtConsole after creating the model!")

def convert_any_exudyn_script():
    """
    General guidelines for converting any Exudyn script to GUI model.
    """
    print("\n📚 General Conversion Guidelines:")
    print("=" * 40)
    
    guidelines = '''
🔧 Step-by-Step Conversion Process:

1. **Analyze your script structure:**
   - Identify nodes (mbs.AddNode)
   - Identify objects (mbs.AddObject)
   - Identify markers (mbs.AddMarker)
   - Identify loads/constraints (mbs.AddLoad)

2. **Convert to GUI items:**
   - Each mbs.AddNode() → add_*_node_simple() or direct modelSequence.append()
   - Each mbs.AddObject() → modelSequence.append() with appropriate type
   - Each mbs.AddMarker() → modelSequence.append() with marker type
   - Each mbs.AddLoad() → modelSequence.append() with load type

3. **Handle references:**
   - Use string references like 'nNodeName' for nodeNumber
   - Use string references like 'mMarkerName' for markerNumber
   - GUI will resolve these during sync

4. **Sync to Exudyn:**
   - Always call sync_model_to_exudyn_simple() after adding items
   - This builds the actual Exudyn system from GUI data

5. **Benefits of GUI approach:**
   ✅ Visual editing of parameters
   ✅ Easy modification and experimentation
   ✅ Automatic code generation
   ✅ Model structure visualization
   ✅ Error checking and validation

6. **Example conversion pattern:**
   ```python
   # Original Exudyn:
   n1 = mbs.AddNode(Point(referenceCoordinates=[1,0,0]))
   
   # GUI equivalent:
   node_data = {
       'name': 'Node1',
       'nodeType': 'NodePoint',
       'referenceCoordinates': [1, 0, 0]
   }
   modelSequence.append({'type': 'NodePoint', 'data': node_data})
   ```
'''
    
    print(guidelines)

# Auto-run the conversion when loaded
print("🚀 Exudyn Script to GUI Converter Loaded!")
print("=" * 45)

print("💡 Available Functions:")
print("  create_mass_spring_damper_model()  - Convert the example script")
print("  setup_simulation_parameters()      - Show simulation setup")
print("  convert_any_exudyn_script()        - General conversion guidelines")

print("\n🎯 Quick Start:")
print("  create_mass_spring_damper_model()  # Convert your example to GUI")

print("\n🔧 After conversion, you can:")
print("  - Edit parameters in the GUI tree")
print("  - Visualize the model structure")
print("  - Run simulations")
print("  - Export as Exudyn script")
