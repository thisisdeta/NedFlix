import re
import json
import xbmc
import xbmcgui
import xbmcvfs

# -----------------------------
# Helper functions for HUB widgets (unchanged)
# -----------------------------

def clear_hub_properties_json(properties_file, slot_index):
    """
    Clears all property values for a home widget slot in the properties JSON file.
    For the given slot, it empties the values for keys:
       "widget", "widgetName", "widgetType", "widgetTarget", and "widgetPath".
    For slot_index 1, keys have no suffix; for slot_index >= 2, keys have a suffix of ".{slot_index-1}".
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Determine suffix based on slot index:
        # slot_index 1 -> suffix = ""
        # slot_index 2 -> suffix = ".1", slot_index 3 -> ".2", etc.
        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        keys_to_clear = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]

        for entry in data:
            # Check for proper format: each entry should be a list with 4 elements.
            if isinstance(entry, list) and len(entry) == 4:
                if entry[0] == "mainmenu" and entry[1] == "10000":
                    # For every key that should be cleared, if the third element matches key+suffix, clear the value.
                    for key in keys_to_clear:
                        if entry[2] == f"{key}{suffix}":
                            # For debugging, you can uncomment the line below:
                            # xbmc.log(f"Clearing entry for key: {entry[2]} in slot {slot_index}", xbmc.LOGERROR)
                            entry[3] = ""
        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        xbmc.log("Error clearing home widget properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to clear home widget properties.")

def update_hub_properties_json(properties_file, slot_index, new_value, is_home_widget=False):
    """
    Updates the widgetName value for a widget slot in the JSON properties file.

    For home widgets:
      - The key is "widgetName" for slot 1 and "widgetName.{i-1}" thereafter.
      
    For hub widgets:
      - The key will be prefixed with "hub." (i.e. "hub.widgetName" for slot 1 and
        "hub.widgetName.{i-1}" for subsequent slots).
      - If no such hub entry exists, a new one is appended without modifying any
        existing home widget data.
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Create a suffix: "" for slot 1, ".{slot_index-1}" for later slots.
        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        if is_home_widget:
            target_key = "widgetName" + suffix
        else:
            target_key = "hub.widgetName" + suffix

        updated = False
        for entry in data:
            if isinstance(entry, list) and len(entry) >= 4:
                # Only update an entry that exactly matches the target key.
                if entry[0] == "mainmenu" and entry[1] == "10000" and entry[2] == target_key:
                    entry[3] = new_value
                    updated = True
                    break

        # For hub widgets (is_home_widget == False): If no hub entry exists,
        # do not fall back to legacy "widgetName". Instead, add a new entry.
        if not updated and not is_home_widget:
            data.append(["mainmenu", "10000", target_key, new_value])
            updated = True

        if not updated:
            xbmcgui.Dialog().ok("Warning", f"No matching JSON entry found for key: {target_key}")
        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to update widget JSON properties.")

def remove_widget_includes(skin_xml_file, widget_id):
    """
    Removes the <include> blocks from the skin XML file that contain a 
    <param name="widgetid" value="widget_id" /> element.
    """
    try:
        with open(skin_xml_file, "r", encoding="utf-8") as f:
            xml_content = f.read()
        pattern = rf"<include\b(?:(?!<\/include>).)*?<param\s+name=\"widgetid\"\s+value=\"{re.escape(widget_id)}\".*?<\/include>"
        new_xml, count = re.subn(pattern, "", xml_content, flags=re.DOTALL | re.IGNORECASE)
        if count == 0:
            xbmcgui.Dialog().ok("Warning", f"No matching include blocks found for widgetid {widget_id}.")
        with open(skin_xml_file, "w", encoding="utf-8") as f:
            f.write(new_xml)
    except Exception as e:
        xbmc.log("Error removing widget includes: " + str(e), xbmc.LOGERROR)
#        xbmcgui.Dialog().ok("Error", "Failed to remove widget includes.")

