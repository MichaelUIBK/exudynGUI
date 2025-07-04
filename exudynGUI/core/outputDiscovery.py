# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/outputDiscovery.py
#
# Description:
#     Utilities for discovering and managing Exudyn OutputVariableType values
#     that are supported by different entity types (objects, nodes, markers, sensors).
#     Provides intelligent output type selection for sensor creation and code generation.
#
# Authors:  Michael Pieber
# Date:     2025-01-21
# Notes:    
#     - Systematically discovers which OutputVariableType values work with each entity
#     - Provides safe output value retrieval and code generation utilities
#     - Integrates with sensor forms for intelligent output type selection
#     - Supports real-time output monitoring and validation
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import exudyn as exu
import numpy as np
import copy
from typing import Dict, List, Tuple, Optional, Any, Union, Set

# Safe debug imports with fallbacks
try:
    from exudynGUI.core.debug import debugInfo, debugWarning, debugError, debugTrace, DebugCategory
    # Ensure OUTPUT category exists
    if not hasattr(DebugCategory, 'OUTPUT'):
        DebugCategory.OUTPUT = "OUTPUT"
except ImportError:
    try:
        from debug import debugInfo, debugWarning, debugError, debugTrace, DebugCategory
        if not hasattr(DebugCategory, 'OUTPUT'):
            DebugCategory.OUTPUT = "OUTPUT"
    except ImportError:
        # Fallback: create no-op debug functions
        def debugInfo(msg, origin=None, category=None): pass
        def debugWarning(msg, origin=None, category=None): pass
        def debugError(msg, origin=None, category=None): pass
        def debugTrace(msg, origin=None, category=None): pass
        class DebugCategory:
            OUTPUT = "OUTPUT"
            FIELD = "FIELD"
            GENERAL = "GENERAL"


class OutputDiscoveryCache:
    """Cache for discovered output types to avoid repeated API calls"""
    def __init__(self):
        self._entity_outputs = {}  # entity_key -> supported_outputs
        self._output_methods = {}  # entity_type -> method_name
        self._configuration_types = None
        
    def get_entity_outputs(self, entity_key: str) -> Optional[List]:
        return self._entity_outputs.get(entity_key)
        
    def set_entity_outputs(self, entity_key: str, outputs: List):
        self._entity_outputs[entity_key] = outputs
        
    def get_output_method(self, entity_type: str) -> Optional[str]:
        return self._output_methods.get(entity_type)
        
    def set_output_method(self, entity_type: str, method_name: str):
        self._output_methods[entity_type] = method_name
        
    def get_configuration_types(self) -> Optional[List]:
        return self._configuration_types
        
    def set_configuration_types(self, config_types: List):
        self._configuration_types = config_types
        
    def clear(self):
        """Clear all cached data"""
        self._entity_outputs.clear()
        self._output_methods.clear()
        self._configuration_types = None


# Global cache instance
_output_cache = OutputDiscoveryCache()

# PRE-COMPUTED OUTPUT MAPPINGS
# These are based on Exudyn documentation and avoid expensive runtime discovery
_STATIC_OUTPUT_MAPPINGS = {}

def get_static_output_mapping(sensor_type: str, object_type: str) -> Optional[List[str]]:
    """
    Get pre-computed output variable types for common object types.
    
    This avoids expensive runtime discovery for common cases and provides
    more accurate results based on Exudyn documentation.
    
    Args:
        sensor_type: Type of sensor (e.g., 'SensorBody')
        object_type: Type of object (e.g., 'MassPoint', 'RigidBody')
    
    Returns:
        List of supported output types or None if no static mapping exists
    """
    key = (sensor_type, object_type)
    mapping = _STATIC_OUTPUT_MAPPINGS.get(key)
    
    if mapping is None:
        # Try fallback to Unknown type
        fallback_key = (sensor_type, 'Unknown')
        mapping = _STATIC_OUTPUT_MAPPINGS.get(fallback_key)
    
    if mapping:
        debugInfo(f"Using static output mapping for {sensor_type} on {object_type}: {mapping}", 
                 origin="get_static_output_mapping", category=DebugCategory.OUTPUT)
    
    return mapping


