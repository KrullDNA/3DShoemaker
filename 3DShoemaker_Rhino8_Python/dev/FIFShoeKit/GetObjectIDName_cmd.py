# -*- coding: utf-8 -*-
"""Get the ID and name of an object

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "GetObjectIDName"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] GetObjectIDName invoked.")
    Rhino.RhinoApp.WriteLine("  Get the ID and name of an object")
    return 0
