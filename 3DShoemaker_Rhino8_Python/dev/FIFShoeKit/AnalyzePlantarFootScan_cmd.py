# -*- coding: utf-8 -*-
"""Analyze a plantar foot scan

Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino

__commandname__ = "AnalyzePlantarFootScan"


def RunCommand(is_interactive):
    Rhino.RhinoApp.WriteLine("[Feet in Focus Shoe Kit] AnalyzePlantarFootScan invoked.")
    Rhino.RhinoApp.WriteLine("  Analyze a plantar foot scan")
    return 0
