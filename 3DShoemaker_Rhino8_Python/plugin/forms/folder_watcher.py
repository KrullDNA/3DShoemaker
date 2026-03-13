"""
folder_watcher.py - Folder watching dialog for Feet in Focus Shoe Kit.

Monitors a designated folder for new scan files and automatically
imports them into the active document when they appear.
"""

import os
import time
import threading
from typing import List, Optional, Set

import Rhino
import Rhino.UI
import System

import Eto.Forms as forms
import Eto.Drawing as drawing


# File extensions to watch for
_WATCH_EXTENSIONS = {".stl", ".obj", ".ply", ".3ds", ".fbx", ".xyz", ".csv"}


class FolderWatcher(forms.Form):
    """
    Non-modal form that watches a folder for new scan files and
    auto-imports them into the Rhino document.

    Runs a background thread that polls the folder at a configurable
    interval.  New files are logged in the dialog and optionally
    imported automatically.
    """

    def __init__(self):
        super().__init__()

        self.Title = "Feet in Focus Shoe Kit - Folder Watcher"
        self.ClientSize = drawing.Size(520, 420)
        self.Padding = drawing.Padding(10)
        self.Resizable = True
        self.Minimizable = True

        # State
        self.watch_folder: str = ""
        self.auto_import: bool = True
        self.poll_interval: float = 2.0  # seconds
        self._watching: bool = False
        self._known_files: Set[str] = set()
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._build_ui()

        # Wire the Shown event
        self.Shown += self.agent_Shown

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = forms.DynamicLayout()
        layout.DefaultSpacing = drawing.Size(5, 5)
        layout.Padding = drawing.Padding(10)

        # -- Folder selection ----------------------------------------------
        folder_group = forms.GroupBox(Text="Watch Folder")
        folder_layout = forms.DynamicLayout()
        folder_layout.DefaultSpacing = drawing.Size(5, 5)
        folder_layout.Padding = drawing.Padding(8)

        self._txt_folder = forms.TextBox(
            ReadOnly=True, PlaceholderText="Select a folder to watch...")
        btn_browse = forms.Button(Text="Browse...")
        btn_browse.Click += self._on_browse

        folder_layout.AddRow(self._txt_folder, btn_browse)

        folder_group.Content = folder_layout
        layout.AddRow(folder_group)

        layout.AddSpace()

        # -- Settings ------------------------------------------------------
        settings_group = forms.GroupBox(Text="Settings")
        settings_layout = forms.DynamicLayout()
        settings_layout.DefaultSpacing = drawing.Size(5, 5)
        settings_layout.Padding = drawing.Padding(8)

        self._chk_auto_import = forms.CheckBox(
            Text="Auto-import new files")
        self._chk_auto_import.Checked = self.auto_import
        settings_layout.AddRow(self._chk_auto_import)

        settings_layout.AddRow(forms.Label(Text="Poll Interval (seconds):"))
        self._num_interval = forms.NumericStepper()
        self._num_interval.MinValue = 0.5
        self._num_interval.MaxValue = 60.0
        self._num_interval.DecimalPlaces = 1
        self._num_interval.Increment = 0.5
        self._num_interval.Value = self.poll_interval
        settings_layout.AddRow(self._num_interval)

        settings_group.Content = settings_layout
        layout.AddRow(settings_group)

        layout.AddSpace()

        # -- Control buttons -----------------------------------------------
        ctrl_row = forms.DynamicLayout()
        ctrl_row.DefaultSpacing = drawing.Size(5, 5)

        self._btn_start = forms.Button(Text="Start Watching")
        self._btn_start.Click += self._on_start
        self._btn_stop = forms.Button(Text="Stop Watching")
        self._btn_stop.Click += self._on_stop
        self._btn_stop.Enabled = False

        ctrl_row.AddRow(self._btn_start, self._btn_stop)
        layout.AddRow(ctrl_row)

        layout.AddSpace()

        # -- Log area ------------------------------------------------------
        log_group = forms.GroupBox(Text="Activity Log")
        log_layout = forms.DynamicLayout()
        log_layout.DefaultSpacing = drawing.Size(5, 5)
        log_layout.Padding = drawing.Padding(8)

        self._txt_log = forms.TextArea()
        self._txt_log.ReadOnly = True
        self._txt_log.Wrap = True
        self._txt_log.Font = drawing.Font(drawing.SystemFont.Default, 9)
        log_layout.AddRow(self._txt_log)

        btn_clear = forms.Button(Text="Clear Log")
        btn_clear.Click += self._on_clear_log
        log_layout.AddRow(None, btn_clear)

        log_group.Content = log_layout
        layout.AddRow(log_group)

        layout.AddSpace()

        # -- Close button --------------------------------------------------
        btn_close = forms.Button(Text="Close")
        btn_close.Click += self._on_close

        btn_layout = forms.DynamicLayout()
        btn_layout.AddRow(None, btn_close)
        layout.AddRow(btn_layout)

        self.Content = layout

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def logrename(self, message: str):
        """
        Append a timestamped message to the activity log.

        Thread-safe: marshals UI updates to the main thread.
        """
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}\n"

        def _update():
            self._txt_log.Append(line, True)

        try:
            forms.Application.Instance.Invoke(_update)
        except Exception:
            # Fallback if invoke fails (dialog already closed)
            pass

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def agent_Shown(self, sender, e):
        """
        Event handler for when the dialog becomes visible.

        Initialises the known-files set from the current folder
        contents so only genuinely new files trigger imports.
        """
        if self.watch_folder and os.path.isdir(self.watch_folder):
            self._snapshot_folder()
            self.logrename(
                f"Watching folder initialised: {self.watch_folder} "
                f"({len(self._known_files)} existing files)"
            )

    # ------------------------------------------------------------------
    # Folder management
    # ------------------------------------------------------------------

    def _on_browse(self, sender, e):
        dlg = forms.SelectFolderDialog()
        dlg.Title = "Select Folder to Watch"
        result = dlg.ShowDialog(self)
        if result == forms.DialogResult.Ok:
            self.watch_folder = dlg.Directory
            self._txt_folder.Text = self.watch_folder
            self._snapshot_folder()
            self.logrename(f"Folder selected: {self.watch_folder}")

    def _snapshot_folder(self):
        """Record all current files in the watch folder."""
        self._known_files.clear()
        if not self.watch_folder or not os.path.isdir(self.watch_folder):
            return
        for fname in os.listdir(self.watch_folder):
            ext = os.path.splitext(fname)[1].lower()
            if ext in _WATCH_EXTENSIONS:
                full_path = os.path.join(self.watch_folder, fname)
                self._known_files.add(full_path)

    # ------------------------------------------------------------------
    # Start / stop watching
    # ------------------------------------------------------------------

    def _on_start(self, sender, e):
        if not self.watch_folder or not os.path.isdir(self.watch_folder):
            self.logrename("Error: No valid folder selected.")
            return

        self.auto_import = self._chk_auto_import.Checked == True
        self.poll_interval = self._num_interval.Value

        self._snapshot_folder()
        self._stop_event.clear()
        self._watching = True

        self._watch_thread = threading.Thread(
            target=self._watch_loop, daemon=True)
        self._watch_thread.start()

        self._btn_start.Enabled = False
        self._btn_stop.Enabled = True
        self.logrename("Started watching.")

    def _on_stop(self, sender, e):
        self._stop_watching()

    def _stop_watching(self):
        """Stop the background watcher thread."""
        self._stop_event.set()
        self._watching = False

        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=5.0)
        self._watch_thread = None

        self._btn_start.Enabled = True
        self._btn_stop.Enabled = False
        self.logrename("Stopped watching.")

    # ------------------------------------------------------------------
    # Background watch loop
    # ------------------------------------------------------------------

    def _watch_loop(self):
        """
        Background thread that polls the watch folder for new files.
        """
        while not self._stop_event.is_set():
            try:
                self._check_for_new_files()
            except Exception as ex:
                self.logrename(f"Watch error: {ex}")

            self._stop_event.wait(self.poll_interval)

    def _check_for_new_files(self):
        """Scan the folder and handle any new files."""
        if not self.watch_folder or not os.path.isdir(self.watch_folder):
            return

        current_files: Set[str] = set()
        for fname in os.listdir(self.watch_folder):
            ext = os.path.splitext(fname)[1].lower()
            if ext in _WATCH_EXTENSIONS:
                full_path = os.path.join(self.watch_folder, fname)
                current_files.add(full_path)

        new_files = current_files - self._known_files
        for fpath in sorted(new_files):
            fname = os.path.basename(fpath)
            self.logrename(f"New file detected: {fname}")

            if self.auto_import:
                self._auto_import_file(fpath)

        self._known_files = current_files

    def _auto_import_file(self, file_path: str):
        """
        Import a scan file into Rhino on the main thread.
        """
        def _do_import():
            try:
                cmd = f'_-Import "{file_path}" _Enter'
                Rhino.RhinoApp.RunScript(cmd, False)
                self.logrename(f"Imported: {os.path.basename(file_path)}")
            except Exception as ex:
                self.logrename(f"Import failed for {os.path.basename(file_path)}: {ex}")

        try:
            forms.Application.Instance.Invoke(_do_import)
        except Exception as ex:
            self.logrename(f"Could not schedule import: {ex}")

    # ------------------------------------------------------------------
    # Misc handlers
    # ------------------------------------------------------------------

    def _on_clear_log(self, sender, e):
        self._txt_log.Text = ""

    def _on_close(self, sender, e):
        if self._watching:
            self._stop_watching()
        self.Close()

    def OnUnLoad(self, e):
        """Ensure watcher is stopped when the form is unloaded."""
        if self._watching:
            self._stop_watching()
        super().OnUnLoad(e)
