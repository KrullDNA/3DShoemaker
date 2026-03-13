# -*- coding: utf-8 -*-
"""Add a thong slot

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AddThongSlot"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AddThongSlot invoked.")
    Rhino.RhinoApp.WriteLine("  Add a thong slot")
    return 0
