# -*- coding: utf-8 -*-
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# This is part of the Exudyn GUI project
#
# Filename: core\helpUltis.py
#
# Description:
#     Provides help utilities for model elements (objects, nodes, etc.).
#     Includes support for:
#       - Legacy field metadata help with descriptions, types, defaults
#       - Full help extraction for Create* functions
#       - Docstring fallback and usage notes
#
#     Used in GUI for context-sensitive help, tooltips, and documentation links.
#
# Authors:  Michael Pieber
# Date:     2025-05-16
#
# License:  BSD 3-Clause License
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def get_legacy_help_from_metadata(typeName):
    """Get help from field metadata, enhanced with PDF description when available."""
    try:
        from exudynGUI.core.fieldMetadata import FieldMetadataBuilder
        builder = FieldMetadataBuilder(useExtracted=True)
        metadata = builder.build(typeName)
        if metadata and len(metadata) > 0:
            help_lines = [f"Exudyn {typeName} Parameters"]
            help_lines.append("=" * 50)
            help_lines.append("")
            param_count = 0
            for field_name, field_info in metadata.items():
                desc = field_info.get('description', '')
                field_type = field_info.get('type', '')
                default_val = field_info.get('defaultValue', field_info.get('default', ''))
                help_lines.append(f"  • {field_name}")
                if field_type:
                    help_lines.append(f"    Type: {field_type}")
                if default_val != '':
                    help_lines.append(f"    Default: {default_val}")
                if desc:
                    clean_desc = desc.replace('\n', ' ').strip()
                    help_lines.append(f"    Description: {clean_desc}")
                param_count += 1
                if param_count >= 20:
                    help_lines.append(f"  ... and {len(metadata) - param_count} more parameters")
                    break
            return '\n'.join(help_lines)
    except Exception as e:
        return None
    return None

def get_full_exudyn_help(typeName):
    """Get full help text for a model element type from Exudyn's internal help system, without creating a new SystemContainer or MainSystem."""
    try:
        import exudyn as exu
        import io
        import inspect
        from contextlib import redirect_stdout
        func = None
        if typeName.startswith("Create"):
            func = getattr(exu.MainSystem, typeName, None)
        if func is None:
            func = getattr(exu, typeName, None)
        if func is not None and typeName.startswith("Create"):
            help_lines = []
            help_lines.append(f"Exudyn {typeName} - High-Level Creation Function")
            help_lines.append("=" * 60)
            help_lines.append("")
            try:
                sig = inspect.signature(func)
                help_lines.append(f"Function signature:")
                help_lines.append(f"  {typeName}{sig}")
                help_lines.append("")
            except Exception:
                pass
            doc = func.__doc__
            if not doc:
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
            return '\n'.join(help_lines)
        # --- Enhanced legacy help logic ---
        if typeName.startswith(("Object", "Node", "Marker", "Load", "Sensor")):
            # 1. Try metadata (rich parameter info)
            try:
                result = get_legacy_help_from_metadata(typeName)
                if result and len(result) > 50:
                    return result
            except Exception:
                pass
            # 2. Try class docstring
            try:
                obj = getattr(exu, typeName, None)
                if obj and hasattr(obj, '__doc__') and obj.__doc__:
                    return obj.__doc__.strip()
            except Exception:
                pass
            # 3. Fallback
            category = "Legacy object type"
            return f"No specific documentation found for '{typeName}'.\n\n{typeName} is a {category} in the Exudyn library.\n\nFor detailed documentation, please refer to:\n• The official Exudyn documentation (theDoc.pdf)\n• Online resources: https://github.com/jgerstmayr/EXUDYN\n• Tutorials and examples: https://github.com/jgerstmayr/EXUDYN#tutorial\n\nUse the PDF help button (if available) to view relevant documentation pages."
        # Fallback for anything else
        category = "Create function" if typeName.startswith("Create") else "Legacy object type"
        return f"No specific documentation found for '{typeName}'.\n\n{typeName} is a {category} in the Exudyn library.\n\nFor detailed documentation, please refer to:\n• The official Exudyn documentation (theDoc.pdf)\n• Online resources: https://github.com/jgerstmayr/EXUDYN\n• Tutorials and examples: https://github.com/jgerstmayr/EXUDYN#tutorial\n\nUse the PDF help button (if available) to view relevant documentation pages."
    except Exception as e:
        return f"Error accessing help for {typeName}: {str(e)}" 