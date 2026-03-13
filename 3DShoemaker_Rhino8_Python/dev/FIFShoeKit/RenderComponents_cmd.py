# -*- coding: utf-8 -*-
"""Render component views

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "RenderComponents"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] RenderComponents invoked.")
    Rhino.RhinoApp.WriteLine("  Render component views")
    return 0
