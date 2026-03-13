# -*- coding: utf-8 -*-
"""Measure the current last

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "MeasureLast"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] MeasureLast invoked.")
    Rhino.RhinoApp.WriteLine("  Measure the current last")
    return 0
