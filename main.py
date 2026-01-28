# Imports
import librosa
import spleeter
import webview
import argparse
import os
import sys
import platformdirs
import hashlib
import render_waveform
import base64
import io
import shutil
import atexit
import uuid
import mimetypes
import threading

# * Constants
APPNAME = "STEMu"
FROZEN = getattr(sys, 'frozen', False)
DIRNAME = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
WAVEFORM_BINS = 300
WAVEFORM_DPI = 20

# Dirs
APP_CACHE_DIR = platformdirs.user_cache_dir(APPNAME)
if not os.path.exists(APP_CACHE_DIR):
    os.makedirs(APP_CACHE_DIR, exist_ok=True)

SESSION_CACHE_DIR = os.path.join(APP_CACHE_DIR, "session_" + uuid.uuid4().hex)
if not os.path.exists(SESSION_CACHE_DIR):
    os.makedirs(SESSION_CACHE_DIR, exist_ok=False)

# * Load arguments
argparser = argparse.ArgumentParser(
    prog="STEMu",
    epilog="Spleeter STEM separation UI",
    description="Spleeter STEM separation UI"
)

argparser.add_argument("--dev", action="store_true", help="Run in development mode")
argparser.add_argument("--port", type=int, default="5678", help="Port for development server (requires --dev)")
argparser.add_argument("--debug", action="store_true", help="Enable debug mode (shows webview inspector)")

args = argparser.parse_args()

# files = []
class JS_API():
    def close(self, *args):
        window.destroy()
        exit()

    def addFile(self, in_file, *args):
        # TODO: Threads or multiprocessing
        # Debug prints
        print("Received file:", in_file["filename"] + ", size:", len(in_file["data"]), "bytes")
        print(in_file["data"][:30])

        # Decode data
        [header, b64data] = in_file["data"].split(",", 1)
        data = base64.b64decode(b64data)

        # File paths
        # Consider using md5

        # hashlib.md5(data).hexdigest() + "_" +
        file_path = os.path.join(SESSION_CACHE_DIR, in_file["filename"])
        waveform_path = file_path + "_waveform.png"
        
        # Save original file
        with open(file_path, "wb") as f:
            f.write(data)

        # Get mimetype
        mimetype, _ = mimetypes.guess_type(file_path)
        
        # Render waveform
        waveform_data = io.BytesIO()
        render_waveform.render_waveform(file_path, waveform_data, WAVEFORM_BINS, WAVEFORM_DPI)
        with open(waveform_path, "wb") as f:
            f.write(waveform_data.getbuffer())

        # Result object
        result = {
            "filename": in_file["filename"],
            "file_path": file_path,
            "file_data": "data:" + mimetype + ";base64," + base64.b64encode(data).decode('utf-8'),
            "waveform_path": waveform_path,
            "waveform_data": "data:image/png;base64," + base64.b64encode(waveform_data.getvalue()).decode('utf-8')
        }

        return result

# * Create window
window = webview.create_window(
    title="STEMu",
    url=f"http://localhost:{args.port}" if args.dev else os.path.join(DIRNAME, 'frontend', 'dist', 'index.html'),
    width=400,
    height=625,
    resizable=False,
    frameless=True,
    easy_drag=False,
    js_api=JS_API(),
    confirm_close=True
)

def cleanup():
    print("Cleaning up session cache...")
    if os.path.exists(SESSION_CACHE_DIR):
        shutil.rmtree(SESSION_CACHE_DIR, ignore_errors=False)

if __name__ == "__main__":
    atexit.register(cleanup)
    webview.start(debug=args.dev or args.debug, http_server=True, private_mode=False)
    cleanup()