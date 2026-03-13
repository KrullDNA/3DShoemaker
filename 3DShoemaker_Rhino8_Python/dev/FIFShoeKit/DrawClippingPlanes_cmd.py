# -*- coding: utf-8 -*-
"""Draw clipping planes on the model

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "DrawClippingPlanes"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] DrawClippingPlanes invoked.")
    Rhino.RhinoApp.WriteLine("  Draw clipping planes on the model")
    return 0
