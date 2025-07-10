# Exudyn GUI - Model Builder

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: BSD-3](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
[![Exudyn](https://img.shields.io/badge/Exudyn-Compatible-green.svg)](https://github.com/jgerstmayr/EXUDYN)

A user-friendly graphical interface for the **Exudyn** multibody dynamics simulation framework. ExudynGUI provides an intuitive way to create, visualize, and simulate complex mechanical systems without writing code.

> **⚠️ Alpha Version Notice**  
> ExudynGUI is currently in **alpha development** (v0.4). While functional, the API may change and some features are still being developed.

![Exudyn GUI Screenshot](https://fileshare.uibk.ac.at/f/0a4a1d65b3b7405c8aea/?dl=1)


## 📦 Installation

### Prerequisites

ExudynGUI requires **Exudyn** to be installed first. Install Exudyn from:
- **PyPI**: `pip install exudyn`
- **GitHub Repository**: [https://github.com/jgerstmayr/EXUDYN](https://github.com/jgerstmayr/EXUDYN)

### Install ExudynGUI

#### Option 1: Install from PyPI (Recommended)
```bash
pip install exudynGUI
```

#### Option 2: Install from Source
```bash
git clone https://github.com/MichaelUIBK/exudynGUI.git
cd exudynGUI
pip install -e .
```

#### Option 3: Development Installation
```bash
git clone https://github.com/MichaelUIBK/exudynGUI.git
cd exudynGUI
pip install -e ".[dev]"
```

### Dependencies

**Core Dependencies:**
- Python 3.8+
- PyQt5 >= 5.15.0
- NumPy >= 1.20.0
- Exudyn (multibody simulation engine)

**Optional Dependencies:**
- PyMuPDF >= 1.20.0 (PDF documentation support)
- QScintilla >= 2.14.0 (advanced code editor)
- IPython >= 7.0.0 (enhanced console)

## 🎯 Quick Start

### Launch the GUI
```bash
# From command line (after installation)
exudynGUI

# Or from Python
python -m exudynGUI
```

### Finding Installation Directory
When installed via pip, ExudynGUI files are located in your Python environment:

```python
# Find the installation path
import exudynGUI
import os
print(f"ExudynGUI installed at: {os.path.dirname(exudynGUI.__file__)}")
```

**Common locations:**
- **Conda environment**: `~/anaconda3/envs/your_env/lib/python3.x/site-packages/exudynGUI/`
- **System Python**: `~/python3.x/site-packages/exudynGUI/`
- **Virtual environment**: `your_venv/lib/python3.x/site-packages/exudynGUI/`

This directory contains examples, exudyn documentation, STL files, and other resources.

### Create Your First Model
1. **Start ExudynGUI** - Launch the application
2. **Add Components** - Use the "Create" button to add bodies, joints, and forces
3. **Set Properties** - Configure mass, stiffness, and other parameters
4. **Run Simulation** - Click the simulation controls to start
5. **Analyze Results** - View the 3D animation and export data

## 📖 Documentation

### Built-in Help
- **F1** - Open online documentation
- **Help Menu** - Access online PDF documentation and examples
- **Tooltips** - Hover over controls for quick information

### External Resources
- **Exudyn Documentation**: [https://exudyn.readthedocs.io/](https://exudyn.readthedocs.io/)


### Key Components
- **Model Manager**: Handles Exudyn model lifecycle
- **Object Registry**: Tracks and manages simulation objects
- **Renderer Interface**: 3D visualization and interaction
- **Property Editor**: Dynamic form generation for object properties
- **Script Generator**: Exports GUI models to Python code


### Get Help
- **GitHub Issues**: [Report bugs or request features](https://github.com/MichaelUIBK/exudynGUI/issues)
- **Discussions**: [Community discussions](https://github.com/MichaelUIBK/exudynGUI/discussions)
- **Email**: michael.pieber@uibk.ac.at

## 📄 License

ExudynGUI is released under the **BSD 3-Clause License**. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **Johannes Gerstmayr** and the Exudyn team for the excellent simulation framework
- Modern AI development tools for accelerating the development process

## 📈 Project Status

**Current Version**: 0.4.3 (Glockturm)
**Status**: Alpha - Active Development
**Stability**: Experimental - API may change

### Roadmap
- [ ] Menu bar
- [ ] Add drag-and-drop or reorder support in the model tree
- [ ] Allow commenting or grouping of tree items
- [ ] Implement a global search bar for components or fields
- [ ] Improve real-time preview/update in Exudyn viewer during parameter edits
- [ ] Plugin marketplace
- [ ] Add predefined examples to load and try out different models
- [ ] exuPilot, a future AI-assisted features (placeholder)
- [ ] Fem module integration
- [ ] Robotics module integration
- [ ] And much more...

---

## *If ExudynGUI helps your work, please consider giving it a ⭐ star!*
