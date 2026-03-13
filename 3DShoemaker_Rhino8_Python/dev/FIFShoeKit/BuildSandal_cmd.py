# -*- coding: utf-8 -*-
"""Create a sandal from a last

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "BuildSandal"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] BuildSandal invoked.")
    Rhino.RhinoApp.WriteLine("  Create a sandal from a last")
    return 0
