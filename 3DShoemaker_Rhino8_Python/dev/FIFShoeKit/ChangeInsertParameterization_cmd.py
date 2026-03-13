# -*- coding: utf-8 -*-
"""Change insert parameterization

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ChangeInsertParameterization"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ChangeInsertParameterization invoked.")
    Rhino.RhinoApp.WriteLine("  Change insert parameterization")
    return 0
