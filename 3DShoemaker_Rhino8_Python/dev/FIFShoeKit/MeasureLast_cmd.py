# -*- coding: utf-8 -*-
"""Measures last dimensions including girths at cross sections.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Geometry as rg
import Rhino.Commands as rc
import Rhino.DocObjects as rdo
import scriptcontext as sc
import System

__commandname__ = "MeasureLast"


def _find_last_brep(doc):
    """Find the last brep in the document by searching known layer paths."""
    layer_paths = [
        "Feet in Focus Shoe Kit::Last",
        "SLM::Last",
    ]
    for path in layer_paths:
        layer_idx = doc.Layers.FindByFullPath(path, -1)
        if layer_idx >= 0:
            layer = doc.Layers[layer_idx]
            objs = doc.Objects.FindByLayer(layer)
            if objs:
                for obj in objs:
                    if isinstance(obj.Geometry, rg.Brep):
                        return obj.Geometry
    return None


def _find_named_curve(doc, name):
    """Find a named curve in the document."""
    settings = rdo.ObjectEnumeratorSettings()
    settings.NameFilter = name
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        if isinstance(obj.Geometry, rg.Curve):
            return obj.Geometry
    return None


def _measure_brep(brep):
    """Measure basic dimensions of a brep."""
    bbox = brep.GetBoundingBox(True)
    if not bbox.IsValid:
        return {}

    measurements = {}
    measurements["Length"] = bbox.Max.Y - bbox.Min.Y
    measurements["Width"] = bbox.Max.X - bbox.Min.X
    measurements["Height"] = bbox.Max.Z - bbox.Min.Z
    return measurements


def RunCommand(is_interactive):
    doc = sc.doc

    try:
        last_brep = _find_last_brep(doc)
        if last_brep is None:
            Rhino.RhinoApp.WriteLine("No active last found. Build or import a last first.")
            return rc.Result.Failure

        # Measure bounding box dimensions
        measurements = _measure_brep(last_brep)

        # Check for stored parameter values in sticky
        ds = sc.sticky.get("FIF_DocumentSettings", {})
        param_names = [
            ("Ball Width", "BallWidth"),
            ("Ball Width Perp", "BallWidthPerp"),
            ("Heel Width", "HeelWidth"),
            ("Ball Girth", "BallGirth"),
            ("Instep Girth", "InstepGirth"),
            ("Waist Girth", "WaistGirth"),
            ("Waist2 Girth", "Waist2Girth"),
            ("Arch Girth", "ArchGirth"),
            ("Heel Girth", "HeelGirth"),
            ("Ankle Girth", "AnkleGirth"),
            ("Heel Height", "last_heel_height_mm"),
            ("Toe Spring", "ToeSpring"),
            ("Ball Break Angle", "BallBreakPointAngle"),
            ("Ball Roll Bulge", "BallRollBulge"),
            ("Ball Line Ratio", "BallLineRatio"),
            ("Arch Length", "ArchLength"),
        ]

        for display_name, key in param_names:
            val = ds.get(key, None)
            if val is not None and val != 0:
                measurements[display_name] = val

        Rhino.RhinoApp.WriteLine("")
        Rhino.RhinoApp.WriteLine("=== Last Measurements ===")
        for name, value in measurements.items():
            if value is not None and value != 0:
                Rhino.RhinoApp.WriteLine("  {0}: {1:.2f}".format(name, value))

        # Measure actual girth curves if present in document
        girth_names = {
            "Ball Girth": "CBG",
            "Instep Girth": "CIG",
            "Waist Girth": "CWG",
            "Waist2 Girth": "CW2G",
        }

        has_girth_curves = False
        for display_name, curve_name in girth_names.items():
            curve = _find_named_curve(doc, curve_name)
            if curve is not None:
                if not has_girth_curves:
                    Rhino.RhinoApp.WriteLine("")
                    Rhino.RhinoApp.WriteLine("=== Measured Girths ===")
                    has_girth_curves = True
                length = curve.GetLength()
                Rhino.RhinoApp.WriteLine("  {0}: {1:.2f}".format(display_name, length))

        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error measuring last: {0}".format(e))
        return rc.Result.Failure
