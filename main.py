# Imports
import librosa
import spleeter
import spleeter.model
import spleeter.resources
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
from enum import Enum
from model_providers.github import GithubModelProvider

# TODO: Warn if no models

# * Types
class SpleeterModel(str, Enum):
    TWO_STEMS = "2stems"
    # TWO_STEMS_FINETUNE = "2stems-finetune"
    FOUR_STEMS = "4stems"
    # FOUR_STEMS_FINETUNE = "4stems-finetune"
    FIVE_STEMS = "5stems"
    # FIVE_STEMS_FINETUNE = "5stems-finetune"
spleeter_models: list[SpleeterModel] = [s.value for s in SpleeterModel]

# * Constants
APPNAME = "STEMu"
FROZEN = getattr(sys, 'frozen', False)
DIRNAME = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
WAVEFORM_BINS = 300
WAVEFORM_DPI = 20

# * Dirs
APP_DATA_DIR = platformdirs.user_data_dir(APPNAME, appauthor=False, roaming=True)
if not os.path.exists(APP_DATA_DIR):
    os.makedirs(APP_DATA_DIR, exist_ok=True)

# Session cache
# Delete past session cache dirs
for item in os.listdir(APP_DATA_DIR):
    item_path = os.path.join(APP_DATA_DIR, item)
    if os.path.isdir(item_path) and item.startswith("session_"):
        shutil.rmtree(item_path, ignore_errors=True)

SESSION_CACHE_DIR = os.path.join(APP_DATA_DIR, "session_" + uuid.uuid4().hex)
if not os.path.exists(SESSION_CACHE_DIR):
    os.makedirs(SESSION_CACHE_DIR, exist_ok=False)

# Models dir
MODELS_DIR = os.path.join(APP_DATA_DIR, "models")
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR, exist_ok=True)

# * Model provider
model_provider = GithubModelProvider(
    GithubModelProvider.DEFAULT_HOST,
    GithubModelProvider.DEFAULT_REPOSITORY,
    GithubModelProvider.LATEST_RELEASE
)

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

processed_files = []
class JS_API():
    def close(self, *args):
        window.destroy()
        exit()

    def checkModels(self, *args):
        models = {}
        for model in spleeter_models:
            model_path = os.path.join(MODELS_DIR, model)
            models[model] = os.path.exists(model_path)
        return models
    
    def downloadModel(self, model: SpleeterModel, *args):
        if model not in spleeter_models:
            raise ValueError("Invalid model: " + model)
        
        # Respond as soon as possible to show progress
        window.evaluate_js(f'window["setModelDownloadProgress"]("{model}", 0.01)')
        
        # Download model
        def progress_callback(progress: float, total: int, downloaded: int):
            print(f"Model {model} download progress: {progress*100:.2f}%, {downloaded}/{total} bytes")
            window.evaluate_js(f'window["setModelDownloadProgress"]("{model}", {progress})')

        model_provider.download(model, os.path.join(MODELS_DIR, model), progress_callback)
        window.evaluate_js('window["checkModels"]()')

    def addFile(self, in_file, *args):
        # TODO: Threads or multiprocessing
        # Debug prints
        print("Received file:", in_file["filename"] + ", size:", len(in_file["data"]), "bytes")
        print(in_file["data"][:30])

        # Check if file already processed
        for pf in processed_files:
            if pf["filename"] == in_file["filename"] and pf["data"] == in_file["data"]:
                print("File already processed, returning cached result.")
                return pf["result"]

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