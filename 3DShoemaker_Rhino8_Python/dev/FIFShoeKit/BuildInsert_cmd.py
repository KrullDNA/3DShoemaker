# -*- coding: utf-8 -*-
"""Create a removable insert

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "BuildInsert"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] BuildInsert invoked.")
    Rhino.RhinoApp.WriteLine("  Create a removable insert")
    return 0
