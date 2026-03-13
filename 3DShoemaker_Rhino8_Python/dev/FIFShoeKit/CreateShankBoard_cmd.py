# -*- coding: utf-8 -*-
"""Create the shank board

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateShankBoard"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateShankBoard invoked.")
    Rhino.RhinoApp.WriteLine("  Create the shank board")
    return 0
