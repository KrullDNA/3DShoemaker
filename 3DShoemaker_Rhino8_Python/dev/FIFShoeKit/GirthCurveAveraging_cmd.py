# -*- coding: utf-8 -*-
"""Average girth curves

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "GirthCurveAveraging"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] GirthCurveAveraging invoked.")
    Rhino.RhinoApp.WriteLine("  Average girth curves")
    return 0
