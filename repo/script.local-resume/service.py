import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
import json
import os
import time
import re

# Updated addon ID reference
ADDON = xbmcaddon.Addon(id='script.local-resume')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
xbmcvfs.mkdirs(PROFILE)
RESUME_FILE = os.path.join(PROFILE, 'resume_points.json')

def format_time(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def get_stable_key(url):
    base_url = url.split('.m3u8')[0] + '.m3u8'
    match = re.search(r'/video/\d+/\d+/\d+_mp4_h264_aac_fhd_1\.m3u8', base_url)
    if match:
        return match.group(0)
    else:
        return base_url

def is_dailymotion_url(url):
    return "dailymotion.com" in url or "dmcdn.net" in url

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

def main():
    resume_manager = ResumeManager()
    player = xbmc.Player()
    monitor = xbmc.Monitor()
    last_key = None
    prompted = False

    while not monitor.abortRequested():
        if player.isPlayingVideo():
            current_path = player.getPlayingFile()

            if not is_dailymotion_url(current_path):
                time.sleep(1)
                continue

            stable_key = get_stable_key(current_path)

            if stable_key != last_key:
                last_key = stable_key
                prompted = False

            if not prompted:
                resume_pos = resume_manager.get_resume_point(stable_key)
                if resume_pos > 0:
                    player.pause()  # Pause playback before showing dialog
                    formatted_time = format_time(resume_pos)
                    dialog = xbmcgui.Dialog()
                    choice = dialog.select("Resume Playback",
                                           [f"Resume from {formatted_time}", "Nahh"])

                    if choice == 0:
                        xbmc.log(f"Resuming {current_path} at {resume_pos} seconds", xbmc.LOGINFO)
                        player.seekTime(resume_pos)
                    elif choice == 1:
                        resume_manager.set_resume_point(stable_key, 0)
                    player.pause()  # Unpause playback after dialog closes
                prompted = True

            pos = player.getTime()
            if pos >= 60:
                resume_manager.set_resume_point(stable_key, pos)

        else:
            last_key = None
            prompted = False

        time.sleep(5)


if __name__ == '__main__':
    main()
