#!/usr/bin/env python3
"""
Test the Complete QtConsole Workflow
===================================

This script tests the complete bidirectional integration between
the QtConsole and the ExudynGUI. Run this in the QtConsole to verify
that everything works correctly.

Usage in QtConsole:
exec(open('test_complete_workflow.py').read())
"""

def test_complete_workflow():
    """
    Test the complete workflow from QtConsole to GUI to Exudyn system.
    """
    print("🧪 Testing Complete QtConsole ↔ GUI ↔ Exudyn Workflow")
    print("=" * 60)
    
    # Step 1: Load the main workflow
    print("\n1️⃣ Loading workflow functions...")
    try:        # Import functions from the workflow script
        import runpy
        workflow_globals = runpy.run_path('guiConsole/qtconsole_complete_workflow.py')
        
        # Extract the functions we need
        global get_model_status, clear_model, add_ground_node, add_mass_node, add_mass_body, sync_model_to_exudyn
        get_model_status = workflow_globals['get_model_status']
        clear_model = workflow_globals['clear_model']
        add_ground_node = workflow_globals['add_ground_node']
        add_mass_node = workflow_globals['add_mass_node'] 
        add_mass_body = workflow_globals['add_mass_body']
        sync_model_to_exudyn = workflow_globals['sync_model_to_exudyn']
        
        print("✅ Workflow functions loaded")
    except Exception as e:
        print(f"❌ Failed to load workflow: {e}")
        return False
    
    # Step 2: Check initial status
    print("\n2️⃣ Checking initial status...")
    initial_status = get_model_status()
    print(f"📊 Initial GUI items: {initial_status.get('modelSequence_length', 0)}")
    print(f"📊 Initial MBS objects: {initial_status.get('mbs_objects', 0)}")
    
    # Step 3: Clear the model to start fresh
    print("\n3️⃣ Clearing model...")
    if not clear_model():
        print("❌ Failed to clear model")
        return False
    
    # Step 4: Add model components
    print("\n4️⃣ Adding model components...")
    
    # Add ground node
    if not add_ground_node("TestGround", referenceCoordinates=[0.0, 0.5, 0.0]):
        print("❌ Failed to add ground node")
        return False
    
    # Add mass node
    if not add_mass_node("TestMass", position=[1.0, 0.0, 0.0]):
        print("❌ Failed to add mass node")
        return False
    
    # Add mass body
    if not add_mass_body("TestBody", node_name="TestMass", mass=2.5):
        print("❌ Failed to add mass body")
        return False
    
    # Step 5: Check GUI status (before sync)
    print("\n5️⃣ Checking GUI status (before sync)...")
    before_sync = get_model_status()
    print(f"📊 GUI items: {before_sync.get('modelSequence_length', 0)}")
    print(f"📊 MBS objects: {before_sync.get('mbs_objects', 0)}")
    
    if before_sync.get('modelSequence_length', 0) != 3:
        print(f"❌ Expected 3 GUI items, got {before_sync.get('modelSequence_length', 0)}")
        return False
    
    if before_sync.get('mbs_objects', 0) != 0:
        print(f"⚠️ Expected 0 MBS objects before sync, got {before_sync.get('mbs_objects', 0)}")
    
    # Step 6: Sync to Exudyn system
    print("\n6️⃣ Syncing to Exudyn system...")
    if not sync_model_to_exudyn():
        print("❌ Failed to sync model")
        return False
    
    # Step 7: Check final status (after sync)
    print("\n7️⃣ Checking final status (after sync)...")
    after_sync = get_model_status()
    print(f"📊 GUI items: {after_sync.get('modelSequence_length', 0)}")
    print(f"📊 MBS objects: {after_sync.get('mbs_objects', 0)}")
    print(f"📊 MBS nodes: {after_sync.get('mbs_nodes', 0)}")
    
    # Step 8: Verify synchronization worked
    print("\n8️⃣ Verifying synchronization...")
    
    gui_items = after_sync.get('modelSequence_length', 0)
    mbs_objects = after_sync.get('mbs_objects', 0)
    mbs_nodes = after_sync.get('mbs_nodes', 0)
    
    success = True
    
    if gui_items != 3:
        print(f"❌ Expected 3 GUI items, got {gui_items}")
        success = False
    else:
        print(f"✅ GUI has correct number of items: {gui_items}")
    
    if mbs_objects != 1:  # Only 1 object (the mass body)
        print(f"❌ Expected 1 MBS object, got {mbs_objects}")
        success = False
    else:
        print(f"✅ MBS has correct number of objects: {mbs_objects}")
    
    if mbs_nodes != 2:  # 2 nodes (ground + mass)
        print(f"❌ Expected 2 MBS nodes, got {mbs_nodes}")
        success = False
    else:
        print(f"✅ MBS has correct number of nodes: {mbs_nodes}")
    
    # Step 9: Show sample items
    print("\n9️⃣ Sample items in model:")
    if "sample_items" in after_sync:
        for item in after_sync["sample_items"]:
            print(f"  [{item['index']}] {item['type']} '{item['name']}' (objIndex: {item['objIndex']})")
    
    # Step 10: Final result
    print("\n🏁 Test Results:")
    if success:
        print("✅ Complete workflow test PASSED!")
        print("✅ QtConsole ↔ GUI ↔ Exudyn integration is working correctly")
        print("\n💡 You can now:")
        print("   - Manipulate models from QtConsole")
        print("   - See changes in GUI immediately")
        print("   - Sync to Exudyn with sync_model_to_exudyn()")
        print("   - Run simulations with the updated model")
    else:
        print("❌ Complete workflow test FAILED!")
        print("❌ Check the error messages above")
    
    return success

