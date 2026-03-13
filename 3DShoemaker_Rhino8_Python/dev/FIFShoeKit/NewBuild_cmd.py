# -*- coding: utf-8 -*-
"""Create a new shoe last build

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "NewBuild"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] NewBuild invoked.")
    Rhino.RhinoApp.WriteLine("  Create a new shoe last build")
    return 0
