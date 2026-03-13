# -*- coding: utf-8 -*-
"""Opens the Feet in Focus Shoe Kit options/settings dialog.

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import scriptcontext as sc

__commandname__ = "OpenFIFShoeKitOptions"


# Default document settings with their defaults
_OPTION_DEFAULTS = {
    "units": "Millimeters",
    "absolute_tolerance": 0.01,
    "show_construction_lines": True,
    "show_measurements": True,
    "display_mode": "Shaded",
    "export_format": "STL",
    "export_stl_tolerance": 0.05,
    "export_stl_angle_tolerance": 5.0,
}


def _get_settings():
    """Get current settings from sticky, initializing if needed."""
    ds = sc.sticky.get("FIF_DocumentSettings", None)
    if ds is None:
        ds = dict(_OPTION_DEFAULTS)
        sc.sticky["FIF_DocumentSettings"] = ds
    return ds


def RunCommand(is_interactive):
    try:
        ds = _get_settings()

        go = ric.GetOption()
        go.SetCommandPrompt("Feet in Focus Shoe Kit Options (Enter when done)")
        go.AcceptNothing(True)

        opt_show_cl = ric.OptionToggle(
            ds.get("show_construction_lines", True), "Hide", "Show"
        )
        opt_show_meas = ric.OptionToggle(
            ds.get("show_measurements", True), "Hide", "Show"
        )
        opt_tol = ric.OptionDouble(
            ds.get("absolute_tolerance", 0.01), 0.001, 1.0
        )
        opt_stl_tol = ric.OptionDouble(
            ds.get("export_stl_tolerance", 0.05), 0.001, 1.0
        )

        display_modes = ["Shaded", "Rendered", "Wireframe", "Ghosted"]
        current_dm = ds.get("display_mode", "Shaded")
        dm_idx = display_modes.index(current_dm) if current_dm in display_modes else 0

        export_formats = ["STL", "OBJ", "3MF", "STEP"]
        current_ef = ds.get("export_format", "STL")
        ef_idx = export_formats.index(current_ef) if current_ef in export_formats else 0

        go.AddOptionToggle("ShowConstructionLines", opt_show_cl)
        go.AddOptionToggle("ShowMeasurements", opt_show_meas)
        go.AddOptionDouble("Tolerance", opt_tol)
        go.AddOptionDouble("STLTolerance", opt_stl_tol)
        go.AddOptionList("DisplayMode", display_modes, dm_idx)
        go.AddOptionList("ExportFormat", export_formats, ef_idx)

        while True:
            res = go.Get()
            if res == Rhino.Input.GetResult.Option:
                option = go.Option()
                if option.EnglishName == "DisplayMode":
                    dm_idx = option.CurrentListOptionIndex
                elif option.EnglishName == "ExportFormat":
                    ef_idx = option.CurrentListOptionIndex
                continue
            break

        # Save settings
        ds["show_construction_lines"] = opt_show_cl.CurrentValue
        ds["show_measurements"] = opt_show_meas.CurrentValue
        ds["absolute_tolerance"] = opt_tol.CurrentValue
        ds["export_stl_tolerance"] = opt_stl_tol.CurrentValue
        ds["display_mode"] = display_modes[dm_idx]
        ds["export_format"] = export_formats[ef_idx]
        sc.sticky["FIF_DocumentSettings"] = ds

        Rhino.RhinoApp.WriteLine("Options saved.")
        return rc.Result.Success

    except Exception as e:
        Rhino.RhinoApp.WriteLine("Error opening options: {0}".format(e))
        return rc.Result.Failure
