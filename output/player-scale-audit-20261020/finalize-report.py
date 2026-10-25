"""Record completed cleanup without changing the shared editor's newer selection."""

import datetime
import json
import math
from pathlib import Path


root = Path(__file__).resolve().parent


def read(name):
    return json.loads((root / name).read_text(encoding="utf-8-sig"))


def write(name, data):
    (root / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


receipt = read("close-audit-tab/close_scene.json")["structuredContent"]
observed = read("editor-restoration.json")
temporary_settings = read("live-fov/restoration.json")
assert receipt["ActivePath"] == "scenes/menu.scene" and receipt["Open"] == ["menu"]
assert all(temporary_settings[key] for key in ("FovRestored", "AdsRestored", "GodModeRestored"))
assert observed["Playing"] is False
assert "scenes/maps/boxyard/boxyard.scene" not in observed["OpenDocuments"]
assert observed["FieldOfView"] == 85 and observed["IndependentAdsFov"] is False

cleanup = {
    "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "audit_play_stopped": True,
    "original_menu_selection_restored_at_cleanup": True,
    "audit_boxyard_edit_tab_closed": True,
    "original_restore_receipt": "close-audit-tab/close_scene.json",
    "latest_observed_editor_state": observed,
    "later_external_belltower_selection_preserved": True,
    "note": (
        "Cleanup restored the original menu and closed the audit's Boxyard document. "
        "Belltower was opened subsequently by another editor user or chat. "
        "The archived strict menu-only verification therefore returned Restored=false; "
        "this is a later selection change, not unfinished audit cleanup. "
        "No action was taken to overwrite that selection."
    ),
    "fov_ads_and_god_mode_restoration": temporary_settings,
}

pending = read("restore-pending.json")
pending["restore_required"] = False
pending["cleanup"] = cleanup
write("restore-pending.json", pending)

report = read("report.json")
report["editor_cleanup"] = cleanup
height = 1.7513001
distance = 10
report["illustrative_display_size_comparison"] = {
    "reference_target_height_metres": height,
    "reference_distance_metres": distance,
    "measured_editor_width_pixels": 1138,
    "target_pixels_at_editor_width_and_60_degrees": height / distance / (2 * math.tan(math.radians(60 / 2))) * 1138,
    "hypothetical_fullscreen_width_pixels": 1920,
    "target_pixels_at_hypothetical_width_and_85_degrees": height / distance / (2 * math.tan(math.radians(85 / 2))) * 1920,
    "limit": (
        "The 1920-pixel fullscreen example is hypothetical, not a measured CoD setup. "
        "This compares displayed widths on the same pixel-density screen. Internal render "
        "resolution or upscaling alone does not change an object's displayed size."
    ),
}
write("report.json", report)
write("cleanup-complete.json", cleanup)
print(json.dumps({"restore_required": False, "audit_cleanup_complete": True,
                  "later_editor_selection_preserved": observed["Active"],
                  "report": str(root / "report.json")}))
