# -*- coding: utf-8 -*-
"""Modify a single design parameter

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ChangeParameter"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ChangeParameter invoked.")
    Rhino.RhinoApp.WriteLine("  Modify a single design parameter")
    return 0
