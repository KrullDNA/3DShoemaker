# -*- coding: utf-8 -*-
"""Modify last parameterization settings

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ChangeLastParameterization"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ChangeLastParameterization invoked.")
    Rhino.RhinoApp.WriteLine("  Modify last parameterization settings")
    return 0
