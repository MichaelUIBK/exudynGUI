# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: model/pdfHelpExtractor.py
#
# Description:
# This module provides utilities to extract and visualize documentation snippets
# from a structured PDF (e.g., 'theDoc.pdf') using bookmarks (Lesezeichen).
#
# Features:
# - Parse and flatten nested PDF bookmarks (via PyPDF2)
# - Locate documentation sections for legacy items (Object*, Node*, etc.)
# - Locate documentation for Create* functions inside "MainSystem extensions"
# - Determine page ranges for help display (2–3 pages per section)
# - Perform content-based fallback search if bookmarks are insufficient
# - Show pages interactively via Qt-based dialog with zoom/navigation
#
# Usage:
#   This file can be used both as a script and as a module.
#   Example command-line usage:
#
#       python pdfHelpExtractor.py /path/to/theDoc.pdf ObjectMassPoint
#
#   This would search for the ObjectMassPoint section and print the page number(s).
#
# GUI Integration:
#   - The class `SectionPdfImageDialog` provides a PyQt5 dialog that displays
#     selected documentation pages (with navigation and zoom support).
#
# Dependencies:
#   - PyMuPDF (fitz)       → for reading and rendering PDF pages
#   - PyPDF2               → for extracting bookmark structure
#   - PyQt5                → for displaying interactive help pages
#
# Authors:   Michael Pieber
# Date:      2025-05-12
# License:   BSD-3 license
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


import sys, os, re

from PyQt5.QtCore import Qt
from PyQt5.QtGui  import QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QScrollArea, QSizePolicy, QWidget
)

import fitz           # PyMuPDF for rendering pages
import PyPDF2         # PyPDF2 for reading bookmarks/outlines

from pathlib import Path
thisFile = Path(__file__).resolve()
projectRoot = thisFile.parents[2]  # mainExudynGUI_V0.03
pdfPath = projectRoot / 'exudynGUI' / 'theDocHelper' / 'theDoc.pdf'


def loadBookmarks(pdfPath):
    """
    Returns a flat list of bookmark dicts: { "title": ..., "page": ..., "level": ... }.
    If no bookmarks found, returns [].
    """
    reader = PyPDF2.PdfReader(pdfPath)
    rawOutlines = []

    # Try reader.outline (PyPDF2 ≥3.0), which may be a list or a method:
    if hasattr(reader, "outline"):
        outlineAttr = reader.outline
        if isinstance(outlineAttr, list):
            rawOutlines = outlineAttr
        elif callable(outlineAttr):
            try:
                rawOutlines = outlineAttr()
            except Exception:
                rawOutlines = []

    # Fallback to get_outlines() (PyPDF2 <3.0):
    if not rawOutlines and hasattr(reader, "get_outlines"):
        try:
            rawOutlines = reader.get_outlines()
        except Exception:
            rawOutlines = []

    def flatten(outlines, level=0, collected=None):
        """
        Recursively flatten a nested list of PyPDF2 bookmark (Destination) objects
        into a flat list of dicts: { "title": ..., "page": ..., "level": ... }.
        Handles item.children as either list or method.
        """
        if collected is None:
            collected = []
        for item in outlines:
            if isinstance(item, list):
                flatten(item, level + 1, collected)
            else:
                title = item.title
                try:
                    pg = reader.get_destination_page_number(item)
                except Exception:
                    pg = None
                collected.append({
                    "title": title,
                    "page": pg + 1 if pg is not None else None,
                    "level": level
                })
                if hasattr(item, "children"):
                    childrenAttr = item.children
                    if isinstance(childrenAttr, list):
                        flatten(childrenAttr, level + 1, collected)
                    elif callable(childrenAttr):
                        try:
                            childList = childrenAttr()
                        except Exception:
                            childList = []
                        if isinstance(childList, list):
                            flatten(childList, level + 1, collected)
        return collected

    if rawOutlines:
        return flatten(rawOutlines)
    else:
        return []


