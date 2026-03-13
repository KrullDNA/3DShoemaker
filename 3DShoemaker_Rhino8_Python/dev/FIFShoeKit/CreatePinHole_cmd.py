# -*- coding: utf-8 -*-
"""Create a pin hole

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreatePinHole"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreatePinHole invoked.")
    Rhino.RhinoApp.WriteLine("  Create a pin hole")
    return 0
