# -*- coding: utf-8 -*-
"""Change component parameterization

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ChangeComponentParameterization"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ChangeComponentParameterization invoked.")
    Rhino.RhinoApp.WriteLine("  Change component parameterization")
    return 0