def get_all_output_variable_types() -> List[str]:
    """Get all available OutputVariableType values from Exudyn"""
    try:
        # Get all OutputVariableType attributes, excluding Python built-ins and properties
        output_types = []
        excluded_attrs = {'name', 'value', '__class__', '__doc__', '__module__'}
        
        for attr_name in dir(exu.OutputVariableType):
            if not attr_name.startswith('_') and attr_name not in excluded_attrs:
                # Additional check: ensure it's actually an OutputVariableType enum value
                try:
                    attr_value = getattr(exu.OutputVariableType, attr_name)
                    # Check if it's an OutputVariableType enum instance (not a property or method)
                    if hasattr(attr_value, '__class__') and 'OutputVariableType' in str(type(attr_value)):
                        output_types.append(attr_name)
                except:
                    # Skip attributes that can't be accessed properly
                    continue
        
        debugTrace(f"Found {len(output_types)} OutputVariableType values", 
                  origin="get_all_output_variable_types", category=DebugCategory.OUTPUT)
        return sorted(output_types)
    except Exception as e:
        debugError(f"Failed to get OutputVariableType values: {e}", 
                  origin="get_all_output_variable_types", category=DebugCategory.OUTPUT)
        return []


def get_all_configuration_types() -> List[str]:
    """Get all available ConfigurationType values from Exudyn"""
    cached = _output_cache.get_configuration_types()
    if cached is not None:
        return cached
        
    try:
        # Get all ConfigurationType attributes
        config_types = []
        for attr_name in dir(exu.ConfigurationType):
            if not attr_name.startswith('_'):
                config_types.append(attr_name)
        
        config_types = sorted(config_types)
        _output_cache.set_configuration_types(config_types)
        
        debugTrace(f"Found {len(config_types)} ConfigurationType values", 
                  origin="get_all_configuration_types", category=DebugCategory.OUTPUT)
        return config_types
    except Exception as e:
        debugError(f"Failed to get ConfigurationType values: {e}", 
                  origin="get_all_configuration_types", category=DebugCategory.OUTPUT)
        return []


def discover_entity_output_methods(mbs) -> Dict[str, str]:
    """Discover which mbs.GetXXXOutput methods are available"""
    cached = {}
    for entity_type in ['node', 'object', 'marker']:
        method = _output_cache.get_output_method(entity_type)
        if method:
            cached[entity_type] = method
    
    if len(cached) == 3:
        return cached
    
    try:
        available_methods = {}
        
        # Check for each output method
        method_mappings = {
            'node': 'GetNodeOutput',
            'object': 'GetObjectOutput', 
            'marker': 'GetMarkerOutput'
        }
        
        for entity_type, method_name in method_mappings.items():
            if hasattr(mbs, method_name):
                available_methods[entity_type] = method_name
                _output_cache.set_output_method(entity_type, method_name)
                debugTrace(f"Found output method: {method_name} for {entity_type}", 
                          origin="discover_entity_output_methods", category=DebugCategory.OUTPUT)
        
        # Also check for specialized object methods
        specialized_methods = ['GetObjectOutputBody', 'GetObjectOutputSuperElement']
        for method_name in specialized_methods:
            if hasattr(mbs, method_name):
                available_methods[f'object_{method_name.lower()}'] = method_name
                debugTrace(f"Found specialized method: {method_name}", 
                          origin="discover_entity_output_methods", category=DebugCategory.OUTPUT)
        
        return available_methods
        
    except Exception as e:
        debugError(f"Failed to discover output methods: {e}", 
                  origin="discover_entity_output_methods", category=DebugCategory.OUTPUT)
        return {}



    

def discover_supported_outputs_via_assembly_test(mbs, entity_type: str, entity_index: int, 
                                                sensor_type: str = 'SensorBody') -> List[str]:
    """
    Return all available OutputVariableType names from Exudyn.
    This does NOT check if they are valid for a specific entity.
    """
    import exudyn as exu
    # Use __members__ if available (most robust)
    if hasattr(exu.OutputVariableType, '__members__'):
        return [k for k in exu.OutputVariableType.__members__.keys() if not k.startswith('_')]
    # Fallback: use dir()
    return [name for name in dir(exu.OutputVariableType)
            if not name.startswith('_') and isinstance(getattr(exu.OutputVariableType, name), int)]

# def discover_supported_outputs_via_assembly_test(mbs, entity_type: str, entity_index: int, 
#                                                 sensor_type: str = 'SensorBody') -> List[str]:
#     """
#     ROBUST DISCOVERY: Test which OutputVariableType values work by testing assembly
    
#     This method first tries to use static pre-computed mappings for common object types.
#     If no static mapping exists, it falls back to expensive runtime discovery.
    
#     Args:
#         mbs: MainSystem instance (used as template to infer entity type)
#         entity_type: 'node', 'object', 'marker', or 'body'
#         entity_index: Index of the entity (used for cache key)
#         sensor_type: Type of sensor to test (default: 'SensorBody')
    
