# -*- coding: utf-8 -*-
"""
Flexible Body (FEM/FFRF) utilities for Exudyn GUI

This module provides functions to:
- Generate or import a mesh (Netgen/NGsolve)
- Set up FEMinterface and compute modes
- Create FFRF/CMS elements and add them to an Exudyn system
- Keep all FEM/FFRF logic separate from the main GUI

Usage:
    from functions.flexibleBody import create_flexible_body_from_ngsolve
    fem_result = create_flexible_body_from_ngsolve(params)
    # fem_result contains fem, objFFRF, markers, sensors, etc.

Author: GitHub Copilot
Date: 2025-06-06
"""

import exudyn as exu
import numpy as np

# Optional: Only import these if available
try:
    import ngsolve as ngs
    from netgen.csg import CSGeometry, OrthoBrick, Pnt
except ImportError:
    ngs = None
    CSGeometry = OrthoBrick = Pnt = None

from exudyn.FEM import FEMinterface, HCBstaticModeSelection, KirchhoffMaterial


def create_flexible_body_from_ngsolve(
    mbs,
    a=0.025,
    L=1.0,
    h=0.5*0.025,
    nModes=8,
    rho=1000,
    Emodulus=1e8,
    nu=0.3,
    meshOrder=1,
    useGraphics=True,
    computeStressModes=True,
    boundaryPlane='left',
    verbose=True
):
    """
    Create a flexible body (CMS/FFRF) from a simple brick mesh using Netgen/NGsolve.
    Returns a dict with fem, objFFRF, markers, sensors, etc.
    """
    if ngs is None:
        raise ImportError("ngsolve and netgen must be installed for flexible body support.")

    # --- Mesh generation ---
    geo = CSGeometry()
    block = OrthoBrick(Pnt(0, -a, -a), Pnt(L, a, a))
    geo.Add(block)
    mesh = ngs.Mesh(geo.GenerateMesh(maxh=h))
    mesh.Curve(1)

    # --- FEM import ---
    fem = FEMinterface()
    fem.ImportMeshFromNGsolve(mesh, density=rho, youngsModulus=Emodulus, poissonsRatio=nu, meshOrder=meshOrder)

    # --- Boundary nodes for HCB ---
    pLeft = [0, -a, -a]
    nodesLeftPlane = fem.GetNodesInPlane(pLeft, [-1, 0, 0])
    weightsLeftPlane = fem.GetNodeWeightsFromSurfaceAreas(nodesLeftPlane)
    boundaryList = [nodesLeftPlane]

    if verbose:
        debugLog("nNodes=", fem.NumberOfNodes())
        debugLog("compute HCB modes... ")
    fem.ComputeHurtyCraigBamptonModes(
        boundaryNodesList=boundaryList,
        nEigenModes=nModes,
        useSparseSolver=True,
        computationMode=HCBstaticModeSelection.RBE2
    )

    # --- Optional: Compute stress modes ---
    # Disabled due to NGSolve mesh 'ndof' attribute error in some versions
    # if computeStressModes:
    #     mat = KirchhoffMaterial(Emodulus, nu, rho)
    #     varType = exu.OutputVariableType.StressLocal
    #     if verbose:
    #         print("ComputePostProcessingModes ... (may take a while)")
    #     fem.ComputePostProcessingModesNGsolve(mesh, material=mat, outputVariableType=varType)

    # --- Create CMS element ---
    cms = exu.FEM.ObjectFFRFreducedOrderInterface(fem)
    objFFRF = cms.AddObjectFFRFreducedOrder(
        mbs,
        positionRef=[0, 0, 0],
        initialVelocity=[0, 0, 0],
        initialAngularVelocity=[0, 0, 0],
        gravity=[0, -9.81, 0],
        color=[0.1, 0.9, 0.1, 1.]
    )

    # --- Add markers and joints ---
    mRB = mbs.AddMarker({'markerType': 'NodeRigid', 'nodeNumber': objFFRF['nRigidBody']})
    oGround = mbs.AddObject({'objectType': 'Ground', 'referencePosition': [0, 0, 0]})
    leftMidPoint = [0, 0, 0]
    mGround = mbs.AddMarker({'markerType': 'BodyRigid', 'bodyNumber': oGround, 'localPosition': leftMidPoint})
    mLeft = mbs.AddMarker({'markerType': 'SuperElementRigid',
        'bodyNumber': objFFRF['oFFRFreducedOrder'],
        'meshNodeNumbers': list(nodesLeftPlane),
        'weightingFactors': weightsLeftPlane,
        'offset': [0, 0, 0]
    })
    mbs.AddObject({'objectType': 'GenericJoint',
        'markerNumbers': [mGround, mLeft],
        'constrainedAxes': [1, 1, 1, 1, 1, 0],
        'visualization': {'axesRadius': 0.1*a, 'axesLength': 0.1*a}
    })

    # --- Add sensor ---
    nTip = fem.GetNodeAtPoint([L, -a, -a])
    fileDir = 'solution/'
    sensTipDispl = mbs.AddSensor({'sensorType': 'SuperElement',
        'bodyNumber': objFFRF['oFFRFreducedOrder'],
        'meshNodeNumber': nTip,
        'fileName': fileDir + f'nMidDisplacementCMS{nModes}Test.txt',
        'outputVariableType': exu.OutputVariableType.Displacement
    })

    # --- Return all relevant objects ---
    return {
        'fem': fem,
        'objFFRF': objFFRF,
        'markers': {
            'mRB': mRB,
            'mGround': mGround,
            'mLeft': mLeft
        },
        'oGround': oGround,
        'sensor': sensTipDispl
    }
