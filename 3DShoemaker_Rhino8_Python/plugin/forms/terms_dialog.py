"""
terms_dialog.py - Terms and Conditions acceptance dialog for Feet in Focus Shoe Kit.

Displays the license terms from Terms.txt and requires the user to
accept before using the plugin.
"""

import os
from typing import Optional

import Rhino
import Rhino.UI
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


class TermsDialog(forms.Dialog[bool]):
    """
    Modal dialog that displays the Feet in Focus Shoe Kit license terms and
    requires explicit acceptance.

    Use the static ``ShowAndAccept`` method for convenient one-call
    usage that returns True when the user accepts.
    """

    def __init__(self, terms_text: str = ""):
        super().__init__()

        self.Title = "Feet in Focus Shoe Kit - Terms and Conditions"
        self.ClientSize = drawing.Size(620, 500)
        self.Padding = drawing.Padding(10)
        self.Resizable = True
        self.Minimizable = False
        self.Maximizable = False

        self._terms_text = terms_text or self._load_terms_text()
        self._accepted = False

        self._build_ui()

    # ------------------------------------------------------------------
    # Terms text loader
    # ------------------------------------------------------------------

    @staticmethod
    def _load_terms_text() -> str:
        """
        Load the terms text from the Terms.txt file shipped with the
        plugin.  Falls back to a placeholder when the file is missing.
        """
        # Walk up from this file to find Terms.txt at the plugin root
        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base_dir, "..", "..", "Terms.txt"),
            os.path.join(base_dir, "..", "Terms.txt"),
            os.path.join(base_dir, "Terms.txt"),
        ]

        for path in candidates:
            norm = os.path.normpath(path)
            if os.path.isfile(norm):
                try:
                    with open(norm, "r", encoding="utf-8") as fh:
                        return fh.read()
                except Exception:
                    pass

        return (
            "Feet in Focus Shoe Kit - Terms and Conditions\n"
            "===================================\n\n"
            "The full terms and conditions document could not be found.\n"
            "Please visit https://ShoeLastMaker.com for the complete terms.\n\n"
            "By clicking 'Accept' you agree to be bound by the terms and\n"
            "conditions of the Feet in Focus Shoe Kit software license."
        )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # Header
        header = forms.Label(
            Text="Please read and accept the Terms and Conditions:",
            Font=drawing.Font(drawing.SystemFont.Bold, 11),
        )
        layout.AddRow(header)

        layout.AddSpace()

        # Terms text area (read-only, scrollable)
        self._txt_terms = forms.TextArea()
        self._txt_terms.ReadOnly = True
        self._txt_terms.Wrap = True
        self._txt_terms.Text = self._terms_text
        self._txt_terms.Font = drawing.Font(drawing.SystemFont.Default, 9)
        layout.AddRow(self._txt_terms)

        layout.AddSpace()

        # Acceptance checkbox
        self._chk_accept = forms.CheckBox(
            Text="I have read and agree to the Terms and Conditions"
        )
        self._chk_accept.CheckedChanged += self._on_check_changed
        layout.AddRow(self._chk_accept)

        layout.AddSpace()

        # Buttons
        self._btn_accept = forms.Button(Text="Accept")
        self._btn_accept.Click += self._on_accept
        self._btn_accept.Enabled = False  # Enabled only when checkbox is ticked

        btn_decline = forms.Button(Text="Decline")
        btn_decline.Click += self._on_decline

        self.AbortButton = btn_decline

        btn_layout = forms.DynamicLayout()
        btn_layout.AddRow(None, btn_decline, self._btn_accept)
        layout.AddRow(btn_layout)

        self.Content = layout

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_check_changed(self, sender, e):
        self._btn_accept.Enabled = self._chk_accept.Checked == True

    def _on_accept(self, sender, e):
        self._accepted = True
        self.Close(True)

    def _on_decline(self, sender, e):
        self._accepted = False
        self.Close(False)

    # ------------------------------------------------------------------
    # Public result
    # ------------------------------------------------------------------

    @property
    def accepted(self) -> bool:
        """True when the user clicked Accept with the checkbox ticked."""
        return self._accepted

    # ------------------------------------------------------------------
    # Static convenience method
    # ------------------------------------------------------------------

    @staticmethod
    def ShowAndAccept(owner=None) -> bool:
        """
        Show the terms dialog modally and return True if accepted.

        Parameters
        ----------
        owner : optional
            Parent window.  Defaults to the Rhino main window.

        Returns
        -------
        bool
            True when the user accepted the terms.
        """
        dlg = TermsDialog()
        parent = owner or Rhino.UI.RhinoEtoApp.MainWindow
        dlg.ShowModal(parent)
        return dlg.accepted
