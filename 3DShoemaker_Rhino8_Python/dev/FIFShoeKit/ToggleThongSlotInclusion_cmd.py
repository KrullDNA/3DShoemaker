# -*- coding: utf-8 -*-
"""Toggle thong slot visibility/inclusion in the sandal model.

Shows or hides the thong slot objects.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import scriptcontext as sc

__commandname__ = "ToggleThongSlotInclusion"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _find_objects_by_prefix(doc, prefix):
    """Return all objects whose name starts with prefix."""
    results = []
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    settings.HiddenObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name.startswith(prefix):
            results.append(obj)
    return results


# ---------------------------------------------------------------------------
#  Command entry point
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    # Find thong slot objects
    slot_objs = _find_objects_by_prefix(doc, "ThongSlot")
    if not slot_objs:
        Rhino.RhinoApp.WriteLine(
            "No thong slot found.  Use AddThongSlot first."
        )
        return Rhino.Commands.Result.Nothing

    # Toggle visibility
    toggled = 0
    for obj in slot_objs:
        is_hidden = obj.Attributes.Visible is False or obj.IsHidden
        if is_hidden:
            doc.Objects.Show(obj, True)
            Rhino.RhinoApp.WriteLine(
                "  Showing: {0}".format(obj.Attributes.Name)
            )
        else:
            doc.Objects.Hide(obj, True)
            Rhino.RhinoApp.WriteLine(
                "  Hiding: {0}".format(obj.Attributes.Name)
            )
        toggled += 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Toggled {0} thong slot object(s).".format(toggled)
    )
    return Rhino.Commands.Result.Success