def findBookmarkPage(bookmarkList, fieldName):
    """
    Among the list of bookmark dicts returned by loadBookmarks(),
    find the first whose "title" contains fieldName as a whole word.
    Returns (pageNumber, bookmarkTitle) or (None, None) if not found.
    """
    pattern = re.compile(r"\b" + re.escape(fieldName) + r"\b", flags=re.IGNORECASE)
    for bm in bookmarkList:
        if bm["title"] and pattern.search(bm["title"]):
            return bm["page"], bm["title"]
    return None, None



def findBookmarkSectionPages(bookmarkList, searchKey):
    """
    Locate the section whose top-level bookmark title matches searchKey, and
    return (startPage, endPageInclusive). If searchKey is not found, return (None, None).

    Handles nested bookmarks and ensures accurate detection of sections like "Objects" and "Markers".
    """
    pattern = re.compile(r"\b" + re.escape(searchKey) + r"\b", flags=re.IGNORECASE)
    startPage, endPage = None, None

    for i, bm in enumerate(bookmarkList):
        if bm["title"] and pattern.search(bm["title"]):
            startPage = bm["page"]
            # Find the end page by checking the next bookmark at the same or higher level
            for j in range(i + 1, len(bookmarkList)):
                if bookmarkList[j]["level"] <= bm["level"]:
                    endPage = bookmarkList[j]["page"] - 1
                    break
            if endPage is None:
                endPage = bm["page"]  # Last page of the section
            break

    return startPage, endPage

def findFunctionPageInCreateSection(pdfPath, bookmarkList, functionName):
    """
    Locate the page for a given function or legacy object type in the PDF.

    For Create functions, it searches for "def <functionName>".
    For legacy object types (Object*, Node*, Marker*, Load*, Sensor*), it searches for
    "<objectType>" in the relevant section.

    - functionName should be passed exactly (e.g., "CreateCartesianSpringDamper" or "ObjectGround").
    - All page numbers here are 1‐based (fitz uses 0‐based indices internally).
    """
    # Determine the section to search based on the functionName prefix
    if functionName.startswith("Create"):
        startP, endP = findCreateSectionPages(bookmarkList)
        if startP is None:
            return None
    elif functionName.startswith(("Object", "Node", "Marker", "Load", "Sensor")):
        # Determine which section to search based on the prefix
        sections = findLegacySectionPages(bookmarkList)
        
        prefix = ""
        if functionName.startswith("Object"):
            prefix = "objects"
        elif functionName.startswith("Node"):
            prefix = "nodes"
        elif functionName.startswith("Marker"):
            prefix = "markers"
        elif functionName.startswith("Load"):
            prefix = "loads"
        elif functionName.startswith("Sensor"):
            prefix = "sensors"
            
        if prefix in sections and sections[prefix] is not None:
            startP, endP = sections[prefix]
        else:
            return None  # Section not found
    else:
        return None  # Unsupported type

    if startP is None:
        return None

    # If endP is None, that means "to end of document"
    doc = fitz.open(pdfPath)
    if endP is None:
        endP = doc.page_count    # Build a regex pattern based on the type
    if functionName.startswith("Create"):
        pattern = re.compile(r"\bdef\s+" + re.escape(functionName) + r"\b")
    else:
        # For legacy items, we need to handle two cases:
        # 1. The full name (e.g., "ObjectMassPoint")
        # 2. Just the type part (e.g., "MassPoint" for "ObjectMassPoint")
        
        # Extract the type part after the prefix
        import re as regex
        match = regex.match(r"^(Object|Node|Marker|Load|Sensor)(.+)", functionName)
        if match:
            prefix, shortType = match.groups()
            # Look for either the full name or just the short type
            pattern = re.compile(r"\b(" + re.escape(functionName) + r"|" + re.escape(shortType) + r")\b")

    # Scan each page in the section
    for pageNum in range(startP, endP + 1):
        page = doc.load_page(pageNum - 1)
        text = page.get_text("text")
        if pattern.search(text):
            # Found it! Return the 1-based page number
            doc.close()
            return pageNum

    doc.close()
    return None

