# -*- coding: utf-8 -*-
"""Generate an insole from the last

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateInsole"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateInsole invoked.")
    Rhino.RhinoApp.WriteLine("  Generate an insole from the last")
    return 0
