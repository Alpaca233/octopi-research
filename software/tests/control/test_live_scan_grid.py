"""Regression tests for the "live scan grid" (orange planned-coordinate overlay).

Bug: during an acquisition the stage steps through the planned FOVs. The live scan
grid is a *positioning preview* that re-centers on the current stage position
(`WellplateMultiPointWidget.update_live_coordinates` -> `set_live_scan_coordinates`).
It is wired to `MovementUpdater.position_after_move` only while the user is manually
navigating, and is supposed to be disconnected for the duration of an acquisition
(`HighContentScreeningGui.toggleAcquisitionStart`).

Two defects let the orange grid follow the stage during acquisition:
  1. `toggle_live_scan_grid(on=True)` connected the signal unconditionally. Because
     PyQt removes only one connection per `disconnect()`, any double-enable left a
     dangling connection that the single acquisition-start disconnect could not clear.
  2. `update_live_coordinates` did not check whether an acquisition was running, so
     a surviving connection would redraw the grid on every stage move.
"""

import control._def
import control.gui_hcs
import control.widgets
import control.microscope
import squid.abc
from qtpy.QtWidgets import QMessageBox


def _confirm_exit(parent, title, text, *args, **kwargs):
    if title == "Confirm Exit":
        return QMessageBox.Yes
    raise RuntimeError(f"Unexpected QMessageBox: {title} - {text}")


def _build_gui(qtbot, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", _confirm_exit)
    scope = control.microscope.Microscope.build_from_global_config(True)
    win = control.gui_hcs.HighContentScreeningGui(microscope=scope, is_simulation=True)
    qtbot.add_widget(win)
    return win


def test_live_scan_grid_does_not_follow_stage_during_acquisition(qtbot, monkeypatch):
    """If the live-grid slot fires while an acquisition is running, it must be a no-op."""
    win = _build_gui(qtbot, monkeypatch)
    wmp = win.wellplateMultiPointWidget

    # Put the widget into "Current Position" mode so the live grid is the active feature.
    wmp.checkbox_xy.setChecked(True)
    wmp.combobox_xy_mode.setCurrentText("Current Position")
    # Bypass the "is this the visible tab?" guard so we exercise the acquisition guard.
    monkeypatch.setattr(wmp, "tab_widget", None)

    # Spy on the grid redraw.
    redraws = []
    monkeypatch.setattr(wmp.scanCoordinates, "set_live_scan_coordinates", lambda *a, **k: redraws.append(a))

    pos1 = squid.abc.Pos(x_mm=10.0, y_mm=20.0, z_mm=0.0, theta_rad=None)
    pos2 = squid.abc.Pos(x_mm=30.0, y_mm=40.0, z_mm=0.0, theta_rad=None)

    # Sanity: while NOT acquiring, moving the stage should update the live grid.
    monkeypatch.setattr(win.multipointController, "acquisition_in_progress", lambda: False)
    wmp._last_update_time = 0
    wmp._last_x_mm = wmp._last_y_mm = None
    wmp.update_live_coordinates(pos1)
    assert len(redraws) == 1, "live grid should follow the stage during manual navigation"

    # Bug condition: while acquiring, a stage move must NOT redraw the planned grid.
    monkeypatch.setattr(win.multipointController, "acquisition_in_progress", lambda: True)
    redraws.clear()
    wmp._last_update_time = 0  # defeat the time throttle so only the acq guard can stop it
    wmp.update_live_coordinates(pos2)
    assert redraws == [], "live scan grid must not follow the stage during acquisition"


def test_toggle_live_scan_grid_is_idempotent(qtbot, monkeypatch):
    """A double-enable must not leave a dangling connection that survives a disable."""
    # Replace the slot with a pure counter so we measure live connections directly.
    calls = []
    monkeypatch.setattr(
        control.widgets.WellplateMultiPointWidget,
        "update_live_coordinates",
        lambda self, pos: calls.append(pos),
    )

    win = _build_gui(qtbot, monkeypatch)
    pos = squid.abc.Pos(x_mm=1.0, y_mm=2.0, z_mm=0.0, theta_rad=None)

    def live_connections():
        calls.clear()
        win.movement_updater.position_after_move.emit(pos)
        return len(calls)

    # Normalize to a known state, then simulate a redundant enable (the latent defect).
    win.toggle_live_scan_grid(on=False)
    win.toggle_live_scan_grid(on=True)
    win.toggle_live_scan_grid(on=True)  # redundant enable
    assert live_connections() == 1, "redundant enable must not create duplicate connections"

    # A single disable (what acquisition-start does) must fully disconnect.
    win.toggle_live_scan_grid(on=False)
    assert live_connections() == 0, "live grid still connected after disable (dangling connection)"