#     Returns:
#         List of supported OutputVariableType names
#     """
#     entity_key = f"assembly_{sensor_type}_{entity_type}_{entity_index}"
       
#     try:
#         # Get the sensor class from itemInterface
#         try:
#             from exudyn.itemInterface import SensorObject, SensorNode, SensorMarker, SensorBody
#             if sensor_type == 'SensorObject':
#                 sensor_class = SensorObject
#             if sensor_type == 'SensorBody':
#                 sensor_class = SensorBody
#             elif sensor_type == 'SensorNode':
#                 sensor_class = SensorNode  
#             elif sensor_type == 'SensorMarker':
#                 sensor_class = SensorMarker
#             else:                # Try to get by dynamic import
#                 import exudyn.itemInterface as itemInterface
#                 sensor_class = getattr(itemInterface, sensor_type, None)
#                 if sensor_class is None:
#                     raise AttributeError(f"Sensor type {sensor_type} not found")
#         except (ImportError, AttributeError) as e:
#             debugError(f"Could not find sensor class {sensor_type}: {e}", 
#                       origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#             return []
        
#         supported_outputs = []
#         output_types = get_all_output_variable_types()
        
#         debugInfo(f"Testing {len(output_types)} output types for {sensor_type} on {entity_type}[{entity_index}] via assembly test", 
#                  origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
        
#         # Test each OutputVariableType by creating a fresh system
#         for output_type_name in output_types:
#             try:
#                 output_type_value = getattr(exu.OutputVariableType, output_type_name)
                
#                 # Create a fresh test system for each OutputVariableType
#                 # This avoids the deep copying problems we discovered
#                 SC_test = exu.SystemContainer()
#                 mbs_test = SC_test.AddSystem()
                
#                 # Instead of creating a generic entity, try to recreate the same type as the original
#                 test_entity_index = None
                
#                 if entity_type in ['object', 'body']:
#                     try:
#                         # Try to get the actual object type from the original system
#                         obj_dict = mbs.GetObject(entity_index)
#                         object_type = obj_dict.get('objectType', 'MassPoint')

#                         debugTrace(f"Original object[{entity_index}] is type: {object_type}", 
#                                   origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)

#                         # Create the same type of object in test system
#                         if object_type == 'MassPoint':
#                             test_entity = mbs_test.CreateMassPoint(
#                                 referencePosition=[0.0, 0.0, 0.0],
#                                 physicsMass=1.0,
#                                 returnDict=True
#                             )
#                             test_entity_index = test_entity['bodyNumber']
#                         elif object_type == 'RigidBody':
#                             test_entity = mbs_test.CreateRigidBody(
#                                 referencePosition=[0.0, 0.0, 0.0],
#                                 referenceRotationMatrix=np.eye(3),
#                                 inertia=exu.utilities.InertiaSphere(mass=1.0, radius=0.1),
#                                 returnDict=True
#                             )
#                             test_entity_index = test_entity['bodyNumber']
#                         else:
#                             # For other types, create a generic MassPoint as fallback
#                             debugTrace(f"Unknown object type {object_type}, using MassPoint fallback", 
#                                       origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                             test_entity = mbs_test.CreateMassPoint(
#                                 referencePosition=[0.0, 0.0, 0.0],
#                                 physicsMass=1.0,
#                                 returnDict=True
#                             )
#                             test_entity_index = test_entity['bodyNumber']
#                     except Exception as e:
#                         debugTrace(f"Could not inspect original object[{entity_index}]: {e}, using MassPoint fallback", 
#                                   origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                         # Fallback: create generic MassPoint
#                         test_entity = mbs_test.CreateMassPoint(
#                             referencePosition=[0.0, 0.0, 0.0],
#                             physicsMass=1.0,
#                             returnDict=True                        )
#                         test_entity_index = test_entity['bodyNumber']
                        
#                 elif entity_type == 'node':
#                     # Create a simple node for testing node sensors
#                     from exudyn.itemInterface import NodePoint
#                     test_entity_index = mbs_test.AddNode(NodePoint(referenceCoordinates=[0, 0, 0]))
#                 elif entity_type == 'marker':
#                     # Create a node and marker for testing marker sensors
#                     from exudyn.itemInterface import NodePoint, MarkerNodePosition
#                     node_index = mbs_test.AddNode(NodePoint(referenceCoordinates=[0, 0, 0]))
#                     test_entity_index = mbs_test.AddMarker(MarkerNodePosition(nodeNumber=node_index))
#                 else:
#                     # Skip unsupported entity types
#                     debugWarning(f"Entity type {entity_type} not supported in assembly test yet", 
#                                origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                     continue
                
