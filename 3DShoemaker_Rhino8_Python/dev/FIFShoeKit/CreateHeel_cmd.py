# -*- coding: utf-8 -*-
"""Create the heel

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateHeel"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateHeel invoked.")
    Rhino.RhinoApp.WriteLine("  Create the heel")
    return 0
