# -*- coding: utf-8 -*-
"""Batch prepare multiple orthotics

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "PrintPrepOrthotics"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] PrintPrepOrthotics invoked.")
    Rhino.RhinoApp.WriteLine("  Batch prepare multiple orthotics")
    return 0
