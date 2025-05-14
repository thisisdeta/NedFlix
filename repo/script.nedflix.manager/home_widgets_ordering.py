import os
import json
import xbmc
import xbmcgui
import xbmcvfs

# Define the properties file path.
PROPERTIES_PATH = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.bingie.fen.light.mod.properties")

def load_properties():
    """
    Loads the properties file (JSON) that represents home widget configuration.
    Expected format: An array of entries [group, id, key, value]
    """
    try:
        with xbmcvfs.File(PROPERTIES_PATH, 'r') as f:
            data = f.read()
        return json.loads(data)
    except Exception as e:
        xbmc.log("Error loading properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to load properties file.")
        return []

def save_properties(properties):
    """
    Saves the given properties (a list) back to the properties file.
    """
    try:
        with xbmcvfs.File(PROPERTIES_PATH, 'w') as f:
            f.write(json.dumps(properties, indent=4))
    except Exception as e:
        xbmc.log("Error saving properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to save properties file.")

def get_virtual_slots():
    """
    Converts the JSON properties into a list of 10 virtual slots.
    For home widgets, slot 1 uses unsuffixed keys;
    for slots 2..10, keys use suffixes ".{i-1}".
    Returns a list of dictionaries with keys:
       "widget", "widgetName", "widgetType", "widgetTarget", "widgetPath".
    """
    keys = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]
    properties = load_properties()
    # Filter entries for group "mainmenu" and id "10000"
    filtered = [entry for entry in properties if entry[0] == "mainmenu" and entry[1] == "10000"]
    slots = []
    for i in range(1, 11):
        slot = {key: "" for key in keys}
        suffix = "" if i == 1 else f".{i-1}"
        for entry in filtered:
            # entry in the format: [group, id, key, value]
            for key in keys:
                if entry[2] == key + suffix:
                    slot[key] = entry[3]
        slots.append(slot)
    return slots

def save_virtual_slots(slots):
    """
    Converts and saves the modified virtual slots back to the properties file.
    Each slot is written as a set of entries for group "mainmenu" and id "10000".
    """
    keys = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]
    new_properties = []
    for i, slot in enumerate(slots, start=1):
        suffix = "" if i == 1 else f".{i-1}"
        for key in keys:
            new_properties.append(["mainmenu", "10000", key + suffix, slot.get(key, "")])
    save_properties(new_properties)

def build_display_list(slots):
    """
    Constructs a list of display strings for the widget list.
    If a slot's "widgetName" is empty, it shows a placeholder.
    """
    display = []
    for idx, slot in enumerate(slots, start=1):
        name = slot.get("widgetName", "")
        if name:
            display.append(f" {name}")
        else:
            display.append(f"Slot {idx} (No widget assigned)")
    return display

def reorder_home_widgets():
    """
    Presents a dialog workflow to reorder home widget slots.
    This function uses only the properties file (via virtual slots).
    When the change is confirmed the properties file is updated.
    """
    dialog = xbmcgui.Dialog()
    slots = get_virtual_slots()
    while True:
        display_list = build_display_list(slots)
        src_index = dialog.select("Select widget to move", display_list)
        if src_index == -1:
            # Exit the reordering menu (returns control to the caller)
            break
        tgt_index = dialog.select("Select target slot", display_list, preselect=src_index)
        if tgt_index == -1 or src_index == tgt_index:
            continue
        # Swap the slots and save the new order.
        slots[src_index], slots[tgt_index] = slots[tgt_index], slots[src_index]
        save_virtual_slots(slots)
        
        # Optionally reload the slots to reflect further changes.
        slots = get_virtual_slots()

def run():
    """
    Entry point for home widgets ordering.
    Only includes the reordering dialog.
    """
    reorder_home_widgets()

if __name__ == '__main__':
    run()
    
def get_home_widgets(properties_file):
    """
    Dynamically loads home widgets from the properties file.
    Supports any number of existing widgets instead of assuming exactly 10.
    """
    keys = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]
    widgets = []

    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Identify relevant widget entries
        for entry in data:
            if isinstance(entry, list) and len(entry) >= 4 and entry[0] == "mainmenu" and entry[1] == "10000":
                key_base = entry[2].split(".")[0]  # Extract base key (e.g., "widgetName")
                if key_base in keys:
                    slot_index = entry[2].split(".")[-1] if "." in entry[2] else "0"
                    slot_index = int(slot_index) if slot_index.isdigit() else 0

                    # Expand list dynamically for indexing
                    while len(widgets) <= slot_index:
                        widgets.append({k: "" for k in keys})

                    widgets[slot_index][key_base] = entry[3]

        # Remove empty widgets (without data)
        widgets = [w for w in widgets if any(w.values())]
        return widgets

    except Exception as e:
        xbmc.log("Error loading home widgets: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to load home widget properties file.")
        return []