#                 # Prepare sensor configuration based on sensor type
#                 if sensor_type == 'SensorBody':
#                     sensor_config = sensor_class(
#                         name=f'TestSensor_{output_type_name}',
#                         bodyNumber=test_entity_index,
#                         outputVariableType=output_type_value
#                     )
#                 elif sensor_type == 'SensorNode':
#                     sensor_config = sensor_class(
#                         name=f'TestSensor_{output_type_name}',
#                         nodeNumber=test_entity_index,
#                         outputVariableType=output_type_value
#                     )
#                 elif sensor_type == 'SensorMarker':
#                     sensor_config = sensor_class(
#                         name=f'TestSensor_{output_type_name}',
#                         markerNumber=test_entity_index,
#                         outputVariableType=output_type_value
#                     )
#                 else:
#                     debugWarning(f"Unknown sensor type: {sensor_type}", 
#                                origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                     continue
                
#                 # Add the test sensor
#                 # Try to add sensor *and* assemble it—catch any Exudyn error
#                 try:
#                     sensor_index = mbs_test.AddSensor(sensor_config)
#                     mbs_test.Assemble()
#                     supported_outputs.append(output_type_name)
#                     debugTrace(f"✓ {sensor_type} on {entity_type}[{entity_index}] supports {output_type_name}", 
#                                origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                 except BaseException as e:
#                     # Skip *any* failure from AddSensor or Assemble (including RuntimeError)
#                     debugTrace(f"✗ {sensor_type} on {entity_type}[{entity_index}] skipping {output_type_name}: {str(e)[:80]}", 
#                                origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                     continue
                
#             except Exception as e:
#                 # Sensor creation or other error
#                 debugTrace(f"✗ {sensor_type} on {entity_type}[{entity_index}] failed for {output_type_name}: {str(e)[:80]}", 
#                           origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#                 continue          # Cache the results
#         _output_cache.set_entity_outputs(entity_key, supported_outputs)
        
#         # Provide a clear summary message
#         total_tested = len(output_types)
#         successful = len(supported_outputs)
#         failed = total_tested - successful
        
#         debugInfo(f"Output discovery completed for {sensor_type} on {entity_type}[{entity_index}]: " +
#                  f"{successful}/{total_tested} types supported, {failed} expected failures. " +
#                  f"Supported: {supported_outputs}", 
#                  origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
        
#         return supported_outputs
        
#     except Exception as e:
#         debugError(f"Failed to discover outputs via assembly test for {entity_type}[{entity_index}]: {e}", 
#                   origin="discover_supported_outputs_via_assembly_test", category=DebugCategory.OUTPUT)
#         return []


