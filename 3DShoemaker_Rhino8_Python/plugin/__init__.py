"""
Feet in Focus Shoe Kit - Shoe Last Making CAD Plugin for Rhino 8 (Python 3)

A Python 3 port of the PodoCAD .NET plugin for Rhinoceros 8.
Provides tools for designing and manufacturing shoe lasts, insoles,
and related footwear components.

Namespace equivalent: PodoCAD
"""

__version__ = "1.0"
__author__ = "Feet in Focus"
__plugin_name__ = "FIFShoeKit"
__plugin_url__ = "https://ShoeLastMaker.com"

# Layer name prefix used by the plugin
SLM_LAYER_PREFIX = "SLM"

# Object class identifiers
CLASS_LAST = "Last"
CLASS_INSERT = "Insert"
CLASS_BOTTOM = "Bottom"
CLASS_FOOT = "Foot"
ALL_CLASSES = [CLASS_LAST, CLASS_INSERT, CLASS_BOTTOM, CLASS_FOOT]

# Document user text keys
DOC_KEY_PREFIX = "FIFShoeKit"
DOC_KEY_GEOMETRIES = f"{DOC_KEY_PREFIX}_Geometries"
DOC_KEY_SETTINGS = f"{DOC_KEY_PREFIX}_Settings"
DOC_KEY_VERSION = f"{DOC_KEY_PREFIX}_Version"
DOC_KEY_MATERIAL_THICKNESSES = f"{DOC_KEY_PREFIX}_MaterialThicknesses"

# Default layer colours (R, G, B) keyed by layer name suffix
DEFAULT_LAYER_COLORS = {
    "Last": (0, 128, 255),
    "Insert": (255, 165, 0),
    "Bottom": (128, 0, 128),
    "Foot": (255, 80, 80),
    "Construction": (180, 180, 180),
    "Measurements": (0, 200, 0),
}

from plugin.plugin_main import PodoCADPlugIn
from plugin.document_settings import DocumentSettings
from plugin.material_thicknesses import MaterialThicknesses
from plugin.preview_module import PreviewConduitClass, PreviewObject
