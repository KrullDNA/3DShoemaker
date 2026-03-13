# -*- coding: utf-8 -*-
"""Create vacuum form geometry

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "VacuumForm"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] VacuumForm invoked.")
    Rhino.RhinoApp.WriteLine("  Create vacuum form geometry")
    return 0
