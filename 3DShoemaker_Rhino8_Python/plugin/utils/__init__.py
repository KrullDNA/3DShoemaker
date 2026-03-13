"""
Feet in Focus Shoe Kit Rhino 8 Plugin - Utility modules.

Provides geometry helpers, JSON serialization,
layer management, curve snapping, and squeeze deformation utilities.
"""

from plugin.utils.geometry_utils import GeometryUtils
from plugin.utils.json_serializer import JsonSerializer
from plugin.utils.layer_manager import LayerManager
from plugin.utils.snap_curves import SnapCurves
from plugin.utils.squeeze import Squeeze

__all__ = [
    "GeometryUtils",
    "JsonSerializer",
    "LayerManager",
    "SnapCurves",
    "Squeeze",
]
