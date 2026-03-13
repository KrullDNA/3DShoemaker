# -*- coding: utf-8 -*-
"""Feet in Focus Shoe Kit - ShowFIFShoeKitPanel Command

Opens the Feet in Focus Shoe Kit panel as a modeless form.
The panel provides categorised buttons for every major command,
curve-editing controls, clipping-plane management, layer visibility
toggles, and a status bar.
"""

import Rhino
import Eto.Forms as ef
import Eto.Drawing as ed


__commandname__ = "ShowFIFShoeKitPanel"

# Module-level reference to keep the form alive
_panel_form = None


def RunCommand(is_interactive):
    global _panel_form

    # If form already exists and is visible, just bring it to front
    if _panel_form is not None:
        try:
            if _panel_form.Visible:
                _panel_form.BringToFront()
                return 0
        except Exception:
            _panel_form = None

    try:
        from plugin.forms.podoCAD_panel import PodoCADPanel

        # Wrap the Panel in a modeless Form for display
        form = ef.Form()
        form.Title = "Feet in Focus Shoe Kit"
        form.ClientSize = ed.Size(280, 700)
        form.Minimizable = True
        form.Resizable = True

        panel = PodoCADPanel()
        scrollable = ef.Scrollable()
        scrollable.Content = panel
        scrollable.ExpandContentWidth = True
        form.Content = scrollable

        form.Show()
        _panel_form = form

        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Panel opened."
        )
    except Exception as ex:
        Rhino.RhinoApp.WriteLine(
            "[Feet in Focus Shoe Kit] Failed to open panel - {}".format(ex)
        )
        return 1

    return 0
