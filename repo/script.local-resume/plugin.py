import xbmc
import xbmcgui
import xbmcaddon
import json
import os

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
watched_file = os.path.join(addon_path, 'watched.json')

def load_watched():
    try:
        with open(watched_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def apply_watched_status():
    watched = load_watched()
    for video_id, entry in watched.items():
        percent = entry.get("played_percent", 0)
        if percent >= 90:
            # For overlays to show up in widgets, the skin must call ListItem.PlayCount
            # This is a placeholder for whatever sets ListItem.Property in your widget items
            xbmc.log(f"Marking '{video_id}' as watched (percent: {percent})", xbmc.LOGINFO)
            # Nothing is returned here—ListItem properties must be injected during item creation

if __name__ == "__main__":
    apply_watched_status()