def findCreateSectionPages(bookmarkList):
    """
    Return (startPage, endPageInclusive) for the entire
    'MainSystem extensions (create)' block.  If not found, return (None, None).

    This version simply does a case‐insensitive substring check for
    'mainsystem extensions (create)' in each bookmark title.
    """
    search_lower = "mainsystem extensions (create)"

    idx    = None
    lvl0   = None
    startP = None

    # 1) Scan through bookmarks until we find one whose lowercase title contains our search string
    for i, bm in enumerate(bookmarkList):
        title = bm.get("title") or ""
        if search_lower in title.lower():
            idx    = i
            lvl0   = bm.get("level", 0)
            startP = bm.get("page")       # page is already 1‐based
            break

    if idx is None:
        return None, None

    # 2) Find the next bookmark at the same or higher level → that marks the end‐of‐section
    endIndex = len(bookmarkList)
    for j in range(idx + 1, len(bookmarkList)):
        if bookmarkList[j].get("level", 0) <= lvl0:
            endIndex = j
            break

    if endIndex < len(bookmarkList):
        nextPage = bookmarkList[endIndex].get("page")
        endP     = (nextPage - 1) if nextPage is not None else None
    else:
        endP = None

    return startP, endP

def findLegacySectionPages(bookmarkList):
    """
    Locate the start and end pages for legacy sections in the PDF based on bookmark structure.
    This function searches for sections that contain legacy items (Objects, Nodes, Markers, etc.)
    using more flexible pattern matching to adapt to the actual PDF structure.

    Returns a dictionary of section_type: (startPage, endPage) pairs.
    """
    # Define section keywords to search for in bookmarks (more flexible patterns)
    sections = {
        "objects": ["object", "objects"],
        "nodes": ["node", "nodes"],
        "markers": ["marker", "markers"],
        "loads": ["load", "loads"],
        "sensors": ["sensor", "sensors"]
    }
    
    # Dictionary to store results for each section
    results = {}
    
    # Find all relevant section bookmarks
    relevant_bookmarks = []
    for i, bookmark in enumerate(bookmarkList):
        if "title" not in bookmark or bookmark["title"] is None:
            continue
            
        title = bookmark["title"].lower()
        page = bookmark.get("page", None)
        level = bookmark.get("level", 0)
        
        # Check if this bookmark relates to any of our sections
        for section_type, keywords in sections.items():
            if any(keyword in title for keyword in keywords):
                relevant_bookmarks.append({
                    "index": i,
                    "section_type": section_type,
                    "title": bookmark["title"],
                    "page": page,
                    "level": level
                })
                break  # Only match one section type per bookmark
    
    # Process relevant bookmarks to find section boundaries
    for i, bm in enumerate(relevant_bookmarks):
        section_type = bm["section_type"]
        
        # If we've already found this section, skip (we want the first occurrence)
        if section_type in results:
            continue
        
        startPage = bm["page"]
        level = bm["level"]
        
        # Find end page by looking at the next bookmark at same or higher level
        endPage = None
        
        # Try to find next bookmark at same or higher level in relevant bookmarks first
        for next_bm in relevant_bookmarks[i+1:]:
            if next_bm["level"] <= level:
                endPage = next_bm["page"] - 1
                break
                
        # If not found, search in all bookmarks
        if endPage is None:
            for j in range(bm["index"] + 1, len(bookmarkList)):
                if bookmarkList[j].get("level", 0) <= level:
                    endPage = bookmarkList[j].get("page", None) - 1
                    break
        
        # Store result for this section
        results[section_type] = (startPage, endPage)
    
    return results

