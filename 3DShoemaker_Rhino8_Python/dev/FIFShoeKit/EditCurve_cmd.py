# -*- coding: utf-8 -*-
"""Enter curve editing mode

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "EditCurve"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] EditCurve invoked.")
    Rhino.RhinoApp.WriteLine("  Enter curve editing mode")
    return 0
