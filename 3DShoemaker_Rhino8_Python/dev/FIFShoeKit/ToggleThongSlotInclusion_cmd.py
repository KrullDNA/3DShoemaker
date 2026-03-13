# -*- coding: utf-8 -*-
"""Toggle thong slot on/off

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "ToggleThongSlotInclusion"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] ToggleThongSlotInclusion invoked.")
    Rhino.RhinoApp.WriteLine("  Toggle thong slot on/off")
    return 0
