# -*- coding: utf-8 -*-
"""Export last parameters to file

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ExportLastParameters"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ExportLastParameters invoked.")
    Rhino.RhinoApp.WriteLine("  Export last parameters to file")
    return 0
