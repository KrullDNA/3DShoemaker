# -*- coding: utf-8 -*-
"""Name all objects in document with standardized names.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import scriptcontext as sc

__commandname__ = "NameObjectsInDoc"

# ---- Constants ----
_SLM_LAYER_PREFIX = "SLM"


# ---- Command ----

def RunCommand(is_interactive):
    doc = sc.doc
    prefix = _SLM_LAYER_PREFIX
    named_count = 0

    # Iterate all objects and assign standardized names based on layer
    enum_settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    enum_settings.DeletedObjects = False
    enum_settings.HiddenObjects = True
    enum_settings.LockedObjects = True

    for obj in doc.Objects.GetObjectList(enum_settings):
        layer = doc.Layers[obj.Attributes.LayerIndex]
        full_path = layer.FullPath

        if not full_path.startswith(prefix):
            continue

        # Derive category from layer path
        parts = full_path.split("::")
        category = parts[-1] if len(parts) > 1 else prefix

        # Build a standardized name: SLM_{Category}_{TypeAbbrev}_{Index}
        geom = obj.Geometry
        if isinstance(geom, Rhino.Geometry.Brep):
            type_abbrev = "Brep"
        elif isinstance(geom, Rhino.Geometry.Mesh):
            type_abbrev = "Mesh"
        elif isinstance(geom, Rhino.Geometry.Curve):
            type_abbrev = "Crv"
        elif isinstance(geom, Rhino.Geometry.Surface):
            type_abbrev = "Srf"
        elif isinstance(geom, Rhino.Geometry.Point):
            type_abbrev = "Pt"
        else:
            type_abbrev = "Obj"

        new_name = "SLM_{0}_{1}_{2:04d}".format(category, type_abbrev, named_count)
        attrs = obj.Attributes.Duplicate()
        attrs.Name = new_name
        doc.Objects.ModifyAttributes(obj, attrs, True)
        named_count += 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "[Feet in Focus Shoe Kit] Named {0} object(s) with standardized names.".format(
            named_count
        )
    )
    return 0
