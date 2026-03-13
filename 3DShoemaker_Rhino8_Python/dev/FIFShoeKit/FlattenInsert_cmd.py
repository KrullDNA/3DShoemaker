# -*- coding: utf-8 -*-
"""Flatten insert to 2D

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "FlattenInsert"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] FlattenInsert invoked.")
    Rhino.RhinoApp.WriteLine("  Flatten insert to 2D")
    return 0
