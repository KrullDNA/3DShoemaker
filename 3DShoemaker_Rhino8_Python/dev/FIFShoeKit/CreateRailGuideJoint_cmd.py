# -*- coding: utf-8 -*-
"""Create a rail guide joint

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateRailGuideJoint"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateRailGuideJoint invoked.")
    Rhino.RhinoApp.WriteLine("  Create a rail guide joint")
    return 0
