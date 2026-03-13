# -*- coding: utf-8 -*-
"""Export measurement equations

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ExportMeasurementEquations"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ExportMeasurementEquations invoked.")
    Rhino.RhinoApp.WriteLine("  Export measurement equations")
    return 0
