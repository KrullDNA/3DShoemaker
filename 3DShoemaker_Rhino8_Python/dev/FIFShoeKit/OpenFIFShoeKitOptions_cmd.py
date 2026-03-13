# -*- coding: utf-8 -*-
"""Open the plugin options dialog

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "OpenFIFShoeKitOptions"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] OpenFIFShoeKitOptions invoked.")
    Rhino.RhinoApp.WriteLine("  Open the plugin options dialog")
    return 0
