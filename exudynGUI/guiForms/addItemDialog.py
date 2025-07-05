# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This file is part of the Exudyn GUI project.
#
# Filename: guiForms/addGraphicsDialog.py
#
# Description:
#     Provides the AddGraphicsDialog class for selecting a graphics constructor
#     from the available `exudyn.graphics` functions.
#
#     The dialog offers a categorized and searchable interface to browse graphics
#     constructors (e.g., Sphere, Arrow, SolidExtrusion) for use in graphicsDataList.
#
#     Key Features:
#     - Categorized view of constructors, based on predefined semantic groups
#     - Live filtering via search input
#     - Descriptive tooltips for each constructor
#     - Visual feedback for selected constructor
#     - Emits `constructorSelected` signal upon confirmation
#
#     Used as the entry point for adding visualization components to Exudyn items
#     via the GUI (e.g., Ground, MassPoint).
#
# Author:    Michael Pieber
# Created:   2025-05-21
# License:   BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Import debug system first
try:
    import exudynGUI.core.debug as debug
    # Legacy compatibility for existing debugLog calls
    def debugLog(msg, origin=None):
        if "Warning" in msg or "Error" in msg:
            debug.debugWarning(msg, origin=origin, category=debug.DebugCategory.GUI)
        else:
            debug.debugInfo(msg, origin=origin, category=debug.DebugCategory.GUI)
    def debugInfo(msg, origin=None, category=None):
        return debug.debugInfo(msg, origin, category)
    def debugWarning(msg, origin=None, category=None):
        return debug.debugWarning(msg, origin, category)
except ImportError:
    # Fallback if debug module not available
    def debugLog(msg, origin=None):
        pass
    def debugInfo(msg, origin=None, category=None):
        pass
    def debugWarning(msg, origin=None, category=None):
        pass

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QLineEdit, QWidget, QScrollArea, QSizePolicy, QToolButton
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon
from exudynGUI.model.objectRegistry import getCategorizedRegistry
import exudyn as exu
import inspect
from exudynGUI.core.helpUtils import get_full_exudyn_help

# Import help system components
try:
    from theDocHelper.theDocFieldHelp import (
        loadBookmarks, findFunctionPageInCreateSection, findCreateSectionPages, SectionPdfImageDialog,
        findCategorySectionPages, getLegacyItemPageRange, getCreateItemPageRange
    )
    HELP_AVAILABLE = True
    debugLog("[Help] PDF help system loaded successfully")
except ImportError as e:
    HELP_AVAILABLE = False
    debugLog(f"[Help] Warning: PDF help system not available - {e}")
except Exception as e:
    HELP_AVAILABLE = False
    debugLog(f"[Help] Warning: Error loading PDF help system - {e}")

from pathlib import Path
thisFile = Path(__file__).resolve()
projectRoot = thisFile.parents[2]  # mainExudynGUI_V0.03
pdfPath = projectRoot / 'exudynGUI' / 'theDocHelper' / 'theDoc.pdf'

# Example icon paths (replace with your own icons or resource system)
CATEGORY_ICONS = {
    "Create (Helpers)": "",  # e.g. ":/icons/create.png"
    "Nodes": "Nodes.png",
    "Objects (Body)": "Objects (Body).png",
    "Objects (SuperElement)": "Objects (SuperElement).png",
    "Objects (FiniteElement)": "Objects (FiniteElement).png",
    "Objects (Joint)": "Objects (Joint).png",
    "Objects (Connector)": "Objects (Connector).png",
    "Objects (Constraint)": "Objects (Constraint).png",
    "Objects (Object)": "Objects (Object).png",
    "Markers": "Markers.png",
    "Loads": "Loads.png",
    "Sensors": "Sensors.png",
}

# Global dictionaries for category descriptions
CATEGORY_DESCRIPTIONS = {
    "Create (Helpers)": "High-level creation functions that automatically handle complex setups",
    "Nodes": "Fundamental points in space with coordinates and degrees of freedom",
    "Objects (Body)": "Physical bodies including rigid bodies, ground, and mass points",
    "Objects (SuperElement)": "Super elements for flexible multibody dynamics (FFRF, reduced order models)",
    "Objects (FiniteElement)": "Finite elements like cables, beams, plates, and continuum elements",
    "Objects (Joint)": "Joint objects including spherical, revolute, prismatic, and generic joints",
    "Objects (Connector)": "Connector objects like springs, dampers, and actuators between bodies",
    "Objects (Constraint)": "Constraint objects for enforcing kinematic and algebraic constraints",
    "Objects (Object)": "Generic and specialized objects for specific modeling needs",
    "Markers": "Attachment points on bodies for constraints, loads, and sensors",
    "Loads": "Applied forces, torques, and distributed loads on the system",
    "Sensors": "Measurement sensors for monitoring system behavior during simulation",
}

# Store full PDF descriptions for help dialogs
FULL_CATEGORY_DESCRIPTIONS = {}

# Icon mappings and descriptions for Create functions (from ribbon configuration)
CREATE_FUNCTION_ICONS = {
    "CreateGround": "Ground.png",
    "CreateMassPoint": "MassPoint.png", 
    "CreateRigidBody": "RigidBody.png",
    "CreateDistanceConstraint": "DistanceConstraint.png",
    "CreateSpringDamper": "SpringDamper.png",
    "CreateCartesianSpringDamper": "CartesianSpringDamper.png",
    "CreateRigidBodySpringDamper": "RigidBodySpringDamper.png",
    "CreateCoordinateConstraint": "CoordinateConstraint.png",
    "CreateTorsionalSpringDamper": "TorsionalSpringDamper.png",
    "CreatePrismaticJoint": "PrismaticJoint.png",
    "CreateRevoluteJoint": "RevoluteJoint.png",
    "CreateSphericalJoint": "SphericalJoint.png",
    "CreateGenericJoint": "GenericJoint.png",
    "CreateRollingDisc": "RollingDisc.png",
    "CreateRollingDiscPenalty": "RollingDiscPenalty.png",
    "CreateForce": "Force.png",
    "CreateTorque": "Torque.png",
    "CreateDistanceSensor": "DistanceSensor.png",
    "CreateDistanceSensorGeometry": "DistanceSensorGeometry.png",
    "CreateKinematicTree": "KinematicTree.png",
    "CreateSphereTriangleContact": "SphereTriangleContact.png",
    "CreateSphereQuadContact": "SphereQuadContact.png",
    "CreateSphereSphereContact": "SphereSphereContact.png",
}

