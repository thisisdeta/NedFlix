import re
import xbmcgui
import xbmcvfs

def change_widget_size():
    """
    Updates two XML files with new widget size values:
      - For IncludesHomeWidgets.xml, updates all occurrences of
        <height>NUMBER</height> and <width>NUMBER</width> (both tag-based
        and attribute-based) between lines 301 and 346.
      - For IncludesBingie.xml, updates the two <param> tags on lines 2192 and 2193.
    
    The function first reads the current dimensions from IncludesHomeWidgets.xml
    (the first occurrence in the specified line range) and shows that in the input prompt.
    """
    # === Update IncludesHomeWidgets.xml ===
    widget_file = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/IncludesHomeWidgets.xml")
    
    try:
        with open(widget_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        xbmcgui.Dialog().ok("Change Widget Size", "Error reading file: " + str(e))
        return

    # Define the line range to update (0-indexed)
    start_line = 300  # corresponds to line 301
    end_line   = 346  # updates up to line 346 (i.e. index 345)

    # Attempt to get the current height from the range (using a tag-based value)
    current_height = None
    current_width  = None
    for line in lines[start_line: end_line]:
        m = re.search(r"<height>(\d+)</height>", line)
        if m:
            current_height = m.group(1)
            break
    for line in lines[start_line: end_line]:
        m = re.search(r"<width>(\d+)</width>", line)
        if m:
            current_width = m.group(1)
            break

    if current_height is None: 
        current_height = "unknown"
    if current_width is None:
        current_width = "unknown"

    # Prompt for new height/width from the user,
    # the prompt shows the current value in its header text.
    new_height = xbmcgui.Dialog().input("New Widget Height (current: %s)" % current_height, type=xbmcgui.INPUT_NUMERIC)
    new_width  = xbmcgui.Dialog().input("New Widget Width (current: %s)" % current_width, type=xbmcgui.INPUT_NUMERIC)
    
    if not new_height or not new_width:
        xbmcgui.Dialog().ok("Change Widget Size", "Operation cancelled")
        return

    new_height = new_height.strip()
    new_width  = new_width.strip()
    
    if not new_height.isdigit() or not new_width.isdigit():
        xbmcgui.Dialog().ok("Change Widget Size", "Invalid numeric values")
        return

    # Compile regex patterns for tag-based height/width.
    tag_height_pattern = re.compile(r"(<height>)(\d+)(</height>)")
    tag_width_pattern  = re.compile(r"(<width>)(\d+)(</width>)")
    # Compile regex patterns for attribute-based height/width.
    attr_height_pattern = re.compile(r'(height=")(\d+)(")')
    attr_width_pattern  = re.compile(r'(width=")(\d+)(")')
    
    # Process the designated range in the widget file.
    for i in range(start_line, min(end_line, len(lines))):
        line = lines[i]
        # Replace tag-style height and width.
        line = tag_height_pattern.sub(lambda m: m.group(1) + new_height + m.group(3), line)
        line = tag_width_pattern.sub(lambda m: m.group(1) + new_width + m.group(3), line)
        # Replace attribute-style height and width.
        line = attr_height_pattern.sub(lambda m: m.group(1) + new_height + m.group(3), line)
        line = attr_width_pattern.sub(lambda m: m.group(1) + new_width + m.group(3), line)
        lines[i] = line

    try:
        with open(widget_file, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        xbmcgui.Dialog().ok("Change Widget Size", "Error writing widget file: " + str(e))
        return

    # === Update IncludesBingie.xml ===
    bingie_file = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/IncludesBingie.xml")
    
    try:
        with open(bingie_file, "r", encoding="utf-8") as f:
            bingie_lines = f.readlines()
    except Exception as e:
        xbmcgui.Dialog().ok("Change Bingie Size", "Error reading file: " + str(e))
        return

    # Lines 2192 and 2193 (1-based) become indices 2191 and 2192 (0-indexed)
    bingie_start = 2191
    bingie_end   = 2193  # We'll update indices 2191 and 2192

    # Patterns for the <param> tags.
    width_param_pattern = re.compile(r'(<param\s+name="width"\s+value=")(\d+)(")')
    height_param_pattern = re.compile(r'(<param\s+name="height"\s+value=")(\d+)(")')

    for i in range(bingie_start, min(bingie_end, len(bingie_lines))):
        line = bingie_lines[i]
        line = width_param_pattern.sub(lambda m: m.group(1) + new_width + m.group(3), line)
        line = height_param_pattern.sub(lambda m: m.group(1) + new_height + m.group(3), line)
        bingie_lines[i] = line

    try:
        with open(bingie_file, "w", encoding="utf-8") as f:
            f.writelines(bingie_lines)
    except Exception as e:
        xbmcgui.Dialog().ok("Change Bingie Size", "Error writing file: " + str(e))
        return

    xbmcgui.Dialog().ok("Change Widget Size", "Widgets resized to height: %s, width: %s" % (new_height, new_width))