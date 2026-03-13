# -*- coding: utf-8 -*-
"""Create individual heel parts

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateHeelParts"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateHeelParts invoked.")
    Rhino.RhinoApp.WriteLine("  Create individual heel parts")
    return 0