CREATE_FUNCTION_DESCRIPTIONS = {
    "CreateGround": "Creates a fixed ground body that cannot move. Use as a reference for constraints and connections.",
    "CreateMassPoint": "Creates a point mass with translational degrees of freedom. Ideal for simple particles or concentrated masses.",
    "CreateRigidBody": "Creates a rigid body with full 6-DOF motion (3 translation + 3 rotation). The fundamental building block for multibody systems.",
    "CreateDistanceConstraint": "Constrains the distance between two points to be constant. Creates a rigid connection.",
    "CreateSpringDamper": "Creates a spring-damper element between two points. Provides force proportional to distance and velocity.",
    "CreateCartesianSpringDamper": "Creates a 3D Cartesian spring-damper with separate stiffness and damping in X, Y, Z directions.",
    "CreateRigidBodySpringDamper": "Creates a 6-DOF spring-damper between rigid bodies with translational and rotational components.",
    "CreateCoordinateConstraint": "Constrains a coordinate (position, velocity, or acceleration) to follow a prescribed motion or value.",
    "CreateTorsionalSpringDamper": "Creates a torsional spring-damper element providing rotational stiffness and damping between bodies.",
    "CreatePrismaticJoint": "Creates a prismatic (sliding) joint allowing translation along one axis while constraining rotation.",
    "CreateRevoluteJoint": "Creates a revolute (hinge) joint allowing rotation about one axis while constraining translation.",
    "CreateSphericalJoint": "Creates a spherical (ball) joint allowing 3-DOF rotation while constraining translation.",
    "CreateGenericJoint": "Creates a generic joint with customizable constraints for complex kinematic relationships.",
    "CreateRollingDisc": "Creates a rolling disc constraint that enforces no-slip rolling contact between a disc and surface.",
    "CreateRollingDiscPenalty": "Creates a penalty-based rolling disc constraint with configurable contact stiffness and damping.",
    "CreateForce": "Applies a force vector to a point on a body. Can be constant, time-dependent, or user-defined.",
    "CreateTorque": "Applies a torque (moment) vector to a rigid body. Used for rotational actuation and loading.",
    "CreateDistanceSensor": "Creates a sensor to measure distance between two points during simulation.",
    "CreateDistanceSensorGeometry": "Creates a geometric distance sensor for complex distance measurements between bodies.",
    "CreateKinematicTree": "Creates a kinematic tree structure for efficient multi-body dynamics with tree topology.",
    "CreateSphereTriangleContact": "Creates contact between a sphere and triangular mesh geometry with collision detection and response.",
    "CreateSphereQuadContact": "Creates contact between a sphere and quadrilateral mesh geometry for surface contact modeling.",
    "CreateSphereSphereContact": "Creates contact between two spheres with collision detection, penetration handling, and contact forces.",
}


# Store full PDF descriptions for help dialogs
FULL_CATEGORY_DESCRIPTIONS = {}

# Initialize CATEGORY_TO_TYPES at import time so it is never None
from exudynGUI.model.objectRegistry import getCategorizedRegistry
CATEGORY_TO_TYPES = getCategorizedRegistry()

def updateCategoryDescriptionsWithPdf():
    """Update CATEGORY_DESCRIPTIONS with rich content extracted from PDF."""
    global CATEGORY_DESCRIPTIONS, FULL_CATEGORY_DESCRIPTIONS, pdfPath
    
    # Check if descriptions are already loaded (e.g., during startup)
    if FULL_CATEGORY_DESCRIPTIONS:
        debugLog("[Help] Category descriptions already loaded globally, skipping extraction")
        return
    
    if not HELP_AVAILABLE or not pdfPath or not pdfPath.exists():
        debugLog("[Help] PDF help not available, using default category descriptions")
        return
    
    try:
        pdf_descriptions = extractCategoryDescriptionsFromPdf()
        # Update both dictionaries
        for category, pdf_desc in pdf_descriptions.items():
            if category in CATEGORY_DESCRIPTIONS:
                # Store full description for help dialogs
                FULL_CATEGORY_DESCRIPTIONS[category] = pdf_desc
                
                # Use a short version for the UI buttons
                short_pdf_desc = pdf_desc
                
                # Truncate long descriptions to keep UI clean
                if len(short_pdf_desc) > 50:
                    # Take first part up to first period or 50 chars, whichever comes first
                    first_sentence = short_pdf_desc.split('.')[0]
                    if len(first_sentence) <= 50:
                        short_pdf_desc = first_sentence + "."
                    else:
                        short_pdf_desc = short_pdf_desc[:47] + "..."
                
                CATEGORY_DESCRIPTIONS[category] = short_pdf_desc
                debugLog(f"[Help] Updated description for {category}")
        
        debugLog(f"[Help] Updated {len(pdf_descriptions)} category descriptions with PDF content")
        
    except Exception as e:
        debugLog(f"[Help] Failed to update category descriptions from PDF: {e}")

