# -*- coding: utf-8 -*-
"""Grade complete footwear to a different size.

Supports grading of insole, outline, third-party insole, and general
geometries.  Updates CBG (ball girth) and CIG (instep girth)
measurements during the grading process.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import traceback

import Rhino
import Rhino.Commands
import Rhino.DocObjects
import Rhino.Geometry
import Rhino.Input
import Rhino.Input.Custom
import Rhino.RhinoApp
import scriptcontext as sc
import System

__commandname__ = "GradeFootwear"


# ---------------------------------------------------------------------------
#  Constants (inlined from plugin)
# ---------------------------------------------------------------------------

_SLM_LAYER_PREFIX = "SLM"
_ALL_CLASSES = ["Last", "Insert", "Bottom", "Foot"]

# Standard EU size grading increment (mm) per full size step
_EU_GRADE_INCREMENT_LENGTH = 6.667
_EU_GRADE_INCREMENT_WIDTH = 1.5
_EU_GRADE_INCREMENT_GIRTH = 5.0

# Size-system conversion tables
_SIZE_SYSTEMS = {
    "EU": {"base_size": 40.0, "base_stick_length": 260.0,
           "increment": _EU_GRADE_INCREMENT_LENGTH},
    "US": {"base_size": 8.0, "base_stick_length": 260.0,
           "increment": 8.467},
    "UK": {"base_size": 7.0, "base_stick_length": 260.0,
           "increment": 8.467},
    "Mondopoint": {"base_size": 260.0, "base_stick_length": 260.0,
                   "increment": 5.0},
}

# Document user text keys
_DOC_KEY_PREFIX = "FIFShoeKit"
_DOC_KEY_SETTINGS = _DOC_KEY_PREFIX + "_Settings"


# ---------------------------------------------------------------------------
#  Grading helpers (inlined from grade_commands.py)
# ---------------------------------------------------------------------------

def _compute_scale_factor(from_size, to_size, size_system):
    """Return the uniform length scale factor for grading between two sizes."""
    info = _SIZE_SYSTEMS.get(size_system, _SIZE_SYSTEMS["EU"])
    from_length = info["base_stick_length"] + (from_size - info["base_size"]) * info["increment"]
    to_length = info["base_stick_length"] + (to_size - info["base_size"]) * info["increment"]
    if abs(from_length) < 1e-9:
        return 1.0
    return to_length / from_length


def _compute_girth_delta(from_size, to_size):
    """Return the girth adjustment (mm) when grading between sizes."""
    return (to_size - from_size) * _EU_GRADE_INCREMENT_GIRTH


def _build_grade_transform(scale_factor, origin):
    """Build a uniform scale transform about *origin*."""
    return Rhino.Geometry.Transform.Scale(origin, scale_factor)


def _find_objects_by_name_prefix(doc, prefix):
    """Return all doc objects whose name starts with *prefix*."""
    results = []
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    settings.HiddenObjects = True
    settings.LockedObjects = True
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name.startswith(prefix):
            results.append(obj)
    return results


def _find_objects_on_layer(doc, layer_name):
    """Return all doc objects residing on *layer_name*."""
    layer_index = doc.Layers.FindByFullPath(layer_name, -1)
    if layer_index < 0:
        for i in range(doc.Layers.Count):
            lyr = doc.Layers[i]
            if not lyr.IsDeleted and lyr.Name == layer_name:
                layer_index = i
                break
    if layer_index < 0:
        return []
    layer = doc.Layers[layer_index]
    objs = doc.Objects.FindByLayer(layer)
    if objs:
        return list(objs)
    return []


def _get_doc_setting(doc, key, default=None):
    """Read a setting from document user text."""
    import json
    raw = doc.Strings.GetValue(_DOC_KEY_SETTINGS, key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _set_doc_setting(doc, key, value):
    """Write a setting to document user text."""
    import json
    doc.Strings.SetString(_DOC_KEY_SETTINGS, key, json.dumps(value))


def _get_orientation_origin(doc):
    """Try to locate the heel-centre point stored on the document."""
    origin = Rhino.Geometry.Point3d.Origin
    # Look for an object named HeelCentre
    settings = Rhino.DocObjects.ObjectEnumeratorSettings()
    settings.DeletedObjects = False
    for obj in doc.Objects.GetObjectList(settings):
        name = obj.Attributes.Name or ""
        if name == "HeelCentre":
            pt_geom = obj.Geometry
            if isinstance(pt_geom, Rhino.Geometry.Point):
                origin = pt_geom.Location
            elif hasattr(pt_geom, "PointAtStart"):
                origin = pt_geom.PointAtStart
            break
    return origin


# ---------------------------------------------------------------------------
#  Grading sub-operations
# ---------------------------------------------------------------------------

def _grade_insole(doc, scale_factor, origin):
    """Scale all insole geometry by *scale_factor* about *origin*."""
    xform = _build_grade_transform(scale_factor, origin)
    objs = _find_objects_by_name_prefix(doc, "Insole")
    if not objs:
        Rhino.RhinoApp.WriteLine("  No insole objects found to grade.")
        return False
    for obj in objs:
        doc.Objects.Transform(obj, xform, True)
    Rhino.RhinoApp.WriteLine(
        "  Graded {0} insole object(s).".format(len(objs))
    )
    return True


def _grade_outline(doc, scale_factor, origin):
    """Scale all outline/last-outline curves by *scale_factor*."""
    xform = _build_grade_transform(scale_factor, origin)
    objs = _find_objects_by_name_prefix(doc, "Outline")
    objs += _find_objects_by_name_prefix(doc, "LastOutline")
    if not objs:
        Rhino.RhinoApp.WriteLine("  No outline objects found to grade.")
        return False
    for obj in objs:
        doc.Objects.Transform(obj, xform, True)
    Rhino.RhinoApp.WriteLine(
        "  Graded {0} outline object(s).".format(len(objs))
    )
    return True


def _grade_other_party_insole(doc, scale_factor, origin):
    """Scale third-party insole geometry if present."""
    xform = _build_grade_transform(scale_factor, origin)
    objs = _find_objects_by_name_prefix(doc, "OtherPartyInsole")
    objs += _find_objects_by_name_prefix(doc, "ThirdPartyInsole")
    if not objs:
        return False
    for obj in objs:
        doc.Objects.Transform(obj, xform, True)
    Rhino.RhinoApp.WriteLine(
        "  Graded {0} third-party insole object(s).".format(len(objs))
    )
    return True


def _grade_geometries(doc, scale_factor, origin):
    """Scale all remaining SLM-layer geometry by *scale_factor*."""
    xform = _build_grade_transform(scale_factor, origin)
    graded_count = 0
    for cls in _ALL_CLASSES:
        full_path = "{0}::{1}".format(_SLM_LAYER_PREFIX, cls)
        objs = _find_objects_on_layer(doc, full_path)
        for obj in objs:
            doc.Objects.Transform(obj, xform, True)
            graded_count += 1
    if graded_count:
        Rhino.RhinoApp.WriteLine(
            "  Graded {0} general geometry object(s).".format(graded_count)
        )
    return graded_count > 0


def _update_girth_measurements(doc, from_size, to_size):
    """Update CBG and CIG values stored in the document after grading."""
    delta = _compute_girth_delta(from_size, to_size)
    cbg = _get_doc_setting(doc, "cbg_ball_girth", 0.0)
    cig = _get_doc_setting(doc, "cig_instep_girth", 0.0)
    if cbg:
        _set_doc_setting(doc, "cbg_ball_girth", cbg + delta)
    if cig:
        _set_doc_setting(doc, "cig_instep_girth", cig + delta)
    Rhino.RhinoApp.WriteLine(
        "  Updated girth measurements: CBG delta={0:+.2f} mm, "
        "CIG delta={1:+.2f} mm".format(delta, delta)
    )


# ---------------------------------------------------------------------------
#  RunCommand
# ---------------------------------------------------------------------------

def RunCommand(is_interactive):
    doc = sc.doc

    current_size = _get_doc_setting(doc, "last_size", 0.0)
    size_system = _get_doc_setting(doc, "last_size_system", "EU")

    if current_size is None or current_size <= 0:
        Rhino.RhinoApp.WriteLine(
            "No current size is set.  Please run NewBuild or UpdateLast first."
        )
        return Rhino.Commands.Result.Failure

    # --- Interactive prompt for target size ---
    go = Rhino.Input.Custom.GetOption()
    go.SetCommandPrompt("Grade footwear to new size")

    opt_target = Rhino.Input.Custom.OptionDouble(current_size)
    systems_list = list(_SIZE_SYSTEMS.keys())
    if size_system in systems_list:
        current_sys_idx = systems_list.index(size_system)
    else:
        current_sys_idx = 0

    go.AddOptionDouble("TargetSize", opt_target)
    go.AddOptionList("SizeSystem", systems_list, current_sys_idx)

    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            continue
        if res == Rhino.Input.GetResult.Nothing:
            break
        return Rhino.Commands.Result.Cancel

    target_size = opt_target.CurrentValue

    # Determine chosen size system
    chosen_sys_idx = current_sys_idx
    if go.OptionIndex() == 1:
        opt = go.Option()
        if opt is not None:
            chosen_sys_idx = opt.CurrentListOptionIndex
    if chosen_sys_idx < len(systems_list):
        size_system = systems_list[chosen_sys_idx]

    if abs(target_size - current_size) < 1e-6:
        Rhino.RhinoApp.WriteLine(
            "Target size is the same as current size. Nothing to do."
        )
        return Rhino.Commands.Result.Nothing

    Rhino.RhinoApp.WriteLine(
        "Grading from {0} {1} to {0} {2} ...".format(
            size_system, current_size, target_size
        )
    )

    origin = _get_orientation_origin(doc)
    scale_factor = _compute_scale_factor(current_size, target_size, size_system)

    Rhino.RhinoApp.WriteLine(
        "  Scale factor: {0:.6f}".format(scale_factor)
    )

    # Perform grading
    try:
        _grade_insole(doc, scale_factor, origin)
        _grade_outline(doc, scale_factor, origin)
        _grade_other_party_insole(doc, scale_factor, origin)
        _grade_geometries(doc, scale_factor, origin)
        _update_girth_measurements(doc, current_size, target_size)
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "Grading error: {0}\n{1}".format(ex, traceback.format_exc())
        )
        return Rhino.Commands.Result.Failure

    # Update document settings
    _set_doc_setting(doc, "last_size", target_size)
    _set_doc_setting(doc, "last_size_system", size_system)

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Grading complete: {0} {1}".format(size_system, target_size)
    )
    return Rhino.Commands.Result.Success
