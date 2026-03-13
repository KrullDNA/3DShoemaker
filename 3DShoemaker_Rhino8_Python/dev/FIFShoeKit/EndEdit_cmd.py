# -*- coding: utf-8 -*-
"""Exit editing mode

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "EndEdit"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] EndEdit invoked.")
    Rhino.RhinoApp.WriteLine("  Exit editing mode")
    return 0
