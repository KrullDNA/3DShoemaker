# -*- coding: utf-8 -*-
"""Add a groove to the sandal

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AddSandalGroove"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AddSandalGroove invoked.")
    Rhino.RhinoApp.WriteLine("  Add a groove to the sandal")
    return 0
