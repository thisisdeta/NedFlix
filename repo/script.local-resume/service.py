import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import json
import os
import time
import urllib.parse
import re

# Addon setup
ADDON = xbmcaddon.Addon(id='script.local-resume')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
xbmcvfs.mkdirs(PROFILE)

# Files for storing data
RESUME_FILE  = os.path.join(PROFILE, 'resume_points.json')
WATCHED_FILE = os.path.join(PROFILE, 'watched.json')

# ResumeManager unchanged…
class ResumeManager:
    def __init__(self):
        self.resume_data = {}
        self.load_resume_data()

    def load_resume_data(self):
        if os.path.exists(RESUME_FILE):
            try:
                with open(RESUME_FILE, 'r', encoding='utf-8') as f:
                    self.resume_data = json.load(f)
            except Exception as e:
                xbmc.log(f"ResumeManager: Failed to load resume data: {e}", xbmc.LOGERROR)
                self.resume_data = {}

    def save_resume_data(self):
        try:
            with open(RESUME_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.resume_data, f, indent=4)
        except Exception as e:
            xbmc.log(f"ResumeManager: Failed to save resume data: {e}", xbmc.LOGERROR)

    def set_resume_point(self, key, position):
        self.resume_data[key] = position
        self.save_resume_data()

    def get_resume_point(self, key):
        return self.resume_data.get(key, 0)

# WatchedManager to log completed videos
class WatchedManager:
    def __init__(self):
        self.watched = {}
        self.load_watched()

    def load_watched(self):
        if os.path.exists(WATCHED_FILE):
            try:
                with open(WATCHED_FILE, 'r', encoding='utf-8') as f:
                    self.watched = json.load(f)
            except Exception as e:
                xbmc.log(f"WatchedManager: Failed to load watched data: {e}", xbmc.LOGERROR)
                self.watched = {}

    def save_watched(self):
        try:
            with open(WATCHED_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.watched, f, indent=4)
        except Exception as e:
            xbmc.log(f"WatchedManager: Failed to save watched data: {e}", xbmc.LOGERROR)

    def mark_watched(self, key):
        """Log when a video was watched to completion."""
        self.watched[key] = time.time()
        self.save_watched()

    def is_watched(self, key):
        return key in self.watched

# Helper to format seconds into h/m/s
def format_time(seconds):
    seconds = int(seconds)
    hours   = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs    = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

# Friendly key: Title only if no year metadata
def get_stable_key():
    tag   = xbmc.Player().getVideoInfoTag()
    title = tag.getTitle() or ""
    year  = tag.getYear() or 0

    # Skip any with year metadata
    if year:
        return None

    # Use title, or fallback to UI label, or filename
    if title:
        friendly = title
    else:
        friendly = xbmc.getInfoLabel("ListItem.Label") or ""
    if not friendly:
        path = xbmc.Player().getPlayingFile()
        friendly = path.split("/")[-1].split("?")[0]
    return friendly

# Main service loop
def main():
    resume_manager  = ResumeManager()
    watched_manager = WatchedManager()
    player          = xbmc.Player()
    monitor         = xbmc.Monitor()

    last_key       = None
    prompted       = False
    last_pos       = None
    pause_saved    = False
    last_save_time = 0

    while not monitor.abortRequested():
        if player.isPlayingVideo():
            # Determine our stable key or skip if media has a year
            stable_key = get_stable_key()
            if not stable_key:
                time.sleep(5)
                continue

            # Reset on new video
            if stable_key != last_key:
                last_key       = stable_key
                prompted       = False
                last_pos       = None
                pause_saved    = False
                last_save_time = 0

            # Prompt resume once
            if not prompted:
                resume_pos = resume_manager.get_resume_point(stable_key)
                if resume_pos > 0:
                    formatted_time = format_time(resume_pos)
                    player.pause()
                    dialog = xbmcgui.Dialog()
                    choice = dialog.select(
                        "Resume Playback",
                        [f"Resume from {formatted_time}", "Don't resume"]
                    )
                    player.pause()

                    if choice == 0:
                        xbmc.log(f"Resuming {stable_key} at {resume_pos}s", xbmc.LOGINFO)
                        player.seekTime(resume_pos)
                    else:
                        resume_manager.set_resume_point(stable_key, 0)
                prompted = True

            # Track playback position & duration
            pos   = player.getTime()
            total = player.getTotalTime() or 0

            if last_pos is None:
                last_pos = pos
            else:
                # — Playing → save every 5 s after 60 s
                if pos > last_pos:
                    now = time.time()
                    if now - last_save_time >= 5 and pos >= 60:
                        # Completed ≥99%?
                        if total > 0 and pos >= 0.99 * total:
                            if not watched_manager.is_watched(stable_key):
                                watched_manager.mark_watched(stable_key)
                            resume_manager.set_resume_point(stable_key, 0)
                        else:
                            resume_manager.set_resume_point(stable_key, max(pos - 4, 0))
                        last_save_time = now
                    pause_saved = False

                # — Paused → save once on pause
                elif pos == last_pos and not pause_saved:
                    if pos >= 60:
                        if total > 0 and pos >= 0.99 * total:
                            if not watched_manager.is_watched(stable_key):
                                watched_manager.mark_watched(stable_key)
                            resume_manager.set_resume_point(stable_key, 0)
                        else:
                            resume_manager.set_resume_point(stable_key, max(pos - 4, 0))
                    pause_saved = True

                last_pos = pos

        else:
            # Reset when playback stops
            last_key       = None
            prompted       = False
            last_pos       = None
            pause_saved    = False
            last_save_time = 0

        time.sleep(5)

if __name__ == '__main__':
    main()