# -----------------------------
# New Home Widget Helpers (Dynamic Loader)
# -----------------------------
def get_home_widgets(properties_file):
    """
    Dynamically loads home widgets from the properties file.
    The JSON is expected to be an array, where each entry is of the form:
         [ "mainmenu", "10000", key, value ]
    We group entries by slot index: unsuffixed keys correspond to slot 0,
    keys with ".N" suffix go to slot N.
    Returns a list of dictionaries, one per slot, containing keys:
         "widget", "widgetName", "widgetType", "widgetTarget", "widgetPath".
    Only entries whose keys do NOT start with "hub." (i.e. home widgets) are loaded.
    """
    keys = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]
    try:
        if not xbmcvfs.exists(properties_file):
            xbmcgui.Dialog().ok("Error", "Properties file not found:\n" + properties_file)
            return []
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        slots = {}  # dictionary keyed by slot index (integer)
        for entry in data:
            if (isinstance(entry, list) and len(entry) >= 4 and
                entry[0] == "mainmenu" and entry[1] == "10000"):
                full_key = entry[2]
                value = entry[3]
                # Skip any keys that start with "hub." so that hub widgets are not loaded here.
                if full_key.startswith("hub."):
                    continue
                # Process home-widget key normally.
                if "." in full_key:
                    base, suffix = full_key.split(".", 1)
                    try:
                        idx = int(suffix)
                    except Exception:
                        idx = 0
                else:
                    base = full_key
                    idx = 0

                if base not in keys:
                    continue
                if idx not in slots:
                    # Initialize slot with empty strings for each key.
                    slots[idx] = {k: "" for k in keys}
                slots[idx][base] = value
        # Convert the dictionary to a list ordered by slot index.
        widget_slots = [slots[i] for i in sorted(slots.keys())]
        return widget_slots
    except Exception as e:
        xbmc.log("Error in get_home_widgets: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to load home widgets.")
        return []

# -----------------------------
# HOME WIDGET FUNCTIONS (using dynamic loader)
# -----------------------------
def rename_home_widget(settings_file, home_xml_file):
    """
    Provides a dialog workflow to rename a home widget.
    Loads home widgets from the properties file dynamically using get_home_widgets(),
    then saves the updated set. After each rename attempt (successful or not),
    the widget select menu is re-displayed.
    Empty slots are not offered for renaming.
    """
    import xbmcgui
    import json
    import xbmcvfs

    # Define the path to the properties file.
    PROPERTIES_FILE = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.nedflix.properties")
    dlg = xbmcgui.Dialog()

    while True:
        # Load current home widget data using our dynamic loader.
        widgets = get_home_widgets(PROPERTIES_FILE)
        if not widgets:
            dlg.ok("Info", "No home widgets found.")
            return

        # Build a display list that includes only populated (non-empty) widgets.
        display_list = []
        valid_indices = []
        for idx, widget in enumerate(widgets):
            name = widget.get("widgetName", "").strip()
            if name:
                display_list.append(name)
                valid_indices.append(idx)

        if not display_list:
            dlg.ok("Info", "No populated home widgets found.")
            return

        # Let the user select a widget to rename.
        choice = dlg.select("Select widget to rename", display_list)
        if choice == -1:
            # Go back to hub selection
            return rename_widget(settings_file, home_xml_file)


        actual_index = valid_indices[choice]
        current_name = display_list[choice]

        # Ask the user for the new name.
        new_name = dlg.input("Enter new name for home widget", current_name)
        if new_name is None or new_name.strip() == "":
            # If the user cancels the input or enters an empty name,
            # just continue back to the widget select menu.
            continue

        # Update the selected widget with the new name.
        widgets[actual_index]["widgetName"] = new_name

        # Rebuild the JSON structure that represents all widget slots.
        new_properties = []
        keys = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]
        for idx, widget in enumerate(widgets):
            suffix = "" if idx == 0 else f".{idx}"
            for key in keys:
                new_properties.append(["mainmenu", "10000", key + suffix, widget.get(key, "")])

        try:
            with open(PROPERTIES_FILE, "w", encoding="utf-8") as f:
                json.dump(new_properties, f, indent=4)
            
        except Exception as e:
            xbmc.log("Error saving home widgets: " + str(e), xbmc.LOGERROR)
            dlg.ok("Error", "Failed to save home widget changes.")

        # After completing (or failing) a rename, loop back to allow another selection.
        

def delete_home_widget(settings_file, home_xml_file):
    """
    Provides a dialog workflow to delete a home widget.
    Loads home widgets dynamically using get_home_widgets();
    then clears the values for all keys for the chosen slot in the JSON properties file.
    No XML files are modified.
    After a successful deletion, the delete menu is automatically re-displayed.
    """
    import xbmcgui, xbmcvfs, json
    PROPERTIES_FILE = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.nedflix.properties")
    dlg = xbmcgui.Dialog()

    while True:
        # Load current home widget data using our dynamic loader.
        widgets = get_home_widgets(PROPERTIES_FILE)
        if not widgets:
            dlg.ok("Info", "No home widgets found.")
            return

        # Build a display list using only populated (non-empty) widgetName slots.
        display_list = []
        valid_indices = []
        for idx, widget in enumerate(widgets):
            name = widget.get("widgetName", "").strip()
            if name:
                display_list.append(name)
                valid_indices.append(idx)

        if not display_list:
            dlg.ok("Info", "No populated home widgets found.")
            return

        # Let the user select a widget to delete.
        choice = dlg.select("Select widget to delete", display_list)
        if choice == -1:
            # Go back to hub selection in delete_widget
            return delete_widget(settings_file, home_xml_file)


        # Use the actual index from our filtered list.
        actual_index = valid_indices[choice]
        current_name = display_list[choice]

        # Confirm deletion.
        if not dlg.yesno("Confirm Delete", f"Are you sure you want to delete '{current_name}'?"):
            continue

        # Calculate slot_index (slot 1 uses no suffix; slot 2 uses suffix ".1", etc.)
        slot_index = actual_index + 1

        # Clear all properties for this widget slot.
        clear_hub_properties_json(PROPERTIES_FILE, slot_index)
