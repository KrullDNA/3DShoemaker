# -*- coding: utf-8 -*-
"""Export support parameters to file

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ExportSupportParameters"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ExportSupportParameters invoked.")
    Rhino.RhinoApp.WriteLine("  Export support parameters to file")
    return 0
