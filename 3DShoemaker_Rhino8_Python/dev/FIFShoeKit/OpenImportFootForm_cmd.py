# -*- coding: utf-8 -*-
"""Open the foot import dialog

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "OpenImportFootForm"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] OpenImportFootForm invoked.")
    Rhino.RhinoApp.WriteLine("  Open the foot import dialog")
    return 0
