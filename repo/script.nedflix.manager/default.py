import os
import re
import time
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json

import home_widgets_ordering
import rename_delete_widgets
from change_widget_size import change_widget_size
from change_splash import choose_splash_screen 

# Friendly mappings for hubs (used for display)
HUB_FRIENDLY_MAPPING = {
    "moviesaddon": "Films",
    "tvshowsaddon": "TV",
    "myhub": "Animation",
    "newaddon": "New & Popular",
    "music": "Wrestling"
}

def get_kodi_userdata_path():
    kodi_base_path = xbmcvfs.translatePath("special://userdata")
    return os.path.join(kodi_base_path, "addon_data", "skin.nedflix", "settings.xml")

def extract_hub_names(xml_file):
    """
    Extract unique hub IDs from the settings.xml file.
    Returns both the raw hub IDs and a friendly display list.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = re.compile(r'<setting id="(bingiehub-[^-]+)-\d+\.label" type="string">')
        hubs = pattern.findall(content)
        hubs = sorted(list(set(hubs)))
        hubs = [hub for hub in hubs if not hub.endswith("local") and hub not in ["bingiehub-customhub", "bingiehub-somethingaddon"]]
        display_list = []
        for hub in hubs:
            hub_key = hub.replace("bingiehub-", "")
            display_name = HUB_FRIENDLY_MAPPING.get(hub_key, hub_key)
            display_list.append(display_name)
        return hubs, display_list
    except Exception:
        return [], []

def extract_widget_names(xml_file, hub):
    """
    Extract widget names for a given hub from the settings.xml file.
    Assumes a maximum of 10 widget slots.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        widget_names = []
        for i in range(10):
            widget_id = 510 + i * 10 if i < 9 else 5100
            label_pattern = rf'<setting id="{hub}-{widget_id}\.label" type="string">(.*?)</setting>'
            match = re.search(label_pattern, content)
            if match and match.group(1).strip():
                widget_names.append(match.group(1).strip())
            else:
                widget_names.append(f"Slot {i+1} (No widget assigned)")
        return widget_names
    except Exception:
        return []

def clear_hub_properties_json(properties_file, slot_index):
    """
    Clears all property values for a home widget slot in the properties JSON file.
    Deletes the text within the fourth element of each relevant entry.
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        keys_to_clear = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]

        for entry in data:
            if isinstance(entry, list) and len(entry) == 4:  # Ensure the entry is correctly formatted
                if entry[0] == "mainmenu" and entry[1] == "10000":  # Target home widgets
                    for key in keys_to_clear:
                        if entry[2] == f"{key}{suffix}":  
                            entry[3] = ""  # Clear only the fourth value in the list

        # Save the updated JSON file
        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        xbmc.log("Error clearing home widget properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to clear home widget properties.")

def update_hub_properties_json(properties_file, slot_index, new_value, is_home_widget=False):
    """
    Updates the widgetName in the properties JSON file.
    Ensures that home widget updates do not affect hub widgets by scoping updates.
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        target_key = "widgetName" + suffix
        updated = False

        for entry in data:
            if isinstance(entry, list) and len(entry) >= 4:
                if entry[0] == "mainmenu" and entry[1] == "10000":
                    if is_home_widget:
                        # Restrict updates ONLY to home widgets (should not affect hubs)
                        if not entry[2].startswith("hub-"):
                            if entry[2] == target_key:
                                entry[3] = new_value
                                updated = True
                    else:
                        # Restrict updates ONLY to hub widgets
                        if entry[2].startswith("hub-"):
                            if entry[2] == target_key:
                                entry[3] = new_value
                                updated = True

        if not updated:
            xbmcgui.Dialog().ok("Warning", "No matching JSON widgetName entry was found.")

        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to update hub JSON properties.")
    """
    Directly updates the widgetName value for a hub widget slot in the JSON properties file.
    For slot 1, the key is "widgetName"; for slot i (i>=2) it is "widgetName.{i-1}".
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        target_key = "widgetName" + suffix
        updated = False
        for entry in data:
            if isinstance(entry, list) and len(entry) >= 4:
                if entry[0] == "mainmenu" and entry[1] == "10000" and entry[2] == target_key:
                    entry[3] = new_value
                    updated = True
        if not updated:
            xbmcgui.Dialog().ok("Warning", "No matching JSON widgetName entry was found.")
        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to update hub JSON properties.")

def remove_widget_includes(skin_xml_file, widget_id):
    """
    Removes <include> blocks from the skin XML file that contain a 
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
        xbmcgui.Dialog().ok("Error", "Failed to remove widget includes.")

