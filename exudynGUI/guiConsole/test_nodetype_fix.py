#!/usr/bin/env python3
"""
Test the Fixed nodeType Conversion
=================================

Test if the nodeType conversion fix resolves the AddNode error.
"""

print("🧪 Testing Fixed nodeType Conversion")
print("=" * 40)

# Load the simple workflow
try:
    exec(open('exudynGUI/guiConsole/qtconsole_simple.py', encoding='utf-8').read())
    print("✅ QtConsole integration loaded")
except Exception as e:
    print(f"❌ Failed to load QtConsole integration: {e}")
    exit(1)

# Test the fix
print("\n🔧 Testing nodeType conversion fix...")

try:
    # Clear model
    print("1. Clearing model...")
    clear_model_simple()
    
    # Add a ground node that previously failed with nodeType error
    print("2. Adding NodePointGround (this previously failed)...")
    add_ground_node_simple("TestGround", [0.0, 0.0, 0.0])
    
    # Check what's in the model data
    print("3. Checking node data structure...")
    from model.modelData import modelSequence
    if len(modelSequence) > 0:
        node_data = modelSequence[0].get('data', {})
        print(f"   Node type: {node_data.get('nodeType', 'MISSING')}")
        print(f"   Node name: {node_data.get('name', 'MISSING')}")
        print(f"   Reference coords: {node_data.get('referenceCoordinates', 'MISSING')}")
    
    # Test the sync (this is where the nodeType conversion happens)
    print("4. Testing sync with nodeType conversion...")
    sync_model_to_exudyn_simple()
    
    # Check the results
    print("5. Checking results...")
    after_status = get_model_status_simple()
    print(f"   GUI items: {after_status.get('modelSequence_length', 0)}")
    print(f"   MBS nodes: {after_status.get('mbs_nodes', 0)}")
    
    # Check if the node was created successfully
    if len(modelSequence) > 0:
        node_data = modelSequence[0].get('data', {})
        return_info = node_data.get('returnInfo', 'No info')
        obj_index = node_data.get('objIndex', None)
        
        print(f"\n📊 Node Creation Results:")
        print(f"   Return info: {return_info}")
        print(f"   Object index: {obj_index}")
        
        if "⚠️ Build failed" not in return_info and obj_index is not None:
            print("✅ SUCCESS! NodePointGround created successfully!")
            print("✅ The nodeType conversion fix worked!")
        else:
            print("❌ Node creation still failed")
            print(f"❌ Error: {return_info}")
    
    # Also test a regular Point node
    print("\n6. Testing NodePoint (regular point node)...")
    add_mass_node_simple("TestMass", [1.0, 0.0, 0.0])
    sync_model_to_exudyn_simple()
    
    final_status = get_model_status_simple()
    print(f"   Final MBS nodes: {final_status.get('mbs_nodes', 0)}")
    
    if final_status.get('mbs_nodes', 0) >= 2:
        print("✅ SUCCESS! Multiple node types working!")
    else:
        print("❌ Issues with multiple nodes")
    
except Exception as e:
    print(f"❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()

print("\n🏁 nodeType Conversion Test Complete")
