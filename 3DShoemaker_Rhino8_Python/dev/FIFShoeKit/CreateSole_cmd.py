# -*- coding: utf-8 -*-
"""Create the outsole

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateSole"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateSole invoked.")
    Rhino.RhinoApp.WriteLine("  Create the outsole")
    return 0