def extractCategoryDescriptionsFromPdf():
    """Extract rich category descriptions from the PDF sections."""
    global pdfPath
    try:
        import fitz
        import re
        
        if not pdfPath:
            debugLog("[Help] PDF path not available")
            return {}
            
        pdf_path = str(pdfPath)
        if not Path(pdf_path).exists():
            debugLog(f"[Help] PDF not found at: {pdf_path}")
            return {}
        
        # Use loadBookmarks to get consistent format
        from exudynGUI.theDocHelper.theDocFieldHelp import loadBookmarks
        bookmarks = loadBookmarks(pdf_path)
        
        # Mapping of GUI categories to exact PDF bookmark names and section patterns
        category_to_pdf_patterns = {
            "Nodes": ["8.1", "Nodes", "8.1 Nodes"],  # Chapter 8.1 Nodes
            "Objects (Body)": ["8.2", "Objects (Body)", "8.2 Objects (Body)", "Objects (Bodies)"],
            "Objects (SuperElement)": ["Objects (SuperElement)", "SuperElement"],
            "Objects (FiniteElement)": ["Objects (FiniteElement)", "FiniteElement"],
            "Objects (Joint)": ["Objects (Joint)", "Joint"],
            "Objects (Connector)": ["Objects (Connector)", "Connector"],
            "Objects (Constraint)": ["Objects (Constraint)", "Constraint"],
            "Objects (Object)": ["Objects (Object)", "Object"],
            "Markers": ["Markers", "8.9", "8.9 Markers"],  # Chapter 8.3 Markers
            "Loads": ["Loads", "8.10", "8.10 Loads"],  # Chapter 8.4 Loads
            "Sensors": ["Sensors", "8.11", "8.11 Sensors"],  # Chapter 8.5 Sensors
        }
        
        extracted_descriptions = {}
        
        for category, patterns in category_to_pdf_patterns.items():
            debugLog(f"[Help] Looking for category: {category}")
            
            # Find the bookmark for this section
            section_page = None
            best_match = None
            
            for bm in bookmarks:
                title = bm.get('title', '')
                page = bm.get('page', 0)
                
                # Look for exact matches first (prioritize chapter numbers)
                for pattern in patterns:
                    if pattern.startswith("8.") and pattern in title:  # Chapter 8.x numbers
                        section_page = page
                        best_match = title
                        debugLog(f"[Help] Found exact match '{title}' at page {page}")
                        break
                    elif pattern == title:  # Exact title match
                        # For "Nodes", prioritize the Chapter 8 version (page 456) over Chapter 2 (page 44)
                        if category == "Nodes" and page > 400:  # Chapter 8 starts around page 455
                            section_page = page
                            best_match = title
                            debugLog(f"[Help] Found exact match '{title}' at page {page}")
                            break
                        elif category != "Nodes" and not section_page:  # For other categories, take first match
                            section_page = page
                            best_match = title
                            debugLog(f"[Help] Found exact match '{title}' at page {page}")
                            break
                
                if section_page:
                    break
            
            if not section_page:
                debugLog(f"[Help] No PDF section found for category: {category}")
                continue
            
            # Extract text from the page
            doc = fitz.open(pdf_path)
            try:
                page_obj = doc.load_page(section_page - 1)  # 0-based
                text = page_obj.get_text("text")
                lines = text.split('\n')
                
                # Find the section header and extract the following paragraph
                description_lines = []
                found_header = False
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    
                    # Skip empty lines
                    if not line:
                        continue
                    
                    # Look for the specific section header
                    if not found_header:
                        # For Nodes, look for Chapter 8.1 patterns
                        if category == "Nodes":
                            header_conditions = [
                                "8.1" in line and "Nodes" in line,  # "8.1 Nodes" 
                                line.strip() == "Nodes" and any("8.1" in prev_line for prev_line in lines[max(0, i-2):i]),
                                # Special case: if we see "Nodes" header directly after seeing "8.1"
                                line.strip() == "Nodes" and i > 0 and "8.1" in lines[i-1]
                            ]
                        else:
                            # For other categories, look for Chapter 8.x patterns
                            header_conditions = []
                            for pattern in patterns:
                                if pattern.startswith("8."):  # Chapter numbers
                                    header_conditions.append(pattern in line and category.split("(")[0].strip() in line)
                                else:
                                    header_conditions.append(pattern in line)
                        
                        if any(header_conditions):
                            found_header = True
                            debugLog(f"[Help] Found header: '{line}'")
                            continue
                    
                    # Once we found the header, start collecting description
                    if found_header:
                        # Stop conditions for description
                        stop_conditions = [
                            # Another section starting
                            re.match(r'^\d+\.\d+', line),  # Pattern like "2.2.2", "8.1.1"
                            # Additional information sections
                            any(keyword in line.lower() for keyword in [
                                'additional information', 'example:', 'python:', 'see also:',
                                'note:', 'miniexample:', 'output:', 'belongs to:', 'figure'
                            ]),
                            # Page numbers or single digits (but not category titles)
                            line.isdigit(),
                            # Very short lines that are not category titles like "Nodes"
                            len(line) < 10 and line not in ["Nodes", "Markers", "Loads", "Sensors"]
                        ]
                        
                        if any(stop_conditions):
                            break
                        
                        # Clean the line
                        clean_line = re.sub(r'\s+', ' ', line)
                        description_lines.append(clean_line)
                        
                        # Stop after collecting enough content (first paragraph)
                        full_text = ' '.join(description_lines)
                        if len(full_text) > 100 and ('. ' in full_text):
                            # Stop after first complete sentence if we have enough content
                            break
                
                # Process the collected description
                if description_lines:
                    full_description = ' '.join(description_lines)
                    
                    # Clean up common PDF artifacts
                    full_description = re.sub(r'\s+', ' ', full_description)
                    full_description = full_description.replace(' ,', ',')
                    full_description = full_description.replace(' .', '.')
                    full_description = full_description.replace('( ', '(')
                    full_description = full_description.replace(' )', ')')
                    # Fix hyphenated words
                    full_description = re.sub(r'-\s+([a-z])', r'\1', full_description)
                    
                    # Take only the first sentence or two for conciseness
                    sentences = re.split(r'[.!?]+\s+', full_description)
                    if sentences and sentences[0]:
                        clean_description = sentences[0].strip()
                        
                        # Include second sentence if first is short
                        if len(clean_description) < 80 and len(sentences) > 1 and sentences[1]:
                            clean_description += '. ' + sentences[1].strip()
                        
                        if not clean_description.endswith('.'):
                            clean_description += '.'
                        
                        extracted_descriptions[category] = clean_description
                        debugLog(f"[Help] Extracted for {category}: '{clean_description[:60]}...'")
                
            except Exception as e:
                debugLog(f"[Help] Error extracting description for {category}: {e}")
            finally:
                doc.close()
        
        debugLog(f"[Help] Extracted descriptions for {len(extracted_descriptions)} categories")
        return extracted_descriptions
        
    except Exception as e:
        debugLog(f"[Help] Error extracting category descriptions: {e}")
        return {}