def findLegacyItemInPdf(pdfPath, bookmarkList, functionName):
    """
    Enhanced function to find legacy items (Object*, Node*, Marker*, etc.) in PDF.
    Uses multiple search strategies to improve the chances of finding the item.
    
    Args:
        pdfPath: Path to the PDF file
        bookmarkList: List of bookmarks from loadBookmarks()
        functionName: The name of the legacy item (e.g., "NodePoint", "ObjectMassPoint")
        
    Returns:
        Page number (1-based) if found, None if not found
    """
    # STRATEGY 1: Direct bookmark match (most reliable)
    for bm in bookmarkList:
        if bm.get("title") and functionName in bm.get("title"):
            return bm.get("page")

    # STRATEGY 2: For legacy items, extract prefix and short name
    shortName = None
    prefix = None
    
    if functionName.startswith(("Object", "Node", "Marker", "Load", "Sensor")):
        match = re.match(r"^(Object|Node|Marker|Load|Sensor)(.+)", functionName)
        if match:
            prefix = match.group(1)
            shortName = match.group(2)
    else:
        return None  # Not a legacy item
        
    # STRATEGY 3: Look for short name in section-specific bookmarks
    if shortName and prefix:
        keyword = prefix.lower()
        for bm in bookmarkList:
            if bm.get("title") and shortName in bm.get("title") and keyword in bm.get("title", "").lower():
                return bm.get("page")
    
    # STRATEGY 4: More aggressive search - just look for the short name in any bookmark
    if shortName:
        for bm in bookmarkList:
            if bm.get("title") and shortName in bm.get("title"):
                return bm.get("page")
    
    # STRATEGY 5: Content-based search in the appropriate section
    if prefix:
        # Map prefix to section name
        section_map = {
            "Object": "objects", 
            "Node": "nodes", 
            "Marker": "markers",
            "Load": "loads", 
            "Sensor": "sensors"
        }
        section_name = section_map.get(prefix, "").lower()
        
        # Find section boundaries using findLegacySectionPages
        sections = findLegacySectionPages(bookmarkList)
        start_page = None
        end_page = None
        
        if section_name in sections and sections[section_name] is not None:
            start_page, end_page = sections[section_name]
        else:
            # Fallback: manually search for the section
            for i, bm in enumerate(bookmarkList):
                title = bm.get("title", "").lower()
                if section_name in title:
                    start_page = bm.get("page")
                    level = bm.get("level", 0)
                    
                    # Find the next bookmark at same or higher level
                    for j in range(i + 1, len(bookmarkList)):
                        if bookmarkList[j].get("level", 0) <= level:
                            end_page = bookmarkList[j].get("page") - 1
                            break
                    break
        
        # If we found the section, search for the item in page content
        if start_page:
            doc = fitz.open(pdfPath)
            end_page = end_page or doc.page_count
            
            # Search for either full name or short name
            pattern = re.compile(r"\b(" + re.escape(functionName) + r"|" + re.escape(shortName) + r")\b")
            
            for page_num in range(start_page, end_page + 1):
                try:
                    page = doc.load_page(page_num - 1)  # 0-based
                    text = page.get_text("text")
                    if pattern.search(text):
                        doc.close()
                        return page_num
                except Exception:
                    pass  # Skip problematic pages
            
            doc.close()  # Ensure we close the document

    # STRATEGY 6: Last resort - search the entire PDF
    try:
        doc = fitz.open(pdfPath)
        # Search for either full name or short name
        search_terms = [functionName]
        if shortName:
            search_terms.append(shortName)
            
        for term in search_terms:
            pattern = re.compile(r"\b" + re.escape(term) + r"\b")
            for page_num in range(doc.page_count):
                try:
                    page = doc.load_page(page_num)
                    text = page.get_text("text")
                    if pattern.search(text):
                        doc.close()
                        return page_num + 1  # Convert to 1-based
                except Exception:
                    pass  # Skip problematic pages
        
        doc.close()
    except Exception:
        pass
        
    # If all strategies fail, return None
    return None

def getCreateItemPageRange(pdfPath, bookmarkList, functionName):
    """
    Get the page range for a CREATE function (typically +2 pages from the start).
    Returns (startPage, endPage) or (None, None) if not found.
    """
    page = findFunctionPageInCreateSection(pdfPath, bookmarkList, functionName)
    if page:
        return page, page + 1  # Show 2 pages for CREATE items
    return None, None