def discover_supported_outputs_via_sensor(mbs, entity_type: str, entity_index: int,
                                        sensor_type: str = 'SensorBody') -> List[str]:
    """
    ROBUST DISCOVERY: Test which OutputVariableType values work by actually trying to create sensors
    
    This is the most reliable method as it directly tests what the sensor creation function accepts.
    Unlike GetObjectOutput* methods which have signature issues, this approach is bulletproof.
    
    Args:
        mbs: MainSystem instance
        entity_type: 'node', 'object', 'marker', or 'body'
        entity_index: Index of the entity
        sensor_type: Type of sensor to test (default: 'SensorBody')
    
    Returns:
        List of supported OutputVariableType names
    """
    entity_key = f"sensor_{sensor_type}_{entity_type}_{entity_index}"
    
    # Check cache first
    cached = _output_cache.get_entity_outputs(entity_key)
    if cached is not None:
        debugInfo(f"Using cached outputs for {entity_key}: {len(cached)} types", 
                 origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
        return cached
    
    try:
        supported_outputs = []
        output_types = get_all_output_variable_types()
        
        debugInfo(f"Testing {len(output_types)} output types for {sensor_type} on {entity_type}[{entity_index}] via sensor creation", 
                 origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
        
        # Get the sensor class from itemInterface
        try:
            from exudyn.itemInterface import SensorObject, SensorNode, SensorMarker
            
            if sensor_type == 'SensorBody':
                # SensorBody is actually SensorObject for bodies/objects
                sensor_class = SensorObject
            elif sensor_type == 'SensorNode':
                sensor_class = SensorNode  
            elif sensor_type == 'SensorMarker':
                sensor_class = SensorMarker
            else:                # Try to get by dynamic import
                import exudyn.itemInterface as itemInterface
                sensor_class = getattr(itemInterface, sensor_type, None)
                if sensor_class is None:
                    raise AttributeError(f"Sensor type {sensor_type} not found")
        except (ImportError, AttributeError) as e:
            debugError(f"Could not find sensor class {sensor_type}: {e}", 
                      origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
            return []
        
        for output_type_name in output_types:
            try:
                output_type_value = getattr(exu.OutputVariableType, output_type_name)
                
                # Skip enum properties that aren't numeric values (e.g., 'name', 'value')
                if not isinstance(output_type_value, int):
                    continue
                
                # Prepare sensor configuration based on sensor type
                if sensor_type == 'SensorBody':
                    # For SensorBody (actually SensorObject), we need objectNumber and outputVariableType
                    sensor_config = sensor_class(
                        objectNumber=entity_index,
                        outputVariableType=output_type_value
                    )
                elif sensor_type == 'SensorNode':
                    # For SensorNode, we need nodeNumber and outputVariableType
                    sensor_config = sensor_class(
                        nodeNumber=entity_index,
                        outputVariableType=output_type_value
                    )
                elif sensor_type == 'SensorMarker':
                    # For SensorMarker, we need markerNumber and outputVariableType
                    sensor_config = sensor_class(
                        markerNumber=entity_index,
                        outputVariableType=output_type_value
                    )
                else:
                    debugWarning(f"Unknown sensor type: {sensor_type}", 
                               origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
                    continue
                
                # Try to add the sensor - if it succeeds, the output type is supported
                # Don't remove sensors since RemoveSensor doesn't exist
                sensor_index = mbs.AddSensor(sensor_config)
                
                # CRITICAL: Also test if we can actually get meaningful values from the sensor
                # This catches cases where sensor creation succeeds but getting values fails
                try:
                    # First try Reference configuration (doesn't require solve)
                    try:
                        test_values = mbs.GetSensorValues(sensor_index, exu.ConfigurationType.Reference)
                        config_used = "Reference"
                    except:
                        # If Reference fails, try Current (may require solving, but let's test)
                        test_values = mbs.GetSensorValues(sensor_index, exu.ConfigurationType.Current)
                        config_used = "Current"
                    
                    # Success! This output type is truly supported
                    supported_outputs.append(output_type_name)
                    debugTrace(f"✓ {sensor_type} on {entity_type}[{entity_index}] supports {output_type_name} -> sensor[{sensor_index}] ({config_used}) -> {test_values}", 
                              origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
                    
                except Exception as sensor_value_error:
                    # Sensor creation succeeded but getting values failed -> not truly supported
                    debugTrace(f"✗ {sensor_type} on {entity_type}[{entity_index}] sensor creation OK but values failed for {output_type_name}: {str(sensor_value_error)[:80]}", 
                              origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
                    continue
                
            except Exception as e:
                # Output type not supported - this is expected for many types
                debugTrace(f"✗ {sensor_type} on {entity_type}[{entity_index}] does not support {output_type_name}: {str(e)[:80]}", 
                          origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
                continue
        
        # Cache the results
        _output_cache.set_entity_outputs(entity_key, supported_outputs)
        
        debugInfo(f"Discovered {len(supported_outputs)} supported outputs for {sensor_type} on {entity_type}[{entity_index}]: {supported_outputs}", 
                 origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
        
        return supported_outputs
        
    except Exception as e:
        debugError(f"Failed to discover outputs via sensor for {entity_type}[{entity_index}]: {e}", 
                  origin="discover_supported_outputs_via_sensor", category=DebugCategory.OUTPUT)
        return []


def discover_supported_outputs(mbs, entity_type: str, entity_index: int, 
                             configuration_type: str = 'Current', sensor_type: str = None) -> List[str]:
    """
    Discover which OutputVariableType values are supported for a specific entity
    
    This is the main entry point for output discovery. It uses the most robust method available.
    For best results, provide sensor_type (e.g., 'SensorBody') to get accurate validation.
    
    Args:
        mbs: MainSystem instance
        entity_type: 'node', 'object', 'marker', or 'body'
        entity_index: Index of the entity
        configuration_type: ConfigurationType to use (default: 'Current') - used for cache key
        sensor_type: Type of sensor (e.g., 'SensorBody') for robust validation
    
    Returns:
        List of supported OutputVariableType names
    """
    # For robust discovery, use assembly-based method when sensor_type is provided
    # For robust discovery, use the generic sensor-creation test when sensor_type is provided
    if sensor_type:
        return discover_supported_outputs_via_sensor(mbs, entity_type, entity_index, sensor_type)    
    
    entity_key = f"{entity_type}_{entity_index}_{configuration_type}_{sensor_type or 'default'}"
    
    # Check cache first
    cached = _output_cache.get_entity_outputs(entity_key)
    if cached is not None:
        return cached
    
    try:
        # Determine the correct output method based on sensor type and entity type
        method_name = None
        
        if sensor_type == 'SensorBody' or entity_type == 'body':
            # For SensorBody, use GetObjectOutputBody
            if hasattr(mbs, 'GetObjectOutputBody'):
                method_name = 'GetObjectOutputBody'
                entity_type_for_method = 'object'  # Still pass object index
            else:
                debugWarning(f"GetObjectOutputBody not available", 
                           origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
                return []
        else:
            # Get the appropriate output method for other types
            methods = discover_entity_output_methods(mbs)
            method_name = methods.get(entity_type)
        
        if not method_name:
            debugWarning(f"No output method found for entity type: {entity_type}, sensor_type: {sensor_type}", 
                        origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
            return []
        
        method = getattr(mbs, method_name)
        config_value = getattr(exu.ConfigurationType, configuration_type)
        
        # Test each OutputVariableType
        supported_outputs = []
        output_types = get_all_output_variable_types()
        
        debugInfo(f"Testing {len(output_types)} output types for {entity_type}[{entity_index}] using {method_name}", 
                 origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
        
        for output_type_name in output_types:
            try:
                output_type_value = getattr(exu.OutputVariableType, output_type_name)
                
                # Try to get output - if it works, the output type is supported
                result = method(entity_index, output_type_value, config_value)
                supported_outputs.append(output_type_name)
                
                debugTrace(f"✓ {entity_type}[{entity_index}] supports {output_type_name} -> {type(result).__name__}", 
                          origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
                
            except Exception as e:
                # Output type not supported - this is expected for many types
                debugTrace(f"✗ {entity_type}[{entity_index}] does not support {output_type_name}: {str(e)[:50]}", 
                          origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
                continue
        
        # Cache the results
        _output_cache.set_entity_outputs(entity_key, supported_outputs)
        
        debugInfo(f"Discovered {len(supported_outputs)} supported outputs for {entity_type}[{entity_index}] using {method_name}: {supported_outputs}", 
                 origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
        
        return supported_outputs
        
    except Exception as e:
        debugError(f"Failed to discover outputs for {entity_type}[{entity_index}]: {e}", 
                  origin="discover_supported_outputs", category=DebugCategory.OUTPUT)
        return []


def get_entity_output_safely(mbs, entity_type: str, entity_index: int, 
                           output_type: str, configuration_type: str = 'Current') -> Tuple[bool, Any, str]:
    """
    Safely retrieve output value for an entity
    
    Args:
        mbs: MainSystem instance
        entity_type: 'node', 'object', or 'marker'
        entity_index: Index of the entity
        output_type: OutputVariableType name
        configuration_type: ConfigurationType name
    
    Returns:
        Tuple of (success, value, error_message)
    """
    try:
        # Get the appropriate output method
        methods = discover_entity_output_methods(mbs)
        method_name = methods.get(entity_type)
        
        if not method_name:
            return False, None, f"No output method found for entity type: {entity_type}"
        
        method = getattr(mbs, method_name)
        output_value = getattr(exu.OutputVariableType, output_type)
        config_value = getattr(exu.ConfigurationType, configuration_type)
        
        result = method(entity_index, output_value, config_value)
        return True, result, ""
        
    except Exception as e:
        return False, None, str(e)


def generate_output_access_code(entity_type: str, entity_index: Union[int, str], 
                              output_type: str, configuration_type: str = 'Current',
                              variable_name: Optional[str] = None) -> str:
    """
    Generate Python code for accessing entity output
    
    Args:
        entity_type: 'node', 'object', or 'marker'
        entity_index: Index of the entity (can be int or symbolic variable name)
        output_type: OutputVariableType name
        configuration_type: ConfigurationType name
        variable_name: Optional variable name for assignment
    
    Returns:
        Generated Python code string
    """
    try:
        # Determine method name
        method_mappings = {
            'node': 'GetNodeOutput',
            'object': 'GetObjectOutput',
            'marker': 'GetMarkerOutput'
        }
        
        method_name = method_mappings.get(entity_type, 'GetObjectOutput')
        
        # Format the code
        if isinstance(entity_index, str) and not entity_index.isdigit():
            # Symbolic reference
            index_ref = entity_index
        else:
            # Numeric index
            index_ref = str(entity_index)
        
        code_line = f"mbs.{method_name}({index_ref}, exu.OutputVariableType.{output_type}, exu.ConfigurationType.{configuration_type})"
        
        if variable_name:
            code_line = f"{variable_name} = {code_line}"
        
        return code_line
        
    except Exception as e:
        debugError(f"Failed to generate output access code: {e}", 
                  origin="generate_output_access_code", category=DebugCategory.OUTPUT)
        return f"# Error generating code: {e}"


def create_output_monitoring_code(entities: List[Dict], output_types: List[str],
                                configuration_type: str = 'Current') -> str:
    """
    Generate code for monitoring multiple entity outputs
    
    Args:
        entities: List of entity dicts with 'type', 'index', 'name' keys
        output_types: List of OutputVariableType names to monitor
        configuration_type: ConfigurationType name
    
    Returns:
        Generated monitoring code
    """
    lines = []
    lines.append("# Output monitoring code")
    lines.append("import exudyn as exu")
    lines.append("")
    
    for entity in entities:
        entity_type = entity.get('type', 'object')
        entity_index = entity.get('index', 0)
        entity_name = entity.get('name', f"{entity_type}_{entity_index}")
        
        lines.append(f"# Monitor {entity_name} ({entity_type}[{entity_index}])")
        
        for output_type in output_types:
            var_name = f"{entity_name}_{output_type.lower()}"
            code_line = generate_output_access_code(
                entity_type, entity_index, output_type, configuration_type, var_name
            )
            lines.append(code_line)
        
        lines.append("")
    
    return "\n".join(lines)


def enhance_sensor_form_with_outputs(mbs, sensor_object_type: str, 
                                   referenced_entity: Dict) -> Dict[str, Any]:
    """
    Enhance sensor form with intelligent output type selection
    
    Args:
        mbs: MainSystem instance
        sensor_object_type: Type of sensor being created
        referenced_entity: Dict with 'type' and 'index' of referenced entity
    
    Returns:
        Dict with output type options and recommendations
    """
    try:
        entity_type = referenced_entity.get('type', 'object')
        entity_index = referenced_entity.get('index', 0)
        
        # Discover supported outputs for the referenced entity
        supported_outputs = discover_supported_outputs(mbs, entity_type, entity_index)
        
        # Get configuration types
        config_types = get_all_configuration_types()
        
        # Provide recommendations based on sensor type
        recommendations = _get_output_recommendations(sensor_object_type, supported_outputs)
        
        return {
            'supported_outputs': supported_outputs,
            'configuration_types': config_types,
            'recommendations': recommendations,
            'default_output': recommendations[0] if recommendations else (supported_outputs[0] if supported_outputs else 'Position'),
            'default_config': 'Current'
        }
        
    except Exception as e:
        debugError(f"Failed to enhance sensor form: {e}", 
                  origin="enhance_sensor_form_with_outputs", category=DebugCategory.OUTPUT)
        return {
            'supported_outputs': [],
            'configuration_types': ['Current'],
            'recommendations': [],
            'default_output': 'Position',
            'default_config': 'Current'
        }


def _get_output_recommendations(sensor_type: str, available_outputs: List[str]) -> List[str]:
    """Get recommended output types for a sensor type"""
    recommendations_map = {
        'SensorObject': ['Position', 'Velocity', 'Displacement', 'Acceleration'],
        'SensorNode': ['Position', 'Velocity', 'Displacement', 'Coordinates'],
        'SensorMarker': ['Position', 'Velocity', 'Displacement'],
        'SensorBody': ['Position', 'Velocity', 'AngularVelocity', 'Rotation'],
        'SensorLoad': ['Force', 'Torque'],
        'SensorKinematicTree': ['Position', 'Velocity', 'Rotation'],
    }
    
    base_recommendations = recommendations_map.get(sensor_type, ['Position', 'Velocity'])
    
    # Filter to only include available outputs
    return [rec for rec in base_recommendations if rec in available_outputs]


def generate_sensor_creation_code(sensor_type: str, sensor_name: str, 
                                entity_reference: str, output_type: str,
                                configuration_type: str = 'Current',
                                additional_params: Optional[Dict] = None) -> str:
    """
    Generate code for creating a sensor with output monitoring
    
    Args:
        sensor_type: Exudyn sensor type (e.g., 'SensorObject')
        sensor_name: Variable name for the sensor
        entity_reference: Reference to the entity being monitored
        output_type: OutputVariableType name
        configuration_type: ConfigurationType name
        additional_params: Optional additional sensor parameters
    
    Returns:
        Generated sensor creation code
    """
    lines = []
    lines.append(f"# Create {sensor_type} for monitoring {output_type}")
    
    # Build sensor parameters
    params = []
    
    # Add entity reference based on sensor type
    if sensor_type in ['SensorObject', 'SensorBody']:
        params.append(f"objectNumber={entity_reference}")
    elif sensor_type == 'SensorNode':
        params.append(f"nodeNumber={entity_reference}")
    elif sensor_type == 'SensorMarker':
        params.append(f"markerNumber={entity_reference}")
    
    # Add output type and configuration
    params.append(f"outputVariableType=exu.OutputVariableType.{output_type}")
    
    if configuration_type != 'Current':
        params.append(f"configurationType=exu.ConfigurationType.{configuration_type}")
    
    # Add any additional parameters
    if additional_params:
        for key, value in additional_params.items():
            if isinstance(value, str) and not value.startswith('exu.'):
                value = f"'{value}'"
            params.append(f"{key}={value}")
    
    # Generate the sensor creation code
    params_str = ",\n    ".join(params)
    lines.append(f"{sensor_name} = mbs.AddSensor(exu.{sensor_type}(")
    lines.append(f"    {params_str}")
    lines.append("))")
    
    return "\n".join(lines)


def create_output_utilities_code() -> str:
    """Generate reusable output utility functions for inclusion in generated code"""
    return '''
# Output Discovery Utilities
def get_entity_output(mbs, entity_type, entity_index, output_type, config_type='Current'):
    """Safely get output from an entity"""
    try:
        if entity_type == 'node':
            method = mbs.GetNodeOutput
        elif entity_type == 'object':
            method = mbs.GetObjectOutput
        elif entity_type == 'marker':
            method = mbs.GetMarkerOutput
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
        
        output_val = getattr(exu.OutputVariableType, output_type)
        config_val = getattr(exu.ConfigurationType, config_type)
        
        return method(entity_index, output_val, config_val)
    except Exception as e:
        print(f"Error getting {output_type} from {entity_type}[{entity_index}]: {e}")
        return None

def monitor_outputs(mbs, entities, output_types, config_type='Current'):
    """Monitor multiple outputs from multiple entities"""
    results = {}
    for entity in entities:
        entity_key = f"{entity['type']}_{entity['index']}"
        results[entity_key] = {}
        for output_type in output_types:
            value = get_entity_output(mbs, entity['type'], entity['index'], output_type, config_type)
            results[entity_key][output_type] = value
    return results
'''


def clear_output_cache():
    """Clear the output discovery cache"""
    _output_cache.clear()
    debugInfo("Output discovery cache cleared", origin="clear_output_cache", category=DebugCategory.OUTPUT)


# Export main functions
__all__ = [
    'get_all_output_variable_types',
    'get_all_configuration_types', 
    'discover_entity_output_methods',
    'discover_supported_outputs',
    'get_entity_output_safely',
    'generate_output_access_code',
    'create_output_monitoring_code',
    'enhance_sensor_form_with_outputs',
    'generate_sensor_creation_code',
    'create_output_utilities_code',
    'clear_output_cache',
    'OutputDiscoveryCache'
]

def discover_sensor_body_outputs(mbs, body_index: int) -> List[str]:
    """
    Convenience function to discover supported OutputVariableType values for SensorBody
    
    This is the RECOMMENDED function for GUI forms and sensor creation.
    Uses optimized static mappings when possible, with runtime discovery as fallback.
    
    Args:
        mbs: MainSystem instance
        body_index: Index of the body/object
    
    Returns:
        List of supported OutputVariableType names for SensorBody
    """
    return discover_supported_outputs_via_assembly_test(mbs, 'object', body_index, 'SensorBody')


def discover_sensor_node_outputs(mbs, node_index: int) -> List[str]:
    """
    Convenience function to discover supported OutputVariableType values for SensorNode
    
    Uses the robust assembly-based discovery method for maximum accuracy.
    
    Args:
        mbs: MainSystem instance
        node_index: Index of the node
    
    Returns:
        List of supported OutputVariableType names for SensorNode
    """
    return discover_supported_outputs_via_assembly_test(mbs, 'node', node_index, 'SensorNode')


def discover_sensor_marker_outputs(mbs, marker_index: int) -> List[str]:
    """
    Convenience function to discover supported OutputVariableType values for SensorMarker
    
    Uses the robust assembly-based discovery method for maximum accuracy.
    
    Args:
        mbs: MainSystem instance        marker_index: Index of the marker
    
    Returns:
        List of supported OutputVariableType names for SensorMarker
    """
    return discover_supported_outputs_via_assembly_test(mbs, 'marker', marker_index, 'SensorMarker')