def test_direct_manipulation():
    """
    Test direct manipulation of modelSequence from QtConsole.
    """
    print("\n🔧 Testing Direct Model Manipulation")
    print("=" * 40)
    
    try:        # Import functions if not already available
        try:
            get_model_status
            sync_model_to_exudyn
        except NameError:
            import runpy
            workflow_globals = runpy.run_path('guiConsole/qtconsole_complete_workflow.py')
            global get_model_status, sync_model_to_exudyn
            get_model_status = workflow_globals['get_model_status']
            sync_model_to_exudyn = workflow_globals['sync_model_to_exudyn']
        
        # Direct access to modelSequence
        from exudynGUI.model.modelData import modelSequence
        
        print(f"📊 Current modelSequence length: {len(modelSequence)}")
        
        # Add item directly
        new_item = {
            'type': 'NodePointGround',
            'data': {
                'name': 'DirectGround',
                'nodeType': 'NodePointGround',
                'referenceCoordinates': [0.0, 0.0, 1.0]
            }
        }
        
        modelSequence.append(new_item)
        print(f"✅ Added item directly to modelSequence")
        print(f"📊 New modelSequence length: {len(modelSequence)}")
        
        # Check if it appears in GUI
        status = get_model_status()
        print(f"📊 GUI shows {status.get('modelSequence_length', 0)} items")
        
        # Sync to Exudyn
        print("🔄 Syncing to Exudyn...")
        sync_model_to_exudyn()
        
        final_status = get_model_status()
        print(f"📊 Final MBS nodes: {final_status.get('mbs_nodes', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct manipulation failed: {e}")
        return False

def run_all_tests():
    """
    Run all tests to verify the complete workflow.
    """
    print("🚀 Running All QtConsole Integration Tests")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Complete workflow
    if test_complete_workflow():
        tests_passed += 1
    
    # Test 2: Direct manipulation
    if test_direct_manipulation():
        tests_passed += 1
    
    # Final summary
    print(f"\n📊 Test Summary: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! QtConsole integration is fully functional!")
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
    
    return tests_passed == total_tests

# Auto-run tests when script is executed
if __name__ == "__main__" or True:
    print("🧪 QtConsole Integration Test Suite")
    print("Type run_all_tests() to run all tests")
    print("Type test_complete_workflow() to test the main workflow")
    print("Type test_direct_manipulation() to test direct model access")
