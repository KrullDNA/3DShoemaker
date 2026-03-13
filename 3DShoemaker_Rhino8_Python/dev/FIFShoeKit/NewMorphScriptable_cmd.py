# -*- coding: utf-8 -*-
"""Create a morph with scriptable parameters

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "NewMorphScriptable"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] NewMorphScriptable invoked.")
    Rhino.RhinoApp.WriteLine("  Create a morph with scriptable parameters")
    return 0
