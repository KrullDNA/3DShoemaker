# -*- coding: utf-8 -*-
"""Customize fit parameters

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AdjustFitCustomization"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AdjustFitCustomization invoked.")
    Rhino.RhinoApp.WriteLine("  Customize fit parameters")
    return 0
