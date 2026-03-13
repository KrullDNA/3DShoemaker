# -*- coding: utf-8 -*-
"""Create a full footwear mockup

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "CreateMockup"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] CreateMockup invoked.")
    Rhino.RhinoApp.WriteLine("  Create a full footwear mockup")
    return 0
