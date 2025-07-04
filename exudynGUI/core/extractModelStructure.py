# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core/extractModelStructure.py
#
# Description:
#     Extracts the complete structure of the current model by collecting
#     all items (nodes, objects, markers, loads, sensors) and analyzing
#     their interconnections. Returns a structured dictionary including
#     graph data and edge lists for visualization and diagnostics.
#
# Authors:  Michael Pieber
# Date:     2025-05-16
# Notes:    Uses networkx to build a graph from model dependencies.
#
# License:  BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



import networkx as nx

def extractModelStructure(mbs, modelSequence=None):
    """Extract structure of the model (nodes, objects, markers, loads, sensors) and their connections."""


    structure = {
        'nodes': [],
        'objects': [],
        'markers': [],
        'loads': [],
        'sensors': [],
        'edges': [],
        'graph': nx.Graph(),
        'categories': {k: {} for k in ['objects', 'nodes', 'markers', 'loads', 'sensors']},
    }
    componentToCreate = {}

    def itemLabel(itemType, index, item=None):
        name = item.get('name', '') if isinstance(item, dict) else ''
        if name:
            if name.startswith("Create"):
                return name
            return f"{itemType}_{name}"
        return f"{itemType}{int(index)}"

    def safeGet(index, getFunc, total):
        index = int(index)
        return getFunc(index) if 0 <= index < total else None

    # === Nodes ===
    for i in range(mbs.systemData.NumberOfNodes()):
        item = mbs.GetNode(i)
        label = itemLabel("Node", i, item)
        structure['nodes'].append({'index': i, 'label': label, 'data': item})
        structure['graph'].add_node(label)

    # === Markers ===
    for i in range(mbs.systemData.NumberOfMarkers()):
        item = mbs.GetMarker(i)
        label = itemLabel("Marker", i, item)
        structure['markers'].append({'index': i, 'label': label, 'data': item})
        structure['graph'].add_node(label)

    # === Objects ===
    for i in range(mbs.systemData.NumberOfObjects()):
        item = mbs.GetObject(i)
        label = itemLabel("Object", i, item)
        structure['objects'].append({'index': i, 'label': label, 'data': item})
        structure['graph'].add_node(label)

        nodeNumbers = []
        if 'nodeNumber' in item:
            nodeNumbers.append(item['nodeNumber'])
        if 'nodeNumbers' in item:
            nodeNumbers += item['nodeNumbers']

        for j in nodeNumbers:
            node = safeGet(j, mbs.GetNode, mbs.systemData.NumberOfNodes())
            if node is not None:
                nodeLabel = itemLabel("Node", j)
                structure['edges'].append((label, nodeLabel, 'Object-Node'))
                structure['graph'].add_edge(label, nodeLabel)

        if 'markerNumbers' in item:
            for j in item['markerNumbers']:
                marker = safeGet(j, mbs.GetMarker, mbs.systemData.NumberOfMarkers())
                if marker is not None:
                    markerLabel = itemLabel("Marker", j, marker)
                    structure['edges'].append((label, markerLabel, 'Object-Marker'))
                    structure['graph'].add_edge(label, markerLabel)

    # === Marker connections ===
    for m in structure['markers']:
        item = m['data']
        label = m['label']

        if 'nodeNumber' in item:
            j = item['nodeNumber']
            node = safeGet(j, mbs.GetNode, mbs.systemData.NumberOfNodes())
            if node is not None:
                nodeLabel = itemLabel("Node", j, node)
                structure['edges'].append((label, nodeLabel, 'Marker-Node'))
                structure['graph'].add_edge(label, nodeLabel)

        for key in ['objectNumber', 'bodyNumber']:
            if key in item:
                j = item[key]
                obj = safeGet(j, mbs.GetObject, mbs.systemData.NumberOfObjects())
                if obj is not None:
                    objLabel = itemLabel("Object", j, obj)
                    structure['edges'].append((label, objLabel, 'Marker-Object'))
                    structure['graph'].add_edge(label, objLabel)

    # === Loads ===
    for i in range(mbs.systemData.NumberOfLoads()):
        item = mbs.GetLoad(i)
        label = itemLabel("Load", i, item)
        structure['loads'].append({'index': i, 'label': label, 'data': item})
        structure['graph'].add_node(label)

        if 'markerNumber' in item:
            j = item['markerNumber']
            marker = safeGet(j, mbs.GetMarker, mbs.systemData.NumberOfMarkers())
            if marker is not None:
                markerLabel = itemLabel("Marker", j, marker)
                structure['edges'].append((label, markerLabel, 'Load-Marker'))
                structure['graph'].add_edge(label, markerLabel)

    # === Sensors ===
    for i in range(mbs.systemData.NumberOfSensors()):
        item = mbs.GetSensor(i)
        label = itemLabel("Sensor", i, item)
        structure['sensors'].append({'index': i, 'label': label, 'data': item})
        structure['graph'].add_node(label)

        for key, prefix in [('objectNumber', 'Object'), ('bodyNumber', 'Object'), ('nodeNumber', 'Node')]:
            if key in item:
                j = item[key]
                if prefix == 'Node':
                    node = safeGet(j, mbs.GetNode, mbs.systemData.NumberOfNodes())
                    if node is not None:
                        refLabel = itemLabel("Node", j, node)
                        structure['edges'].append((label, refLabel, 'Sensor-Node'))
                        structure['graph'].add_edge(label, refLabel)
                else:
                    obj = safeGet(j, mbs.GetObject, mbs.systemData.NumberOfObjects())
                    if obj is not None:
                        refLabel = itemLabel("Object", j, obj)
                        structure['edges'].append((label, refLabel, 'Sensor-Object'))
                        structure['graph'].add_edge(label, refLabel)

    # === Enrich with mapping from Create[i] → component indices ===
    if modelSequence is not None:
        def snapshot():
            return {
                'objects': set(range(mbs.systemData.NumberOfObjects())),
                'nodes': set(range(mbs.systemData.NumberOfNodes())),
                'markers': set(range(mbs.systemData.NumberOfMarkers())),
                'loads': set(range(mbs.systemData.NumberOfLoads())),
                'sensors': set(range(mbs.systemData.NumberOfSensors())),
            }

        prev = snapshot()
        for i, entry in enumerate(modelSequence):
            curr = snapshot()
            diff = {k: curr[k] - prev[k] for k in curr}
            prev = curr

            for compType, newIndices in diff.items():
                for idx in sorted(newIndices):
                    # ✅ Skip if this index was present in the initial snapshot
                    if idx in initialSnapshot[compType]:
                        continue
                    try:
                        data = (
                            mbs.GetObject(idx) if compType == 'objects' else
                            mbs.GetNode(idx) if compType == 'nodes' else
                            mbs.GetMarker(idx) if compType == 'markers' else
                            mbs.GetLoad(idx) if compType == 'loads' else
                            mbs.GetSensor(idx)
                        )
                        structure['categories'][compType][idx] = data.get(f"{compType[:-1]}Type", '?')
                        componentToCreate.setdefault(i, {}).setdefault(compType, set()).add(idx)
                    except:
                        debugLog(f"[WARNING] Could not enrich {compType} {idx} from Create[{i}]")

    return structure, componentToCreate


