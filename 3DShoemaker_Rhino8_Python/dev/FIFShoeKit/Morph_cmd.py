# -*- coding: utf-8 -*-
"""Morph the last shape interactively

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "Morph"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] Morph invoked.")
    Rhino.RhinoApp.WriteLine("  Morph the last shape interactively")
    return 0