def getLegacyItemPageRange(pdfPath, bookmarkList, functionName):
    """
    Get the page range for a legacy item (from its start until the next item of same level).
    Returns (startPage, endPage) or (None, None) if not found.
    """
    # First find the item in bookmarks
    target_bookmark = None
    target_index = None
    
    for i, bm in enumerate(bookmarkList):
        if bm.get("title") and functionName in bm.get("title"):
            target_bookmark = bm
            target_index = i
            break
    
    if not target_bookmark:
        # Try using our enhanced search to find the page
        start_page = findLegacyItemInPdf(pdfPath, bookmarkList, functionName)
        if start_page:
            # If we found it via content search, show 2 pages
            return start_page, start_page + 1
        return None, None
    
    start_page = target_bookmark.get("page")
    if not start_page:
        return None, None
    
    # Find the next bookmark at the same or higher level to determine end page
    target_level = target_bookmark.get("level", 0)
    end_page = start_page + 1  # Default to 2 pages
    
    for j in range(target_index + 1, len(bookmarkList)):
        next_bm = bookmarkList[j]
        next_level = next_bm.get("level", 0)
        next_page = next_bm.get("page")
        
        # Stop at the next item of same or higher level
        if next_level <= target_level and next_page:
            end_page = next_page - 1
            break
    
    # Ensure we show at least 2 pages
    if end_page <= start_page:
        end_page = start_page + 1
    
    return start_page, end_page

