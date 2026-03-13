# -*- coding: utf-8 -*-
"""Apply twist deformation to orthotic

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "TwistOrthotic"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] TwistOrthotic invoked.")
    Rhino.RhinoApp.WriteLine("  Apply twist deformation to orthotic")
    return 0