#        dlg.ok("Success", f"Home widget '{current_name}' deleted.")

        # After deletion, automatically loop back to the selection menu.
        
def rename_hub_widget(settings_file):
    """
    Provides a dialog workflow to rename a hub widget.
    Updates both the XML settings file and JSON properties.
    """
    from default import extract_hub_names, extract_widget_names
    dlg = xbmcgui.Dialog()

    while True:
        hubs, hubs_display = extract_hub_names(settings_file)
        if not hubs:
            dlg.ok("Error", "No hubs found.")
            return

        hub_choice = dlg.select("Select a hub to rename widget", hubs_display)
        if hub_choice == -1:
            break
        selected_hub = hubs[hub_choice]

        while True:
            widget_names = extract_widget_names(settings_file, selected_hub)
            populated = []
            populated_indices = []
            for idx, widget_name in enumerate(widget_names):
                if "(No widget assigned)" not in widget_name:
                    populated.append(widget_name)
                    populated_indices.append(idx)
            if not populated:
                dlg.ok("Info", "No populated widgets found in this hub.")
                break

            widget_choice = dlg.select("Select widget to rename", populated)
            if widget_choice == -1:
                break

            actual_index = populated_indices[widget_choice]
            current_name = populated[widget_choice]
            new_name = dlg.input("Enter new name for widget", current_name)
            if new_name is None or new_name.strip() == "":
                continue
            new_name = new_name.strip()

            # Calculate the widget_id based on the actual_index.
            widget_id = 510 + actual_index * 10 if actual_index < 9 else 5100

            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                pattern = rf'(<setting id="{selected_hub}-{widget_id}\.label" type="string">)(.*?)(</setting>)'
                new_content, count = re.subn(
                    pattern,
                    lambda m: m.group(1) + new_name + m.group(3),
                    content,
                    flags=re.DOTALL
                )
                if count == 0:
                    dlg.ok("Error", "Widget label not found; unable to rename widget.")
                    continue
                with open(settings_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                xbmc.log("Error renaming widget: " + str(e), xbmc.LOGERROR)
                dlg.ok("Error", "Failed to rename widget.")
                continue

            # Define slot_index explicitly after the XML update.
            slot_index = actual_index + 1
            PROPERTIES_FILE = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.nedflix.properties")
            try:
                update_hub_properties_json(PROPERTIES_FILE, slot_index, new_name, is_home_widget=False)
            except Exception as e:
                xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
                dlg.ok("Error", "Failed to update hub widget JSON properties.")
                continue

            dlg.ok("Success", f"Renamed widget '{current_name}' to '{new_name}'")
            # Continue to allow additional renaming.
            continue

def delete_widget(settings_file, home_xml_file):
    """
    Provides a main dialog workflow to delete a widget.
    For hub widgets, updates both the settings XML and JSON properties,
    and removes related XML <include> blocks.
    For home widgets, calls delete_home_widget().
    """
    from default import extract_hub_names, extract_widget_names
    hubs, hubs_display = extract_hub_names(settings_file)
    if not hubs:
        xbmcgui.Dialog().ok("Error", "No hubs found.")
        return

    hubs_display.insert(0, "Home")
    choice = xbmcgui.Dialog().select("Select hub for deleting widgets", hubs_display)
    if choice == -1:
        return
    if choice == 0:
        delete_home_widget(settings_file, home_xml_file)
        return
    selected_hub = hubs[choice - 1]

    while True:
        widget_names = extract_widget_names(settings_file, selected_hub)
        if not widget_names:
            xbmcgui.Dialog().ok("Error", "No widgets found for this hub.")
            break

        populated = []
        populated_indices = []
        for idx, name in enumerate(widget_names):
            if "(No widget assigned)" not in name:
                populated.append(name)
                populated_indices.append(idx)

        if not populated:
            xbmcgui.Dialog().ok("Error", "No populated widgets found for this hub.")
            break

        widget_choice = xbmcgui.Dialog().select("Select widget to delete", populated)
        if widget_choice == -1:
            # Just break out of widget selection, not the whole hub menu
            return delete_widget(settings_file, home_xml_file)

        actual_index = populated_indices[widget_choice]
        current_name = populated[widget_choice]
        if not xbmcgui.Dialog().yesno("Confirm Delete", f"Are you sure you want to delete '{current_name}'?"):
            continue

        widget_id = 510 + actual_index * 10 if actual_index < 9 else 5100
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                content = f.read()

            pattern = rf'\s*<setting id="{selected_hub}-{widget_id}\.(?:label|path|sortorder|sortby|LocalizedSortOrder|LocalizedSortBy|target)" type="string">.*?</setting>\s*'
            new_content, count = re.subn(pattern, "", content, flags=re.DOTALL)
            if count == 0:
                xbmcgui.Dialog().ok("Error", "No widget settings were removed; unable to delete widget.")
                continue

            with open(settings_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            slot_index = actual_index + 1
            PROPERTIES_FILE = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.nedflix.properties")
            update_hub_properties_json(PROPERTIES_FILE, slot_index, "")
            SKIN_XML_FILE = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.xml")
            remove_widget_includes(SKIN_XML_FILE, "2520")  # Update if needed
        except Exception as e:
            xbmc.log("Error deleting widget: " + str(e), xbmc.LOGERROR)
            xbmcgui.Dialog().ok("Error", "Failed to delete widget.")
            continue


# -----------------------------
# MAIN DIALOG FUNCTIONS
# -----------------------------
def rename_widget(settings_file, home_xml_file):
    """
    Provides a main dialog workflow to rename a widget.
    Shows a menu with option "Home" for home widgets and a list of hubs.
    """
    while True:
        from default import extract_hub_names, extract_widget_names
        hubs, hubs_display = extract_hub_names(settings_file)
        if not hubs:
            xbmcgui.Dialog().ok("Error", "No hubs found.")
            return

        hubs_display.insert(0, "Home")
        choice = xbmcgui.Dialog().select("Select hub for renaming widgets", hubs_display)
        if choice == -1:
            break
        if choice == 0:
            rename_home_widget(settings_file, home_xml_file)
            break
        selected_hub = hubs[choice - 1]

        while True:
            widget_names = extract_widget_names(settings_file, selected_hub)
            if not widget_names:
                xbmcgui.Dialog().ok("Error", "No widgets found for this hub.")
                break
            populated = []
            populated_indices = []
            for idx, name in enumerate(widget_names):
                if "(No widget assigned)" not in name:
                    populated.append(name)
                    populated_indices.append(idx)
            if not populated:
                xbmcgui.Dialog().ok("Error", "No populated widgets found for this hub.")
                break
            widget_choice = xbmcgui.Dialog().select("Select widget to rename", populated)
            if widget_choice == -1:
                break
            actual_index = populated_indices[widget_choice]
            current_name = populated[widget_choice]
            new_name = xbmcgui.Dialog().input("Enter new name for widget", current_name)
            if new_name is None or new_name.strip() == "":
                continue
            new_name = new_name.strip()
            widget_id = 510 + actual_index * 10 if actual_index < 9 else 5100

            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Use a lambda function for replacement to avoid backreference issues.
                pattern = rf'(<setting id="{selected_hub}-{widget_id}\.label" type="string">)(.*?)(</setting>)'
                new_content, count = re.subn(
                    pattern,
                    lambda m: m.group(1) + new_name + m.group(3),
                    content,
                    flags=re.DOTALL
                )
                if count == 0:
                    xbmcgui.Dialog().ok("Error", "Widget label not found; unable to rename widget.")
                    continue
                with open(settings_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except Exception as e:
                xbmc.log("Error renaming widget: " + str(e), xbmc.LOGERROR)
                xbmcgui.Dialog().ok("Error", "Failed to rename widget.")
                continue

            # Define slot_index explicitly here.
            slot_index = actual_index + 1
            PROPERTIES_FILE = xbmcvfs.translatePath("special://userdata/addon_data/script.skinshortcuts/skin.nedflix.properties")
            try:
                update_hub_properties_json(PROPERTIES_FILE, slot_index, new_name, is_home_widget=False)
            except Exception as e:
                xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
                xbmcgui.Dialog().ok("Error", "Failed to update hub widget JSON properties.")
                continue

#            xbmcgui.Dialog().ok("Success", f"Renamed widget '{current_name}' to '{new_name}'")
            # Loop back to allow additional renames.
            continue


