# -*- coding: utf-8 -*-
"""Change object status/state.

Toggles the design status of selected objects (e.g., Draft, Review,
Approved, Locked) and stores it in user text.
Feet in Focus Shoe Kit command.
IronPython 2 compatible - no Python 3 syntax.
"""

import Rhino
import Rhino.Commands as rc
import Rhino.Input.Custom as ric
import Rhino.DocObjects as rdo
import scriptcontext as sc

__commandname__ = "ChangeStatus"


def RunCommand(is_interactive):
    doc = sc.doc

    # Select objects
    go = ric.GetObject()
    go.SetCommandPrompt("Select objects to change status")
    go.EnablePreSelect(True, True)
    go.GetMultiple(1, 0)
    if go.CommandResult() != rc.Result.Success:
        return go.CommandResult()

    count = go.ObjectCount
    if count == 0:
        return rc.Result.Cancel

    statuses = ["Draft", "Review", "Approved", "Locked", "Archived"]

    go_stat = ric.GetOption()
    go_stat.SetCommandPrompt("Select new status")
    go_stat.AddOptionList("Status", statuses, 0)

    status_idx = 0
    while True:
        res = go_stat.Get()
        if res == Rhino.Input.GetResult.Option:
            status_idx = go_stat.Option().CurrentListOptionIndex
            continue
        break

    new_status = statuses[status_idx] if status_idx < len(statuses) else "Draft"

    # Apply status to selected objects
    changed = 0
    for i in range(count):
        obj = go.Object(i).Object()
        if obj is None:
            continue

        attrs = obj.Attributes.Duplicate()
        # Store status in user text
        attrs.SetUserString("FIFShoeKit_Status", new_status)

        # Visual feedback: lock objects with "Locked" status
        if new_status == "Locked":
            attrs.Mode = rdo.ObjectMode.Locked
        elif new_status == "Archived":
            attrs.Visible = False
        else:
            attrs.Mode = rdo.ObjectMode.Normal
            attrs.Visible = True

        doc.Objects.ModifyAttributes(obj, attrs, True)
        changed += 1

    doc.Views.Redraw()
    Rhino.RhinoApp.WriteLine(
        "Status changed to '{0}' for {1} object(s).".format(new_status, changed)
    )
    return rc.Result.Success
