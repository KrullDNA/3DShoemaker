"""
layer_manager.py - Layer management for 3DShoemaker.

Creates, deletes, and manages the layer hierarchy that the 3DShoemaker
plugin uses to organize shoe-last geometry inside a Rhino document.

Layer tree structure::

    SLM
    +-- Last
    +-- Insert
    +-- Bottom
    +-- Foot
    +-- Dimensions
    +-- ClippingPlanes
    +-- Mockup
    +-- Construction
    +-- Measurements
    +-- Export
    +-- Reference
    +-- CrossSections
    +-- FlatPattern

Each category can contain sub-layers created on demand by specific
commands (e.g. ``SLM::Last::TopSurface``).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import Rhino
import Rhino.DocObjects
import System.Drawing


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PREFIX = "SLM"

# (layer_suffix, (R, G, B))
_LAYER_DEFINITIONS: List[Tuple[str, Tuple[int, int, int]]] = [
    ("Last",            (0, 128, 255)),
    ("Insert",          (255, 165, 0)),
    ("Bottom",          (128, 0, 128)),
    ("Foot",            (255, 80, 80)),
    ("Dimensions",      (0, 180, 0)),
    ("ClippingPlanes",  (120, 120, 120)),
    ("Mockup",          (80, 160, 220)),
    ("Construction",    (180, 180, 180)),
    ("Measurements",    (0, 200, 0)),
    ("Export",          (200, 200, 0)),
    ("Reference",       (160, 160, 200)),
    ("CrossSections",   (200, 120, 60)),
    ("FlatPattern",     (60, 200, 160)),
]

# Deprecated layer names that should be cleaned up by DeleteOldLayers
_DEPRECATED_LAYERS: List[str] = [
    "SLM::Insole",       # renamed to Insert
    "SLM::Outsole",      # renamed to Bottom
    "SLM::Scan",         # renamed to Foot
    "SLM::Temp",
    "SLM::Debug",
]


# ---------------------------------------------------------------------------
# LayerManager
# ---------------------------------------------------------------------------

class LayerManager:
    """Manages the SLM layer hierarchy in a Rhino document.

    All public methods are static and operate on an explicit
    ``Rhino.RhinoDoc`` parameter.
    """

    # ======================================================================
    # Setup / teardown
    # ======================================================================

    @staticmethod
    def SetupLayers(doc: Rhino.RhinoDoc) -> None:
        """Create all required SLM layers in *doc*.

        Idempotent -- layers that already exist are left untouched.
        """
        if doc is None:
            return

        # Ensure the root SLM layer
        parent_index = LayerManager.FindByFullPath(doc, _PREFIX)
        if parent_index < 0:
            parent_layer = Rhino.DocObjects.Layer()
            parent_layer.Name = _PREFIX
            parent_layer.Color = System.Drawing.Color.FromArgb(100, 100, 100)
            parent_index = doc.Layers.Add(parent_layer)

        if parent_index < 0:
            return  # cannot create layers

        parent_id = doc.Layers[parent_index].Id

        # Create child layers
        for suffix, (r, g, b) in _LAYER_DEFINITIONS:
            full_path = f"{_PREFIX}::{suffix}"
            idx = LayerManager.FindByFullPath(doc, full_path)
            if idx < 0:
                child = Rhino.DocObjects.Layer()
                child.Name = suffix
                child.ParentLayerId = parent_id
                child.Color = System.Drawing.Color.FromArgb(r, g, b)
                doc.Layers.Add(child)

        doc.Views.Redraw()

    @staticmethod
    def DeleteAllSLMLayers(doc: Rhino.RhinoDoc) -> int:
        """Remove every SLM layer and all objects they contain.

        Returns the number of layers deleted.
        """
        if doc is None:
            return 0

        table = doc.Layers
        indices: List[int] = []

        for i in range(table.Count):
            layer = table[i]
            if layer.IsDeleted:
                continue
            fp = layer.FullPath
            if fp == _PREFIX or fp.startswith(f"{_PREFIX}::"):
                indices.append(i)

        # Delete objects on those layers
        for idx in indices:
            layer = table[idx]
            objs = doc.Objects.FindByLayer(layer)
            if objs:
                for obj in objs:
                    doc.Objects.Delete(obj, True)

        # Delete layers from deepest to shallowest
        removed = 0
        for idx in sorted(indices, reverse=True):
            if table.Delete(idx, True):
                removed += 1

        if removed:
            doc.Views.Redraw()
        return removed

    @staticmethod
    def DeleteOldLayers(doc: Rhino.RhinoDoc) -> int:
        """Remove deprecated / renamed layers left over from older plugin
        versions.

        Returns the number of layers deleted.
        """
        if doc is None:
            return 0

        removed = 0
        for full_path in _DEPRECATED_LAYERS:
            idx = LayerManager.FindByFullPath(doc, full_path)
            if idx < 0:
                continue
            layer = doc.Layers[idx]
            # Delete objects on the layer first
            objs = doc.Objects.FindByLayer(layer)
            if objs:
                for obj in objs:
                    doc.Objects.Delete(obj, True)
            if doc.Layers.Delete(idx, True):
                removed += 1

        if removed:
            doc.Views.Redraw()
        return removed

    # ======================================================================
    # Finders
    # ======================================================================

    @staticmethod
    def FindByFullPath(
        doc: Rhino.RhinoDoc, full_path: str,
    ) -> int:
        """Find a layer by its full path (e.g. ``SLM::Last``).

        Returns the layer index, or -1 if not found.
        """
        if doc is None or not full_path:
            return -1
        return doc.Layers.FindByFullPath(full_path, -1)

    @staticmethod
    def FindByName(
        doc: Rhino.RhinoDoc, name: str,
    ) -> int:
        """Find the first layer whose short name matches *name*.

        Returns the layer index, or -1 if not found.

        Note: this may match layers outside the SLM hierarchy.  Prefer
        ``FindByFullPath`` when the full path is known.
        """
        if doc is None or not name:
            return -1
        for i in range(doc.Layers.Count):
            layer = doc.Layers[i]
            if not layer.IsDeleted and layer.Name == name:
                return i
        return -1

    @staticmethod
    def FindSLMLayerByName(
        doc: Rhino.RhinoDoc, name: str,
    ) -> int:
        """Find an SLM child layer by its short name.

        Equivalent to ``FindByFullPath(doc, "SLM::<name>")``.
        """
        return LayerManager.FindByFullPath(doc, f"{_PREFIX}::{name}")

    # ======================================================================
    # Current layer
    # ======================================================================

    @staticmethod
    def SetCurrentLayerIndex(
        doc: Rhino.RhinoDoc, index: int,
    ) -> bool:
        """Set the current (active) layer by index.

        Returns True on success.
        """
        if doc is None or index < 0:
            return False
        try:
            doc.Layers.SetCurrentLayerIndex(index, True)
            return True
        except Exception:
            return False

    @staticmethod
    def SetCurrentLayerByFullPath(
        doc: Rhino.RhinoDoc, full_path: str,
    ) -> bool:
        """Set the current layer by its full path.

        Returns True on success, False if the layer was not found.
        """
        idx = LayerManager.FindByFullPath(doc, full_path)
        if idx < 0:
            return False
        return LayerManager.SetCurrentLayerIndex(doc, idx)

    # ======================================================================
    # Visibility
    # ======================================================================

    @staticmethod
    def UpdateLayerVisibility(
        doc: Rhino.RhinoDoc,
        full_path: str,
        visible: bool,
    ) -> bool:
        """Set the visibility of a layer (and optionally its children).

        Parameters
        ----------
        doc : RhinoDoc
        full_path : str
            Full layer path.
        visible : bool
            True to show, False to hide.

        Returns True on success.
        """
        idx = LayerManager.FindByFullPath(doc, full_path)
        if idx < 0:
            return False
        layer = doc.Layers[idx]
        layer.IsVisible = visible
        layer.CommitChanges()
        doc.Views.Redraw()
        return True

    @staticmethod
    def SetSLMLayerVisibility(
        doc: Rhino.RhinoDoc,
        suffix: str,
        visible: bool,
    ) -> bool:
        """Show or hide an SLM child layer by suffix.

        ``SetSLMLayerVisibility(doc, "Mockup", False)`` hides ``SLM::Mockup``.
        """
        return LayerManager.UpdateLayerVisibility(
            doc, f"{_PREFIX}::{suffix}", visible,
        )

    @staticmethod
    def ShowAllSLMLayers(doc: Rhino.RhinoDoc) -> None:
        """Make every SLM layer visible."""
        if doc is None:
            return
        for i in range(doc.Layers.Count):
            layer = doc.Layers[i]
            if layer.IsDeleted:
                continue
            fp = layer.FullPath
            if fp == _PREFIX or fp.startswith(f"{_PREFIX}::"):
                if not layer.IsVisible:
                    layer.IsVisible = True
                    layer.CommitChanges()
        doc.Views.Redraw()

    @staticmethod
    def HideAllSLMLayers(doc: Rhino.RhinoDoc) -> None:
        """Hide every SLM layer."""
        if doc is None:
            return
        for i in range(doc.Layers.Count):
            layer = doc.Layers[i]
            if layer.IsDeleted:
                continue
            fp = layer.FullPath
            if fp == _PREFIX or fp.startswith(f"{_PREFIX}::"):
                if layer.IsVisible:
                    layer.IsVisible = False
                    layer.CommitChanges()
        doc.Views.Redraw()

    # ======================================================================
    # Sub-layer creation helpers
    # ======================================================================

    @staticmethod
    def EnsureSubLayer(
        doc: Rhino.RhinoDoc,
        parent_full_path: str,
        child_name: str,
        color: Optional[System.Drawing.Color] = None,
    ) -> int:
        """Ensure a child layer exists under *parent_full_path*.

        Creates the layer if it does not exist.  Returns the child layer
        index, or -1 on failure.
        """
        if doc is None:
            return -1

        full_path = f"{parent_full_path}::{child_name}"
        idx = LayerManager.FindByFullPath(doc, full_path)
        if idx >= 0:
            return idx

        parent_idx = LayerManager.FindByFullPath(doc, parent_full_path)
        if parent_idx < 0:
            return -1

        parent_id = doc.Layers[parent_idx].Id
        child = Rhino.DocObjects.Layer()
        child.Name = child_name
        child.ParentLayerId = parent_id
        if color is not None:
            child.Color = color
        else:
            # Inherit parent colour
            child.Color = doc.Layers[parent_idx].Color
        return doc.Layers.Add(child)

    @staticmethod
    def EnsureSLMSubLayer(
        doc: Rhino.RhinoDoc,
        category: str,
        child_name: str,
        color: Optional[System.Drawing.Color] = None,
    ) -> int:
        """Convenience: ensure a sub-layer under ``SLM::<category>``.

        Example::

            LayerManager.EnsureSLMSubLayer(doc, "Last", "TopSurface")
            # creates SLM::Last::TopSurface
        """
        return LayerManager.EnsureSubLayer(
            doc, f"{_PREFIX}::{category}", child_name, color,
        )

    # ======================================================================
    # Query helpers
    # ======================================================================

    @staticmethod
    def GetSLMLayerNames(doc: Rhino.RhinoDoc) -> List[str]:
        """Return the full paths of all SLM layers in *doc*."""
        if doc is None:
            return []
        result: List[str] = []
        for i in range(doc.Layers.Count):
            layer = doc.Layers[i]
            if layer.IsDeleted:
                continue
            fp = layer.FullPath
            if fp == _PREFIX or fp.startswith(f"{_PREFIX}::"):
                result.append(fp)
        return result

    @staticmethod
    def GetLayerColor(
        doc: Rhino.RhinoDoc, full_path: str,
    ) -> Optional[System.Drawing.Color]:
        """Return the colour of a layer, or None if not found."""
        idx = LayerManager.FindByFullPath(doc, full_path)
        if idx < 0:
            return None
        return doc.Layers[idx].Color

    @staticmethod
    def SetLayerColor(
        doc: Rhino.RhinoDoc, full_path: str,
        color: System.Drawing.Color,
    ) -> bool:
        """Set the colour of a layer.  Returns True on success."""
        idx = LayerManager.FindByFullPath(doc, full_path)
        if idx < 0:
            return False
        layer = doc.Layers[idx]
        layer.Color = color
        layer.CommitChanges()
        return True

    # ======================================================================
    # Repr
    # ======================================================================

    def __repr__(self) -> str:
        return "<LayerManager>"
