# -*- coding: utf-8 -*-
"""Adjust material properties for a component.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "AdjustMaterial"


def _get_settings():
    """Get current document settings from sticky."""
    ds = sc.sticky.get("FIF_DocumentSettings", None)
    if ds is None:
        ds = {}
        sc.sticky["FIF_DocumentSettings"] = ds
    return ds


def RunCommand(is_interactive):
    ds = _get_settings()

    components = ["Insert", "Bottom", "Last"]
    materials = [
        "EVA", "Cork", "Leather", "Rubber", "Polypropylene",
        "Carbon", "Nylon", "TPU", "Silicone", "Polyester",
    ]

    go = ric.GetOption()
    go.SetCommandPrompt("Adjust material")
    go.AddOptionList("Component", components, 0)
    go.AddOptionList("Material", materials, 0)
    opt_density = ric.OptionDouble(1.0, 0.01, 20.0)
    opt_hardness = ric.OptionDouble(40.0, 0.0, 100.0)
    go.AddOptionDouble("Density", opt_density)
    go.AddOptionDouble("ShoreAHardness", opt_hardness)

    comp_idx = 0
    mat_idx = 0
    while True:
        res = go.Get()
        if res == Rhino.Input.GetResult.Option:
            option = go.Option()
            if option.EnglishName == "Component":
                comp_idx = option.CurrentListOptionIndex
            elif option.EnglishName == "Material":
                mat_idx = option.CurrentListOptionIndex
            continue
        break

    component = components[comp_idx] if comp_idx < len(components) else "Insert"
    material = materials[mat_idx] if mat_idx < len(materials) else "EVA"

    # Store in settings
    key_prefix = component.lower()
    ds["{0}_material".format(key_prefix)] = material
    ds["{0}_material_density".format(key_prefix)] = opt_density.CurrentValue
    ds["{0}_material_hardness".format(key_prefix)] = opt_hardness.CurrentValue
    sc.sticky["FIF_DocumentSettings"] = ds

    Rhino.RhinoApp.WriteLine(
        "{0} material set to {1} (density={2:.2f}, hardness={3:.0f} Shore A).".format(
            component, material,
            opt_density.CurrentValue, opt_hardness.CurrentValue
        )
    )
    return rc.Result.Success
