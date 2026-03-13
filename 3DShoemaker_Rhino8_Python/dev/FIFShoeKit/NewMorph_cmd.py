# -*- coding: utf-8 -*-
"""Create a new morph operation

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "NewMorph"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] NewMorph invoked.")
    Rhino.RhinoApp.WriteLine("  Create a new morph operation")
    return 0
