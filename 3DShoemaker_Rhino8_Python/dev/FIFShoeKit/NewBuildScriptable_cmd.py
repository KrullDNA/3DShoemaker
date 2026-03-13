# -*- coding: utf-8 -*-
"""Create a new build with scriptable parameters

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "NewBuildScriptable"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] NewBuildScriptable invoked.")
    Rhino.RhinoApp.WriteLine("  Create a new build with scriptable parameters")
    return 0