class AddModelElementDialog(QDialog):
    typeSelected = pyqtSignal(str)
    
    def __init__(self, parent=None, mode="all", pdfBookmarks=None, pdfPath=None):
        super().__init__(parent)
        self.setWindowTitle("Add Model Element")
        self.resize(600, 400)
        self.selectedCategory = None
        self._selectedType = None
        self.mode = mode  # 'create', 'legacy', or 'all'
        self.pdfBookmarks = pdfBookmarks
        self.pdfPath = pdfPath

        # Initialize help system with provided or loaded bookmarks/path
        if not self.pdfBookmarks or not self.pdfPath:
            # Try to use global values first
            try:
                import main
                global_bookmarks = main.getGlobalPdfBookmarks()
                global_path = main.getGlobalPdfPath()
                
                if global_bookmarks and global_path:
                    self.pdfBookmarks = global_bookmarks
                    self.pdfPath = global_path
                    debugLog(f"[Help] Using global PDF bookmarks: {len(self.pdfBookmarks)} bookmarks from {self.pdfPath}")
                    # Don't fall back to loading - use globals or nothing
                else:
                    debugLog("[Help] No global PDF bookmarks available")
                    self.pdfBookmarks = []
                    self.pdfPath = None
            except Exception as e:
                debugLog(f"[Help] Failed to get global bookmarks: {e}")
                self.pdfBookmarks = []
                self.pdfPath = None
        else:
            debugLog(f"[Help] Using provided PDF bookmarks and path: {self.pdfPath}")
        
        # Only update category descriptions once if we have PDF access and they're not already loaded
        if HELP_AVAILABLE and self.pdfBookmarks and self.pdfPath and not FULL_CATEGORY_DESCRIPTIONS:
            updateCategoryDescriptionsWithPdf()
        elif FULL_CATEGORY_DESCRIPTIONS:
            debugLog("[Help] Category descriptions already loaded globally, skipping extraction")
        
        self._buildUI()
        # If mode is 'create', immediately show Create (Helpers) types
        if self.mode == "create":
            self._showTypes("Create (Helpers)")

    def selectedType(self):
        return self._selectedType

    def _buildUI(self):
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        # Search bar
        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Search model element...")
        self.searchBar.textChanged.connect(self._onSearch)
        self.layout.addWidget(self.searchBar)

        # Main area: category view
        self.categoryWidget = QWidget()
        self.categoryLayout = QGridLayout(self.categoryWidget)
        self.categoryLayout.setSpacing(16)
        self.layout.addWidget(self.categoryWidget)
        self._populateCategories()

        # Type area (hidden by default)
        self.typeWidget = QWidget()
        self.typeLayout = QGridLayout(self.typeWidget)
        self.typeLayout.setSpacing(12)
        self.typeWidget.setVisible(False)
        self.layout.addWidget(self.typeWidget)

        # Back button
        self.backButton = QPushButton("← Back")
        self.backButton.clicked.connect(self._showCategories)
        self.backButton.setVisible(False)
        self.layout.addWidget(self.backButton)

    def _populateCategories(self):        # Remove old buttons
        for i in reversed(range(self.categoryLayout.count())):
            w = self.categoryLayout.itemAt(i).widget()
            if w:
                w.setParent(None)
        
        # Determine which categories to show
        cats = []
        global CATEGORY_TO_TYPES
        CATEGORY_TO_TYPES = getCategorizedRegistry()  # Always up-to-date
        
        if self.mode == "create":
            cats = ["Create (Helpers)"]
        elif self.mode == "legacy":
            cats = [k for k in CATEGORY_TO_TYPES if k != "Create (Helpers)"]
        else:  # 'all'
            cats = list(CATEGORY_TO_TYPES.keys())
        
        for idx, cat in enumerate(cats):
            icon_filename = CATEGORY_ICONS.get(cat, "")
            
            # Create main button
            btn = QPushButton()
            btn.setText(cat)
            
            # Set icon if available for legacy categories
            if icon_filename:
                import os
                icon_path = os.path.join(os.path.dirname(__file__), "..", "design", "legacyItems", icon_filename)
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(32, 32))  # Smaller icon for the dialog
            
            # Set rich tooltip with description
            if cat in CATEGORY_DESCRIPTIONS:
                clean_name = cat.replace("Objects (", "").replace(")", "") if "Objects (" in cat else cat
                rich_tooltip = f"""
                <div style="max-width: 300px;">
                    <h3 style="margin-bottom: 5px; color: #2c3e50;">{clean_name}</h3>
                    <p style="margin: 0; line-height: 1.4; color: #34495e;">
                        {CATEGORY_DESCRIPTIONS[cat]}
                    </p>
                    <hr style="margin: 8px 0; border: none; border-top: 1px solid #bdc3c7;">
                    <small style="color: #7f8c8d;">Click to browse {clean_name} components</small>
                </div>
                """
                btn.setToolTip(rich_tooltip)
            else:
                btn.setToolTip(cat)
            
            btn.setMinimumHeight(48)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked, c=cat: self._showTypes(c))
            
            # Create help button (same style as CREATE function help buttons)
            help_btn = QToolButton()
            help_btn.setText("?")
            help_btn.setToolTip(f"Show help for {cat}")
            help_btn.setFixedSize(24, 24)
            help_btn.setStyleSheet("""
                QToolButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QToolButton:hover {
                    background-color: #45a049;
                }
                QToolButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            help_btn.clicked.connect(lambda checked, c=cat: self._showCategoryHelp(c))
            
            # Layout: main button and help button in a horizontal layout (same as CREATE functions)
            buttonLayout = QHBoxLayout()
            buttonLayout.addWidget(btn, 1)  # Main button takes most space
            buttonLayout.addWidget(help_btn, 0)  # Help button fixed size
            buttonLayout.setContentsMargins(0, 0, 0, 0)
            buttonLayout.setSpacing(4)
            
            # Create button widget (same as CREATE functions)
            buttonWidget = QWidget()
            buttonWidget.setLayout(buttonLayout)
            
            self.categoryLayout.addWidget(buttonWidget, idx // 2, idx % 2)

    def _showCategories(self):
        self.typeWidget.setVisible(False)
        self.backButton.setVisible(False)
        self.categoryWidget.setVisible(True)
        self.selectedCategory = None
        self.searchBar.setText("")

    def _showTypes(self, category):
        self.selectedCategory = category
        self.categoryWidget.setVisible(False)
        self.typeWidget.setVisible(True)
        self.backButton.setVisible(True)
        self._populateTypes(category)

    def _populateTypes(self, category):
        # Remove old
        for i in reversed(range(self.typeLayout.count())):
            w = self.typeLayout.itemAt(i).widget()
            if w:
                w.setParent(None)
        # Add type cards
        global CATEGORY_TO_TYPES
        if CATEGORY_TO_TYPES is None:
            CATEGORY_TO_TYPES = getCategorizedRegistry()
        if category == "Create (Helpers)":
            # Dynamically get Create* functions with proper icons and descriptions
            types = []
            for f in CATEGORY_TO_TYPES[category]:
                icon_filename = CREATE_FUNCTION_ICONS.get(f, "")
                description = CREATE_FUNCTION_DESCRIPTIONS.get(f, f"Create: {f}")
                types.append({"name": f, "desc": description, "icon": icon_filename})
        else:
            types = [{"name": t, "desc": t, "icon": ""} for t in CATEGORY_TO_TYPES.get(category, [])]
        
        for idx, t in enumerate(types):
            # Main button for selecting the type
            btn = QPushButton()
            btn.setText(t["name"])
            
            # Set icon if available for Create functions
            if t["icon"]:
                import os
                icon_path = os.path.join(os.path.dirname(__file__), "..", "design", "createItems", t["icon"])
                if os.path.exists(icon_path):
                    btn.setIcon(QIcon(icon_path))
                    btn.setIconSize(QSize(32, 32))  # Smaller icon for the dialog
                    
            # Set tooltip with description
            if category == "Create (Helpers)" and t["name"] in CREATE_FUNCTION_DESCRIPTIONS:
                clean_name = t["name"].replace("Create", "")
                rich_tooltip = f"""
                <div style="max-width: 300px;">
                    <h3 style="margin-bottom: 5px; color: #2c3e50;">{clean_name}</h3>
                    <p style="margin: 0; line-height: 1.4; color: #34495e;">
                        {CREATE_FUNCTION_DESCRIPTIONS[t["name"]]}
                    </p>
                    <hr style="margin: 8px 0; border: none; border-top: 1px solid #bdc3c7;">
                    <small style="color: #7f8c8d;">Click to create {clean_name} in your model</small>
                </div>
                """
                btn.setToolTip(rich_tooltip)
            else:
                btn.setToolTip(t["desc"])
            
            btn.setMinimumHeight(48)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.clicked.connect(lambda checked, name=t["name"]: self._selectType(name))
            
            # Help button
            helpBtn = QToolButton()
            helpBtn.setText("?")
            helpBtn.setToolTip(f"Show help for {t['name']}")
            helpBtn.setFixedSize(24, 24)
            helpBtn.setStyleSheet("""
                QToolButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QToolButton:hover {
                    background-color: #45a049;
                }
                QToolButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            helpBtn.clicked.connect(lambda checked, name=t["name"]: self._showHelp(name))
              # Layout: main button and help button in a horizontal layout
            buttonLayout = QHBoxLayout()
            buttonLayout.addWidget(btn, 1)  # Main button takes most space
            buttonLayout.addWidget(helpBtn, 0)  # Help button fixed size
            buttonLayout.setContentsMargins(0, 0, 0, 0)
            buttonLayout.setSpacing(4)
            
            # Clean layout without description text
            buttonWidget = QWidget()
            buttonWidget.setLayout(buttonLayout)
            
            self.typeLayout.addWidget(buttonWidget, idx // 2, idx % 2)

    def _onSearch(self, text):
        text = text.lower().strip()
        
        if not self.selectedCategory:
            # Filter categories
            for i in range(self.categoryLayout.count()):
                w = self.categoryLayout.itemAt(i).widget()
                if w:
                    label = w.layout().itemAt(0).widget().text().lower()
                    visible = text in label if text else True
                    w.setVisible(visible)
        else:
            # Filter types - check each widget in the type layout
            for i in range(self.typeLayout.count()):
                item = self.typeLayout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    typeName = ""
                    typeDesc = ""
                    
                    # Extract the type name and description from the widget structure
                    # Structure: widget -> vbox -> [buttonWidget, descLabel]
                    layout = widget.layout()
                    if layout and layout.count() >= 2:
                        # Get button widget (contains button and help button)
                        buttonWidget = layout.itemAt(0).widget()
                        if buttonWidget and buttonWidget.layout():
                            # Get the main button (first widget in horizontal layout)
                            mainButton = buttonWidget.layout().itemAt(0).widget()
                            if mainButton:
                                typeName = mainButton.text()
                        
                        # Get description label
                        descLabel = layout.itemAt(1).widget()
                        if descLabel:
                            typeDesc = descLabel.text()
                        
                        # Check if search text matches type name or description
                        if typeName and typeDesc:
                            visible = (text in typeName.lower() or                                     text in typeDesc.lower()) if text else True
                            widget.setVisible(visible)
                        else:
                            # Fallback: show all if we can't extract text or no search text
                            widget.setVisible(True)
                    else:
                        # Fallback for unexpected structure
                        widget.setVisible(True)    
    def _selectType(self, typeName):
        self._selectedType = typeName
        self.typeSelected.emit(typeName)
        # Defensive: only close if not already closed
        if self.isVisible():
            self.accept()  # Always close the dialog when a type is selected

    def getSelectedType(self):
        return self._selectedType
        
    def _showHelp(self, typeName):
        import exudyn as exu
        import inspect
        try:
            if typeName.startswith("Create"):
                func = getattr(exu.MainSystem, typeName, None)
                if func is None:
                    func = getattr(exu, typeName, None)
                help_lines = []
                help_lines.append(f"Exudyn {typeName} - High-Level Creation Function")
                help_lines.append("=" * 60)
                help_lines.append("")
                try:
                    sig = inspect.signature(func)
                    help_lines.append("Function signature:")
                    help_lines.append(f"  {typeName}{sig}")
                    help_lines.append("")
                except Exception:
                    pass
                doc = func.__doc__
                if not doc:
                    import io
                    from contextlib import redirect_stdout
                    f = io.StringIO()
                    with redirect_stdout(f):
                        help(func)
                    doc = f.getvalue()
                if doc:
                    help_lines.append(doc.strip())
                help_lines.append("")
                help_lines.append("Usage Note:")
                help_lines.append("This is a high-level creation function that automatically handles")
                help_lines.append("the creation of nodes, objects, markers, and constraints as needed.")
                help_lines.append("")
                help_lines.append("For more detailed documentation, use the PDF help button.")
                help_text = '\n'.join(help_lines)
            else:
                help_text = self._getLegacyHelpFromMetadata(typeName)
            # Try to find PDF help if available
            page_range = None
            has_pdf_help = False
            if HELP_AVAILABLE and hasattr(self, 'pdfBookmarks') and self.pdfBookmarks:
                if typeName.startswith(("Object", "Node", "Marker", "Load", "Sensor")):
                    from theDocHelper.theDocFieldHelp import getLegacyItemPageRange
                    start_page, end_page = getLegacyItemPageRange(self.pdfPath, self.pdfBookmarks, typeName)
                    if start_page and end_page:
                        page_range = list(range(start_page, end_page + 1))
                        has_pdf_help = True
                elif typeName.startswith("Create"):
                    from theDocHelper.theDocFieldHelp import getCreateItemPageRange
                    start_page, end_page = getCreateItemPageRange(self.pdfPath, self.pdfBookmarks, typeName)
                    if start_page and end_page:
                        page_range = list(range(start_page, end_page + 1))
                        has_pdf_help = True
            from PyQt5.QtWidgets import QMessageBox, QTextEdit, QDialog, QVBoxLayout, QPushButton, QHBoxLayout, QLabel
            help_dialog = QDialog(self)
            help_dialog.setWindowTitle(f"Help: {typeName}")
            help_dialog.setModal(True)
            help_dialog.resize(800, 600)
            layout = QVBoxLayout(help_dialog)
            header = QLabel(f"<b>Exudyn Internal Documentation for {typeName}</b>")
            header.setStyleSheet("padding: 10px; background-color: #e8f4fd; border: 1px solid #b3d9ff;")
            layout.addWidget(header)
            text_edit = QTextEdit()
            text_edit.setPlainText(help_text)
            text_edit.setReadOnly(True)
            text_edit.setFont(self.font())
            layout.addWidget(text_edit)
            button_layout = QHBoxLayout()
            if has_pdf_help and page_range:
                page_count = len(page_range)
                pdf_btn = QPushButton(f"📖 View PDF Documentation ({page_count} pages)")
                pdf_btn.clicked.connect(lambda: self._showPdfHelp(page_range))
                button_layout.addWidget(pdf_btn)
            button_layout.addStretch()
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(help_dialog.accept)
            button_layout.addWidget(close_btn)
            layout.addLayout(button_layout)
            help_dialog.exec_()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Help Error", f"Error showing help for {typeName}:\n{str(e)}")
    
    def _showPdfHelp(self, page_range):
        """Display PDF documentation for the specified page range."""
        try:
            if not HELP_AVAILABLE:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "PDF Help", "PDF help system is not available.")
                return
                
            if not hasattr(self, 'pdfPath') or not self.pdfPath:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "PDF Help", "PDF documentation path is not available.")
                return
                
            # Use SectionPdfImageDialog to display the PDF pages
            dialog = SectionPdfImageDialog(str(self.pdfPath), page_range, parent=self)
            dialog.exec_()
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "PDF Help Error", f"Error displaying PDF help:\n{str(e)}")

    def _showCategoryHelp(self, category):
        """Show help dialog for a main category with both PDF description and parameter information."""
        try:
            # Get full description from the global full category descriptions
            full_description = FULL_CATEGORY_DESCRIPTIONS.get(category, 
                CATEGORY_DESCRIPTIONS.get(category, f"Information about {category} category."))
            
            # Create comprehensive help dialog like the old system
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel
            
            help_dialog = QDialog(self)
            help_dialog.setWindowTitle(f"Help: {category}")
            help_dialog.resize(800, 600)  # Make it larger for full content
            
            layout = QVBoxLayout(help_dialog)
            
            # Title
            title_label = QLabel(f"<h2>{category}</h2>")
            layout.addWidget(title_label)
            
            # Create comprehensive help content
            help_content = []
            
            # Add PDF description first
            if full_description:
                help_content.append(full_description)
                help_content.append("")
            
            # Add parameter information if this is a category with types
            if category in CATEGORY_TO_TYPES:
                types_list = CATEGORY_TO_TYPES[category]
                if types_list and len(types_list) > 0:
                    help_content.append("Available Types in this Category:")
                    help_content.append("=" * 40)
                    
                    # Show a few example types with their parameters
                    for i, type_name in enumerate(types_list[:5]):  # Show first 5 types
                        help_content.append(f"\n{i+1}. {type_name}")
                        
                        # Try to get parameter info for this type
                        try:
                            from core.fieldMetadata import FieldMetadataBuilder
                            builder = FieldMetadataBuilder(useExtracted=True)
                            metadata = builder.build(type_name)
                            
                            if metadata and len(metadata) > 0:
                                param_count = 0
                                for field_name, field_info in metadata.items():
                                    if param_count >= 3:  # Limit parameters per type
                                        remaining = len(metadata) - param_count
                                        if remaining > 0:
                                            help_content.append(f"   ... and {remaining} more parameters")
                                        break
                                    
                                    field_type = field_info.get('type', 'unknown')
                                    default_val = field_info.get('defaultValue', field_info.get('default', ''))
                                    desc = field_info.get('description', '')
                                    
                                    help_content.append(f"   • {field_name}: {field_type}")
                                    if default_val not in [None, '']:
                                        help_content.append(f"     Default: {default_val}")
                                    if desc:
                                        clean_desc = desc.replace('\\n', ' ').replace('  ', ' ').strip()
                                        if len(clean_desc) > 60:
                                            clean_desc = clean_desc[:57] + "..."
                                        help_content.append(f"     {clean_desc}")
                                    
                                    param_count += 1
                        except Exception:
                            help_content.append("   (Parameter information not available)")
                    
                    if len(types_list) > 5:
                        help_content.append(f"\n... and {len(types_list) - 5} more types in this category.")
                    
                    help_content.append("")
                    help_content.append("💡 Tip: Use the PDF help button for detailed documentation with examples.")
            
            # Display content
            desc_edit = QTextEdit()
            desc_edit.setPlainText('\n'.join(help_content))
            desc_edit.setReadOnly(True)
            desc_edit.setFont(self.font())  # Use same font as dialog
            layout.addWidget(desc_edit)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            # PDF button (only show if PDF is available)
            if HELP_AVAILABLE and hasattr(self, 'pdfBookmarks') and self.pdfBookmarks:
                pdf_button = QPushButton("View PDF Documentation (4 pages)")
                pdf_button.clicked.connect(lambda: self._showCategoryPdfHelp(category))
                button_layout.addWidget(pdf_button)
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(help_dialog.accept)
            button_layout.addWidget(close_button)
            
            layout.addLayout(button_layout)
            
            help_dialog.exec_()
            
        except Exception as e:
            debugLog(f"[Help] Error showing category help for {category}: {e}")
            import traceback
            traceback.print_exc()

    def _showCategoryPdfHelp(self, category):
        """Show PDF help for a main category."""
        try:
            if not HELP_AVAILABLE or not hasattr(self, 'pdfBookmarks') or not self.pdfBookmarks:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "PDF Help", "PDF help system is not available.")
                return
            
            # Find the main category section in the PDF
            from theDocHelper.theDocFieldHelp import findCategorySectionPages
            
            # Map GUI categories to PDF section names (exact bookmark titles for main sections)
            pdf_category_map = {
                "Create (Helpers)": "Create",
                "Nodes": "Nodes",
                "Objects (Body)": "Objects (Body)",
                "Objects (SuperElement)": "Objects (SuperElement)",
                "Objects (FiniteElement)": "Objects (FiniteElement)",
                "Objects (Joint)": "Objects (Joint)",
                "Objects (Connector)": "Objects (Connector)",
                "Objects (Constraint)": "Objects (Constraint)",
                "Objects (Object)": "Objects (Object)",
                "Markers": "Markers",
                "Loads": "Loads",
                "Sensors": "Sensors",
            }
            
            
            pdf_section = pdf_category_map.get(category, category.replace(" (", "").replace(")", ""))
            debugLog(f"[Help] Looking for PDF section: '{pdf_section}' in {len(self.pdfBookmarks)} bookmarks")
            start_page, end_page = findCategorySectionPages(self.pdfPath, self.pdfBookmarks, pdf_section)
            debugLog(f"[Help] Found pages for {pdf_section}: {start_page} to {end_page}")
            
            if start_page and end_page:
                page_range = list(range(start_page, end_page + 1))  # Show complete section
                from theDocHelper.theDocFieldHelp import SectionPdfImageDialog
                dialog = SectionPdfImageDialog(self.pdfPath, page_range, title=f"PDF Help: {category}", parent=self)
                dialog.exec_()
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "PDF Help", f"Could not find PDF section for {category}.")
                debugLog(f"[Help] Available bookmark titles: {[b.get('title', '') for b in self.pdfBookmarks[:20]]}")  # Show first 20 titles
                
        except Exception as e:
            debugLog(f"[Help] Error showing PDF help for category {category}: {e}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "PDF Help Error", f"Error opening PDF help: {e}")

    def _getLegacyHelpFromDefaults(self, mbs, prefix, shortType, typeName):
        """Get help for legacy items using GetXDefaults methods, but avoid dict() documentation."""
        getDefaultsMethod = getattr(mbs, f"Get{prefix}Defaults", None)
        
        if getDefaultsMethod:
            try:
                # Get defaults and capture help
                defaults = getDefaultsMethod(shortType)
                debugLog(f"[DEBUG] Got defaults for {typeName}: {type(defaults)}")
                
                # Skip trying to get help from the defaults object itself (it's just a dict)
                # Instead, focus on building help from metadata and structure
                
                help_lines = [f"Exudyn {typeName} Parameters"]
                help_lines.append("=" * (len(f"Exudyn {typeName} Parameters")))
                help_lines.append("")
                
                # Try to get field metadata first
                metadata_found = False
                try:
                    from core.fieldMetadata import FieldMetadataBuilder
                    builder = FieldMetadataBuilder(useExtracted=True)
                    metadata = builder.build(typeName)
                    
                    if metadata and len(metadata) > 0:
                        metadata_found = True
                        help_lines.append("Parameters from metadata:")
                        
                        param_count = 0
                        for field_name, field_info in metadata.items():
                            desc = field_info.get('description', '')
                            field_type = field_info.get('type', '')
                            default_val = field_info.get('defaultValue', field_info.get('default', ''))
                            
                            help_lines.append(f"\n  • {field_name}")
                            if field_type:
                                help_lines.append(f"    Type: {field_type}")
                            if default_val not in [None, '']:
                                help_lines.append(f"    Default: {default_val}")
                            if desc:
                                clean_desc = desc.replace('\\n', ' ').replace('  ', ' ').strip()
                                help_lines.append(f"    Description: {clean_desc}")
                            
                            param_count += 1
                            if param_count >= 10:  # Limit to avoid overwhelming
                                remaining = len(metadata) - param_count
                                if remaining > 0:
                                    help_lines.append(f"\n  ... and {remaining} more parameters")
                                break
                        
                except Exception as e:
                    debugLog(f"[DEBUG] Metadata extraction failed: {e}")
                
                # If no metadata, show basic structure from defaults (but don't call help() on it)
                if not metadata_found and isinstance(defaults, dict):
                    help_lines.append("Available parameters from defaults:")
                    param_count = 0
                    for key, value in defaults.items():
                        if param_count >= 10:  # Limit parameters
                            help_lines.append(f"  ... and {len(defaults) - param_count} more parameters")
                            break
                        
                        # Show parameter name and infer type from value
                        value_type = type(value).__name__
                        if value_type == 'list' and value:
                            # For lists, show the element type
                            element_type = type(value[0]).__name__
                            value_type = f"list of {element_type}"
                        
                        help_lines.append(f"  • {key}: {value_type}")
                        if isinstance(value, (int, float, bool, str)) and len(str(value)) < 50:
                            help_lines.append(f"    Default: {value}")
                        elif isinstance(value, list) and len(value) <= 3:
                            help_lines.append(f"    Default: {value}")
                        
                        param_count += 1
                
                if len(help_lines) > 3:  # More than just header
                    help_lines.append("")
                    help_lines.append("💡 Use the PDF help button for detailed documentation with examples.")
                    result = '\n'.join(help_lines)
                    debugLog(f"[DEBUG] Enhanced defaults help for {typeName}: {len(result)} chars")
                    return result
                    
            except Exception as e:
                debugLog(f"[DEBUG] GetDefaults method failed for {typeName}: {e}")
                return None
        return None
    
    def _getLegacyHelpFromAttribute(self, mbs, typeName):
        """Try to get help by directly accessing the type as an attribute."""
        if hasattr(mbs, typeName):
            func = getattr(mbs, typeName)
            debugLog(f"[DEBUG] Found {typeName} as mbs attribute")
            
            try:
                import io
                from contextlib import redirect_stdout
                
                # Try to get help for the actual function, not just the object
                f = io.StringIO()
                with redirect_stdout(f):
                    help(func)
                help_text = f.getvalue()
                
                if help_text and len(help_text) > 100:
                    # Filter out generic Python help and focus on Exudyn content
                    lines = help_text.split('\n')
                    exudyn_lines = []
                    in_exudyn_section = False
                    
                    for line in lines:
                        # Look for Exudyn-specific content
                        if any(keyword in line.lower() for keyword in ['exudyn', 'function:', 'input:', 'output:', 'parameter']):
                            in_exudyn_section = True
                        
                        # Skip generic Python dict documentation
                        if 'dict()' in line or 'new empty dictionary' in line:
                            continue
                            
                        if in_exudyn_section or any(keyword in line for keyword in ['#**', 'description', 'parameter']):
                            exudyn_lines.append(line)
                    
                    # If we found Exudyn-specific content, use it
                    if exudyn_lines and len('\n'.join(exudyn_lines)) > 50:
                        filtered_help = '\n'.join(exudyn_lines).strip()
                        debugLog(f"[DEBUG] Got filtered help text for {typeName}: {len(filtered_help)} chars")
                        return f"Exudyn {typeName} Documentation:\n\n{filtered_help}"
                      # Otherwise, try to extract meaningful parts from the full help
                    if len(help_text) > 100:
                        debugLog(f"[DEBUG] Got help text for {typeName}: {len(help_text)} chars (using full text)")
                        # Remove the generic "Help on method" header
                        clean_lines = []
                        skip_generic = True
                        for line in lines:
                            if skip_generic and ('Help on' in line or 'method' in line or 'built-in' in line):
                                continue
                            skip_generic = False
                            clean_lines.append(line)
                        
                        if clean_lines:
                            return f"Exudyn {typeName} Documentation:\n\n" + '\n'.join(clean_lines).strip()
            except Exception as e:
                debugLog(f"[DEBUG] Help extraction failed for {typeName}: {e}")
        return None
    
    def _getLegacyHelpFromMetadata(self, typeName):
        """Get help from field metadata, enhanced with PDF description when available."""
        try:
            from core.fieldMetadata import FieldMetadataBuilder
            builder = FieldMetadataBuilder(useExtracted=True)
            metadata = builder.build(typeName)
            
            if metadata and len(metadata) > 0:
                help_lines = [f"Exudyn {typeName} Parameters"]
                help_lines.append("=" * 50)
                help_lines.append("")
                
                # Try to get description from PDF first (more detailed)
                pdf_description = self._getLegacyHelpFromPdfContent(typeName)
                
                if pdf_description:
                    help_lines.append(f"Description: {pdf_description}")
                    help_lines.append("")
                else:
                    # Fallback to simple descriptions
                    type_descriptions = {
                        "ObjectConnector": "A connector object that links bodies or nodes with specific constraints",
                        "ObjectContact": "A contact object for collision detection and response",
                        "ObjectMass": "A mass object representing inertial properties",
                        "NodePoint": "A point node with position coordinates",
                        "NodeRigidBody": "A rigid body node with position and orientation",
                        "MarkerNode": "A marker attached to a node for measurements or connections",
                        "MarkerBody": "A marker attached to a body for measurements or connections",
                        "LoadForce": "A force load applied to nodes or bodies",
                        "LoadTorque": "A torque load applied to nodes or bodies",
                        "SensorNode": "A sensor for monitoring node quantities",
                        "SensorBody": "A sensor for monitoring body quantities",
                    }
                    
                    # Find matching description
                    description = None
                    for key, desc in type_descriptions.items():
                        if typeName.startswith(key):
                            description = desc
                            break
                    
                    if description:
                        help_lines.append(f"Description: {description}")
                        help_lines.append("")
                
                help_lines.append("Parameters:")
                
                param_count = 0
                for field_name, field_info in metadata.items():
                    desc = field_info.get('description', '')
                    field_type = field_info.get('type', '')
                    default_val = field_info.get('defaultValue', field_info.get('default', ''))
                    
                    help_lines.append(f"\n  {field_name}:")
                    if field_type:
                        help_lines.append(f"    Type: {field_type}")
                    if default_val not in [None, '']:
                        help_lines.append(f"    Default: {default_val}")
                    if desc:
                        # Clean up description
                        clean_desc = desc.replace('\\n', ' ').strip()
                        if len(clean_desc) > 80:
                            # Break long descriptions
                            words = clean_desc.split()
                            lines = []
                            current_line = "    "
                            for word in words:
                                if len(current_line + word) > 75:
                                    lines.append(current_line.rstrip())
                                    current_line = "    " + word + " "
                                else:
                                    current_line += word + " "
                            if current_line.strip():
                                lines.append(current_line.rstrip())
                            help_lines.extend(lines)
                        else:
                            help_lines.append(f"    Description: {clean_desc}")
                    
                    param_count += 1
                    if param_count >= 15:  # Limit number of parameters to avoid overwhelming output
                        help_lines.append(f"\n  ... and {len(metadata) - param_count} more parameters")
                        break
                
                if len(help_lines) > 5:  # More than just header
                    help_lines.append("")
                    help_lines.append("💡 Tip: Use the PDF help button for detailed documentation with examples.")
                    result = '\n'.join(help_lines)
                    debugLog(f"[DEBUG] Got enhanced metadata help for {typeName}: {len(result)} chars, {param_count} parameters")
                    return result
                    
        except Exception as e:
            debugLog(f"[DEBUG] Enhanced metadata help failed for {typeName}: {e}")
        return None

    def _getLegacyHelpFromPdfContent(self, typeName):
        """Extract help content directly from PDF for legacy items, preferring specific type descriptions over category descriptions."""
        try:
            # Only proceed if we have PDF access
            if not (hasattr(self, 'pdfPath') and hasattr(self, 'pdfBookmarks') and 
                    self.pdfPath and self.pdfBookmarks):
                return None
            
            from theDocHelper.theDocFieldHelp import getLegacyItemPageRange
            import fitz
            import re
            
            debugLog(f"[DEBUG] Trying to find specific PDF content for {typeName}")
            
            # First, try to find the specific type in the PDF
            start_page, end_page = getLegacyItemPageRange(self.pdfPath, self.pdfBookmarks, typeName)
            
            if start_page and end_page and start_page <= end_page:
                debugLog(f"[DEBUG] Found specific pages for {typeName}: {start_page} to {end_page}")
                
                # Extract content from the PDF pages for this specific type
                try:
                    doc = fitz.open(str(self.pdfPath))
                    content_lines = []
                    
                    for page_num in range(start_page - 1, min(end_page, len(doc))):  # Convert to 0-based indexing
                        page = doc.load_page(page_num)
                        text = page.get_text()
                        
                        # Look for the type description (usually after the type name)
                        lines = text.split('\n')
                        found_type = False
                        description_lines = []
                        
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                                
                            # Look for the type name or similar pattern
                            if typeName in line or (typeName.replace('Object', '') in line and len(line) < 50):
                                found_type = True
                                continue
                                
                            # If we found the type, collect description text
                            if found_type:
                                # Skip headers, page numbers, and collect meaningful description text
                                if (not re.match(r'^[A-Z\s]+$', line) and 
                                    not re.match(r'^\d+$', line) and 
                                    len(line) > 10 and 
                                    not line.startswith('Figure ') and
                                    not line.startswith('Table ')):
                                    description_lines.append(line)
                                    # Stop after collecting a reasonable amount of description
                                    if len(' '.join(description_lines)) > 300:
                                        break
                        
                        if description_lines:
                            content_lines.extend(description_lines)
                            break  # Found content, no need to check more pages
                    
                    doc.close()
                    
                    if content_lines:
                        result = ' '.join(content_lines)
                        # Clean up the text
                        result = re.sub(r'\s+', ' ', result)
                        result = result.strip()
                        debugLog(f"[DEBUG] Extracted specific PDF content for {typeName}: {len(result)} chars")
                        return result
                    
                except Exception as e:
                    debugLog(f"[DEBUG] Failed to extract specific content from PDF pages {start_page}-{end_page}: {e}")
            
            # If no specific content found, fall back to category description
            debugLog(f"[DEBUG] No specific content found for {typeName}, trying category description")
            
            from model.objectRegistry import getCategorizedRegistry
            
            # Get the category for this type
            categorized_registry = getCategorizedRegistry()
            item_category = None
            for category, types in categorized_registry.items():
                if typeName in types:
                    item_category = category
                    break
            
            # If we found the category and have a full description for it, use it as fallback
            if item_category and item_category in FULL_CATEGORY_DESCRIPTIONS:
                category_desc = FULL_CATEGORY_DESCRIPTIONS[item_category]
                debugLog(f"[DEBUG] Using category description for {typeName} from {item_category} as fallback")
                return category_desc
            
            return None
            
        except Exception as e:
            debugLog(f"[DEBUG] PDF content extraction failed for {typeName}: {e}")
            return None


# Alias for backward compatibility
AddItemDialog = AddModelElementDialog