class SectionPdfImageDialog(QDialog):
    """
    Display PDF pages with navigation controls.
    Shows one page at a time with Previous/Next buttons.
    """
    
    def __init__(self, pdfPath, pageNums, title=None, parent=None):
        super().__init__(parent)
        self.pdfPath = pdfPath
        
        # Ensure pageNums is a flat list of integers
        if isinstance(pageNums, int):
            self.pageNums = [pageNums]
        elif isinstance(pageNums, (list, tuple)):
            # Flatten any nested lists and ensure all elements are integers
            flat_pages = []
            for item in pageNums:
                if isinstance(item, (list, tuple)):
                    # If item is nested, flatten it
                    for subitem in item:
                        try:
                            flat_pages.append(int(subitem))
                        except (ValueError, TypeError):
                            pass  # Skip invalid page numbers
                else:
                    try:
                        flat_pages.append(int(item))
                    except (ValueError, TypeError):
                        pass  # Skip invalid page numbers
            self.pageNums = flat_pages
        else:
            # Try to convert single value to integer
            try:
                self.pageNums = [int(pageNums)]
            except (ValueError, TypeError):
                self.pageNums = []
        
        # Remove duplicates and sort
        self.pageNums = sorted(list(set(self.pageNums)))
        
        self.currentPageIndex = 0
        self.doc = None
        
        # Set up basic dialog properties
        self.setWindowTitle(title or "PDF Documentation")
        self.resize(900, 800)  # Larger size for better readability
        
        # Initialize UI
        self._setupUI()
        
        # Load PDF document
        try:
            self.doc = fitz.open(pdfPath)
            # Validate page numbers against document
            valid_pages = []
            for page_num in self.pageNums:
                if 1 <= page_num <= self.doc.page_count:
                    valid_pages.append(page_num)
            self.pageNums = valid_pages
            
            if self.pageNums:
                self._showCurrentPage()
            else:
                self._showError("No valid pages to display")
        except Exception as e:
            self._showError(f"Error loading PDF: {e}")

    def _setupUI(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header with navigation info
        self.headerLabel = QLabel()
        self.headerLabel.setStyleSheet("""
            font-weight: bold; 
            padding: 10px; 
            background-color: #e8f4fd; 
            border: 1px solid #b3d9ff;
            color: #1a472a;
        """)
        layout.addWidget(self.headerLabel)
        
        # Main content area with scroll
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setAlignment(Qt.AlignCenter)
        self.scrollArea.setStyleSheet("QScrollArea { border: 1px solid #ddd; }")
        layout.addWidget(self.scrollArea)
        
        # Page display area
        self.pageWidget = QWidget()
        self.pageLayout = QVBoxLayout(self.pageWidget)
        self.scrollArea.setWidget(self.pageWidget)
        
        # Page content label
        self.pageLabel = QLabel()
        self.pageLabel.setAlignment(Qt.AlignCenter)
        self.pageLabel.setStyleSheet("background-color: white; border: none;")
        self.pageLayout.addWidget(self.pageLabel)
        
        # Navigation and control buttons
        buttonLayout = QHBoxLayout()
        
        # Previous button
        self.prevButton = QPushButton("◀ Previous")
        self.prevButton.setEnabled(False)
        self.prevButton.clicked.connect(self._previousPage)
        self.prevButton.setFixedWidth(100)
        buttonLayout.addWidget(self.prevButton)
        
        # Page indicator
        self.pageIndicator = QLabel()
        self.pageIndicator.setAlignment(Qt.AlignCenter)
        self.pageIndicator.setStyleSheet("font-weight: bold; padding: 5px;")
        buttonLayout.addWidget(self.pageIndicator)
        
        # Next button
        self.nextButton = QPushButton("Next ▶")
        self.nextButton.setEnabled(False)
        self.nextButton.clicked.connect(self._nextPage)
        self.nextButton.setFixedWidth(100)
        buttonLayout.addWidget(self.nextButton)
        
        buttonLayout.addStretch()
        
        # Zoom controls
        zoomLayout = QHBoxLayout()
        
        self.zoomOutButton = QPushButton("Zoom -")
        self.zoomOutButton.clicked.connect(self._zoomOut)
        self.zoomOutButton.setFixedWidth(80)
        zoomLayout.addWidget(self.zoomOutButton)
        
        self.zoomLabel = QLabel("100%")
        self.zoomLabel.setAlignment(Qt.AlignCenter)
        self.zoomLabel.setFixedWidth(50)
        zoomLayout.addWidget(self.zoomLabel)
        
        self.zoomInButton = QPushButton("Zoom +")
        self.zoomInButton.clicked.connect(self._zoomIn)
        self.zoomInButton.setFixedWidth(80)
        zoomLayout.addWidget(self.zoomInButton)
        
        buttonLayout.addLayout(zoomLayout)
        
        # Close button
        closeButton = QPushButton("Close")
        closeButton.clicked.connect(self.accept)
        closeButton.setFixedWidth(100)
        buttonLayout.addWidget(closeButton)
        
        layout.addLayout(buttonLayout)
          # Store zoom level
        self.zoomLevel = 1.0  # Default zoom for readability

    def _updateHeader(self):
        """Update the header information"""
        if self.pageNums:
            current_page = self.pageNums[self.currentPageIndex]
            total_pages = len(self.pageNums)
            filename = os.path.basename(self.pdfPath)
            self.headerLabel.setText(f"📖 PDF Documentation: {filename} - Page {current_page}")
            self.pageIndicator.setText(f"Page {self.currentPageIndex + 1} of {total_pages}")
        else:
            self.headerLabel.setText(f"📖 PDF Documentation: {os.path.basename(self.pdfPath)}")
            self.pageIndicator.setText("No pages")

    def _updateButtons(self):
        """Update navigation button states"""
        if len(self.pageNums) > 1:
            self.prevButton.setEnabled(self.currentPageIndex > 0)
            self.nextButton.setEnabled(self.currentPageIndex < len(self.pageNums) - 1)
        else:
            self.prevButton.setEnabled(False)
            self.nextButton.setEnabled(False)
    
    def _showCurrentPage(self):
        """Display the current page"""
        if not self.pageNums or not self.doc:
            self._showError("No pages to display")
            return
            
        try:
            current_page_num = self.pageNums[self.currentPageIndex]
            
            # Ensure current_page_num is an integer
            if isinstance(current_page_num, (list, tuple)):
                self._showError(f"Invalid page number format: {current_page_num} (expected integer)")
                return
            
            # Convert to integer if it's a string or other numeric type
            try:
                current_page_num = int(current_page_num)
            except (ValueError, TypeError):
                self._showError(f"Cannot convert page number to integer: {current_page_num}")
                return
            
            # Validate page number
            if current_page_num < 1 or current_page_num > self.doc.page_count:
                self._showError(f"Invalid page number: {current_page_num} (valid range: 1-{self.doc.page_count})")
                return
            
            # Load and render the page
            page = self.doc.load_page(current_page_num - 1)  # Convert to 0-based
            matrix = fitz.Matrix(self.zoomLevel, self.zoomLevel)
            pixmap = page.get_pixmap(matrix=matrix)
            
            # Convert to Qt format
            img = QImage(pixmap.samples, pixmap.width, pixmap.height, 
                        pixmap.stride, QImage.Format_RGB888)
            qpixmap = QPixmap.fromImage(img)
            
            # Display the page
            self.pageLabel.setPixmap(qpixmap)
            
            # Update UI elements
            self._updateHeader()
            self._updateButtons()
            self.zoomLabel.setText(f"{int(self.zoomLevel * 100)}%")
            
        except Exception as e:
            self._showError(f"Error displaying page: {e}")

    def _showError(self, message):
        """Display an error message"""
        self.pageLabel.setText(f"❌ {message}")
        self.headerLabel.setText("Error")
        self.pageIndicator.setText("")

    def _previousPage(self):
        """Go to previous page"""
        if self.currentPageIndex > 0:
            self.currentPageIndex -= 1
            self._showCurrentPage()

    def _nextPage(self):
        """Go to next page"""
        if self.currentPageIndex < len(self.pageNums) - 1:
            self.currentPageIndex += 1
            self._showCurrentPage()

    def _zoomIn(self):
        """Increase zoom level"""
        if self.zoomLevel < 3.0:  # Max zoom
            self.zoomLevel += 0.25
            self._showCurrentPage()

    def _zoomOut(self):
        """Decrease zoom level"""
        if self.zoomLevel > 0.5:  # Min zoom
            self.zoomLevel -= 0.25
            self._showCurrentPage()

    def closeEvent(self, event):
        """Clean up when dialog closes"""
        if self.doc:
            self.doc.close()
        event.accept()

    def keyPressEvent(self, event):
        """Handle keyboard navigation"""
        from PyQt5.QtCore import Qt
        if event.key() == Qt.Key_Left or event.key() == Qt.Key_Up:
            self._previousPage()
        elif event.key() == Qt.Key_Right or event.key() == Qt.Key_Down:
            self._nextPage()
        elif event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self._zoomIn()
        elif event.key() == Qt.Key_Minus:
            self._zoomOut()
        else:
            super().keyPressEvent(event)


def findCategorySectionPages(pdfPath, bookmarks, categoryName):
    """
    Find the page range for a main category section (like "Nodes", "Objects", "Markers", etc.).
    
    Args:
        pdfPath: Path to the PDF file
        bookmarks: List of bookmarks from loadBookmarks()
        categoryName: Name of the category (e.g., "Nodes", "Markers", "Objects (Body)")
        
    Returns:
        Tuple (start_page, end_page) if found, (None, None) if not found
    """
    try:
        from core.debug import debugInfo
        
        # Clean category name for matching
        clean_name = categoryName.replace(" (", "").replace(")", "").strip()
        debugInfo(f"[Help] Searching for category '{categoryName}' (clean: '{clean_name}') in {len(bookmarks)} bookmarks", origin="Help")
        
        # Try different matching strategies
        strategies = [
            # Exact match
            lambda title: title.strip().lower() == clean_name.lower(),
            # Contains match
            lambda title: clean_name.lower() in title.strip().lower(),
            # Chapter number match (8.1 Nodes, 8.2 Objects, etc.)
            lambda title: any(chapter in title for chapter in ["8.1", "8.2", "8.3", "8.4", "8.5"]) and clean_name.lower() in title.lower()
        ]
        
        for strategy_idx, strategy in enumerate(strategies):
            debugInfo(f"[Help] Trying strategy {strategy_idx + 1} for '{categoryName}'", origin="Help")
            for i, bookmark in enumerate(bookmarks):
                title = bookmark.get('title', '')
                if strategy(title):
                    start_page = bookmark['page']
                    debugInfo(f"[Help] Found match for '{categoryName}': '{title}' at page {start_page}", origin="Help")
                    
                    # Find end page by looking for next bookmark at same or higher level
                    end_page = None
                    for j in range(i + 1, len(bookmarks)):
                        next_bookmark = bookmarks[j]
                        if next_bookmark.get('level', 0) <= bookmark.get('level', 0):
                            end_page = next_bookmark['page'] - 1
                            break
                    
                    if end_page is None:
                        end_page = start_page + 20  # Reasonable default for categories
                    
                    # Ensure end_page is at least start_page (avoid invalid ranges)
                    if end_page < start_page:
                        end_page = start_page + 2  # Show at least 3 pages for categories
                    
                    debugInfo(f"[Help] Page range for '{categoryName}': {start_page} to {end_page}", origin="Help")
                    return start_page, end_page
        
        # If not found, show some sample bookmarks for debugging
        sample_titles = [b.get('title', '') for b in bookmarks[:10]]
        debugInfo(f"[Help] Could not find '{categoryName}'. Sample bookmark titles: {sample_titles}", origin="Help")
        return None, None
        
    except Exception as e:
        from core.debug import debugError
        debugError(f"Error finding category section pages for {categoryName}: {e}", origin="Help")
        return None, None


def getLegacyItemPageRange(pdfPath, bookmarks, itemName):
    """
    Get the page range for a legacy item (ObjectXXX, NodeXXX, etc.) in the PDF.
    
    Args:
        pdfPath: Path to the PDF file
        bookmarks: List of bookmarks from loadBookmarks()
        itemName: Name of the legacy item (e.g., "NodePoint", "ObjectMassPoint")
        
    Returns:
        Tuple (start_page, end_page) if found, (None, None) if not found
    """
    try:
        # Try direct bookmark match first
        page = findLegacyItemInPdf(pdfPath, bookmarks, itemName)
        
        if page:
            # Find the next bookmark to determine end page
            for i, bookmark in enumerate(bookmarks):
                if bookmark.get('page') == page:
                    end_page = page
                    # Look for next bookmark
                    for j in range(i + 1, len(bookmarks)):
                        next_bookmark = bookmarks[j]
                        if next_bookmark.get('level', 0) <= bookmark.get('level', 0):
                            end_page = next_bookmark['page'] - 1
                            break
                    
                    # Ensure end_page is at least page (avoid invalid ranges)
                    if end_page < page:
                        end_page = page + 1  # Show at least 2 pages for legacy items
                        
                    return page, end_page
            
            # If no next bookmark found, assume single page
            return page, page
        
        return None, None
        
    except Exception as e:
        from core.debug import debugError
        debugError(f"Error finding legacy item page range for {itemName}: {e}", origin="Help")
        return None, None


def getCreateItemPageRange(pdfPath, bookmarks, itemName):
    """
    Get the page range for a Create function in the PDF.
    
    Args:
        pdfPath: Path to the PDF file
        bookmarks: List of bookmarks from loadBookmarks()  
        itemName: Name of the Create function (e.g., "CreateFlexibleBody")
        
    Returns:
        Tuple (start_page, end_page) if found, (None, None) if not found
    """
    try:
        page = findFunctionPageInCreateSection(pdfPath, bookmarks, itemName)
        
        if page:
            # For Create functions, assume they span 2-3 pages
            return page, page + 2
        
        return None, None
        
    except Exception as e:
        from core.debug import debugError
        debugError(f"Error finding Create item page range for {itemName}: {e}", origin="Help")
        return None, None