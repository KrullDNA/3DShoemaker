# -*- coding: utf-8 -*-
"""Name all objects in the document

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "NameObjectsInDoc"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] NameObjectsInDoc invoked.")
    Rhino.RhinoApp.WriteLine("  Name all objects in the document")
    return 0