def reorder_hub_widgets(selected_hub, settings_file):
    """
    Reorders widgets for a given hub by swapping widget settings in the XML file.
    """
    while True:
        widgets = extract_widget_names(settings_file, selected_hub)
        if not widgets:
            xbmcgui.Dialog().ok("Error", "No widgets found for the selected hub.")
            return
        dlg = xbmcgui.Dialog()
        while True:
            src = dlg.select("Select widget to move", widgets)
            if src == -1:
                return
            tgt = dlg.select("Select target slot", widgets, preselect=src)
            if tgt == -1 or src == tgt:
                break
            reorder_widget(settings_file, selected_hub, src, tgt)
            # Refresh the widget order after swap.
            widgets = extract_widget_names(settings_file, selected_hub)

def reorder_widget(xml_file, hub, source_index, target_index):
    """
    Swaps the settings for two widget slots within the specified hub.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        widget_id_source = 510 + source_index * 10 if source_index < 9 else 5100
        widget_id_target = 510 + target_index * 10 if target_index < 9 else 5100
        keys = ["path", "label", "sortorder", "sortby", "LocalizedSortOrder", "LocalizedSortBy", "target"]
        for key in keys:
            pattern_src = re.compile(rf'(<setting id="{hub}-{widget_id_source}\.{key}" type="string">)(.*?)(</setting>)')
            pattern_tgt = re.compile(rf'(<setting id="{hub}-{widget_id_target}\.{key}" type="string">)(.*?)(</setting>)')
            src_match = pattern_src.search(content)
            tgt_match = pattern_tgt.search(content)
            if src_match and tgt_match:
                src_val = src_match.group(2)
                tgt_val = tgt_match.group(2)
                content = content.replace(src_match.group(0),
                                          f'{src_match.group(1)}{tgt_val}{src_match.group(3)}')
                content = content.replace(tgt_match.group(0),
                                          f'{tgt_match.group(1)}{src_val}{tgt_match.group(3)}')
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        xbmc.log(f"[Reorder Hub Widgets] Failed to swap widget values: {e}", xbmc.LOGERROR)

def reorder_widgets_menu(settings_file):
    """
    Displays a menu for moving widgets between Home and Hub.
    For Home, calls the home widget ordering module.
    For Hubs, uses the settings.xml file.
    """
    while True:
        groups = ["Home"]
        hubs, hubs_display = extract_hub_names(settings_file)
        if hubs:
            for hub, disp in zip(hubs, hubs_display):
                groups.append(disp)
        sel_group = xbmcgui.Dialog().select("Select hub for moving widgets", groups)
        if sel_group == -1:
            break
        if sel_group == 0:
            # Launch the home widget ordering module.
            home_widgets_ordering.run()
        else:
            selected_hub = hubs[sel_group - 1]
            reorder_hub_widgets(selected_hub, settings_file)

def refresh_skin_and_verify():
    xbmc.executebuiltin("ReloadSkin()")
    time.sleep(3)
    retries = 5
    for _ in range(retries):
        if "bingie" in xbmc.getSkinDir().lower():
            return True
        time.sleep(2)
    return False

def save_and_close_kodi():
    xbmc.executebuiltin("RunAddon(plugin.close.kodi)")

def change_bingie_logo():
    
    import re, sys
    import xbmc, xbmcvfs, xbmcgui

    dialog = xbmcgui.Dialog()

    # Define your available theme options as tuples: (Display Label, Logo Image Path, Diffuse Hex Code)
    logo_options = [
        ("Red (Default)",                   "home/bingie_logo.png",                     "e50914"),
        ("Yellow",                          "home/bingie_logo_yellow.png",              "e5c709"),
        ("Yellow (Smiler)",                 "home/bingie_logo_yellow2.png",             "ffec00"),
        ("Blue (Prime Video)",              "home/bingie_logo_blue.png",                "0679fd"),
        ("Pink (iPlayer)",                  "home/bingie_logo_pink.png",                "ff4c98"),
        ("Turquoise",                       "home/bingie_logo_turquoise.png",           "45b8ac"),
        ("Sunlight",                        "home/bingie_logo_sunlight.png",            "edd59e"),
        ("Orange",                          "home/bingie_logo_orange.png",              "ffa00a"),
        ("Orange (Rec Room)",               "home/bingie_logo_orange2.png",             "ff6727"),
        ("Green",                           "home/bingie_logo_green.png",               "1dd72f"),
        ("Light Green (Channel 4)",         "home/bingie_logo_light_green.png",         "aaff89"),
        ("Aqua (Kodi)",                     "home/bingie_logo_aqua.png",                "2ba7d7"),
        ("Aqua 2",                          "home/bingie_logo_aqua2.png",               "01ffff"),
        ("Peach Fuzz",                      "home/bingie_logo_peach_fuzz.png",          "ffbe98"),
        ("Purple",                          "home/bingie_logo_purple.png",              "a515ff"),
        ("Purple (GOG)",                    "home/bingie_logo_purple2.png",             "6900d1"),
        ("Dedflix",                         "home/bingie_logo_dedflix.png",             "c20c0c"),
        ("Dedflix (Orange)",                "home/bingie_logo_dedflix2.png",            "fb7e07"),
        ("Nedflix",                         "home/bingie_logo_nedflix.png",             "1ed760")
    ]
    
    # Build a list of display labels for the selection dialog.
    display_labels = [option[0] for option in logo_options]
    
    # Translate the file path for the IncludesHomeBingie.xml file.
    file_path = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/IncludesHomeBingie.xml")
    if not xbmcvfs.exists(file_path):
        dialog.ok("Error", "File not found:\n" + file_path)
        return
    
    # Translate the file path for the Theme Variable.theme file.
    theme_file_path = xbmcvfs.translatePath("special://home/addons/skin.nedflix/extras/skinthemes/Update Theme.theme")
    
    # Translate the file path for the Custom_1159_MPAATopBar.xml file.
    custom_file_path = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/Custom_1159_MPAATopBar.xml")
    
    # Define the list of theme data keys that should get updated in the theme file.
    # Add or remove keys as needed.
    keys_to_update = [
        "WatchedIndicator.Watched.Color.base",
        "BingieProgressBarColor.base",
        "WatchedIndicator.Episodes.Color",
        "SpinnerTextureColor.base"
        "LineUnderMenuIconsColor.base",
        "lineundermenuiconscolor",
        "BingieOSDProgressBarColor.base",
        "BingieProgressBarColor",
        "WatchedIndicator.Episodes.Color.base",
        "WatchedIndicator.Watched.Color",
        "OSDVolumeButtonColor.base",
        "BingieNewEpisodesTagColor.base",
        "WatchedIndicator.Progress.Color.base",
        "bingienewepisodestagcolor",
        "ActiveSpinControlColor",
        "SpinnerTextureColor",
        "WatchedIndicator.Progress.Color",
        "ActiveSpinControlColor.base",
        "OSDBufferingSpinnerColor.base",
        "bingieosdprogressbarcolor",
        "OSDVolumeButtonColor",
        "osdbufferingspinnercolor",
        
        # You can add additional keys here if needed.
    ]
    
    # Loop continuously so the theme-selection dialog remains available until cancelled.
    while True:
        choice = dialog.select("Choose Theme", display_labels)
        if choice == -1:
            break  # Exit the function if the user cancels.
            
        # Map the selection to the chosen values.
        new_logo_path = logo_options[choice][1]
        new_diffuse_hex = logo_options[choice][2]
        
        try:
            # -----------------------------------
            # Update IncludesHomeBingie.xml
            # -----------------------------------
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if len(lines) < 835:
                dialog.ok("Error", "The file does not have at least 835 lines.")
                continue
            
            # Update the Bingie Logo line (assumed line 820; index 819)
            lines[819] = re.sub(r'(<texture>).*?(</texture>)', r'\1' + new_logo_path + r'\2', lines[819])
            # Update the Bingie Logo line (assumed line 832; index 831)
            lines[831] = re.sub(r'(<texture>).*?(</texture>)', r'\1' + new_logo_path + r'\2', lines[831])
            # Update the diffuse color line (assumed line 847; index 846)
            lines[846] = re.sub(r'(colordiffuse=")[0-9A-Fa-f]{8}(")', r'\1' + "ff" + new_diffuse_hex + r'\2', lines[846])
            
            # Write the updated contents back to IncludesHomeBingie.xml.
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            # -----------------------------------
            # Update Custom_1159_MPAATopBar.xml (line 36)
            # -----------------------------------
            if xbmcvfs.exists(custom_file_path):
                with open(custom_file_path, "r", encoding="utf-8") as f:
                    custom_lines = f.readlines()
                
                if len(custom_lines) < 36:
                    dialog.ok("Error", "Custom_1159_MPAATopBar.xml does not have at least 36 lines.")
                else:
                    # Using index 35 (line 36) modify the colordiffuse tag.
                    # The expected tag is: <colordiffuse>FFE50914</colordiffuse>
                    # We update the inner value to "FF" + new_diffuse_hex (in uppercase).
                    custom_lines[35] = re.sub(r"(<colordiffuse>)[^<]*(</colordiffuse>)",
                                              r"\1" + "FF" + new_diffuse_hex.upper() + r"\2",
                                              custom_lines[35])
                    
                    # Write back the updated lines.
                    with open(custom_file_path, "w", encoding="utf-8") as f:
                        f.writelines(custom_lines)
            
            # -----------------------------------
            # Update the Theme Variable.theme file if it exists.
            # -----------------------------------
            if xbmcvfs.exists(theme_file_path):
                with open(theme_file_path, "r", encoding="utf-8") as f:
                    theme_content = f.read()
                
                # For each key, update its value within the tuple.
                for key in keys_to_update:
                    # Construct a regex from the key.
                    # Pattern matches tuple of the form: ('string', 'KEY', 'XXXXXXXX')
                    pattern = r"(\('string',\s*'" + re.escape(key) + r"'\s*,\s*')[0-9A-Fa-f]{8}('.*\))"
                    replacement = r"\1" + "ff" + new_diffuse_hex + r"\2"
                    theme_content = re.sub(pattern, replacement, theme_content)
                
                with open(theme_file_path, "w", encoding="utf-8") as f:
                    f.write(theme_content)
            
            # Refresh the skin automatically.
            xbmc.executebuiltin("ReloadSkin()")
            xbmc.executebuiltin("RunScript(script.skin.helper.skinbackup,action=colorthemes)")
            sys.exit()
        
        except Exception as e:
            xbmc.log("Error updating Bingie theme: " + str(e), xbmc.LOGERROR)
            dialog.ok("Error", "Failed to update Bingie theme.")

def main_menu():
    options = [
        "Change Theme",
        "Change Kodi Splash Screen",
        "Move Widgets",       
        "Rename Widgets",
        "Delete Widgets",
        "Change Widget Size",  
        "Save and Refresh (Home Widgets)",
        "Save and Force Quit Kodi (All Widgets)",        
        "Exit"
    ]
    return xbmcgui.Dialog().select("Nedflix Manager", options)

if __name__ == '__main__':
    SETTINGS_FILE = get_kodi_userdata_path()  # Hub settings XML file
    # Define the home widgets XML file manually
    HOME_WIDGETS_FILE = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/script-skinshortcuts-includes.xml")
    
    while True:
        choice = main_menu()
        if choice == 0:
            change_bingie_logo()
        elif choice == 1:
            choose_splash_screen()
        elif choice == 2:
            reorder_widgets_menu(SETTINGS_FILE)
        elif choice == 3:
            rename_delete_widgets.rename_widget(SETTINGS_FILE, HOME_WIDGETS_FILE)
        elif choice == 4:
            rename_delete_widgets.delete_widget(SETTINGS_FILE, HOME_WIDGETS_FILE)
        elif choice == 5:
            change_widget_size()
        elif choice == 6:
            if refresh_skin_and_verify():
                pass
            sys.exit()
        elif choice == 7:
            save_and_close_kodi()        
        elif choice == 8:
            sys.exit()