# -*- coding: utf-8 -*-
"""Change the active clipping plane

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ChangeClippingPlane"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ChangeClippingPlane invoked.")
    Rhino.RhinoApp.WriteLine("  Change the active clipping plane")
    return 0
