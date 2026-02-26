# Imports
import librosa
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
import spleeter
from enum import Enum
from model_providers.github import GithubModelProvider
from io import BytesIO
import json
import time

# * Types
class SpleeterModel(str, Enum):
    TWO_STEMS = "2stems"
    FOUR_STEMS = "4stems"
    FIVE_STEMS = "5stems"
spleeter_models: list[SpleeterModel] = [s.value for s in SpleeterModel]

# Get available devices for tensorflow
# devices = tf.config.list_physical_devices()
# print(f"Available devices ({len(devices)}):")
# for device in devices:
#     print(f" - {device.device_type}: {device.name}")

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

# Output path
DEFAULT_OUTPUT_PATH = os.path.join(platformdirs.user_music_dir(), "STEMu Output")
if not os.path.exists(DEFAULT_OUTPUT_PATH):
    os.makedirs(DEFAULT_OUTPUT_PATH, exist_ok=True)
output_path = DEFAULT_OUTPUT_PATH

# * Model provider
model_provider = GithubModelProvider(
    GithubModelProvider.DEFAULT_HOST,
    GithubModelProvider.DEFAULT_REPOSITORY,
    GithubModelProvider.LATEST_RELEASE
)

# * Spleeter separator
spleeter_resources_root_path = os.path.join(os.path.dirname(os.path.abspath(spleeter.__file__)), "resources")

spleeter_2stems_model_config_path = os.path.join(spleeter_resources_root_path, "2stems.json")
stemu_2stems_model = os.path.join(MODELS_DIR, "2stems", "5stems.json")
with open(spleeter_2stems_model_config_path, "r") as f:
    m_json = json.load(f)
    m_json["model_dir"] = os.path.join(MODELS_DIR, "2stems")
    with open(stemu_2stems_model, "w") as f:
        f.write(json.dumps(m_json))

spleeter_4stems_model_config_path = os.path.join(spleeter_resources_root_path, "4stems.json")
stemu_4stems_model = os.path.join(MODELS_DIR, "4stems", "5stems.json")
with open(spleeter_4stems_model_config_path, "r") as f:
    m_json = json.load(f)
    m_json["model_dir"] = os.path.join(MODELS_DIR, "4stems")
    with open(stemu_4stems_model, "w") as f:
        f.write(json.dumps(m_json))

spleeter_5stems_model_config_path = os.path.join(spleeter_resources_root_path, "5stems.json")
stemu_5stems_model = os.path.join(MODELS_DIR, "5stems", "5stems.json")
with open(spleeter_5stems_model_config_path, "r") as f:
    m_json = json.load(f)
    m_json["model_dir"] = os.path.join(MODELS_DIR, "5stems")
    with open(stemu_5stems_model, "w") as f:
        f.write(json.dumps(m_json))

# Import spleeter after
import spleeter
import spleeter.separator

# Create separators for each model with multiprocessing enabled
# TODO: WTF THIS CONSUMES SO MUCH RAM, HOW TF DO WE OPTIMIZE THIS? maybe we can create the separator on demand and then cache it for future use?
# separator_2stems = spleeter.separator.Separator("spleeter:2stems", multiprocess=True)
# separator_4stems = spleeter.separator.Separator("spleeter:4stems", multiprocess=True)
# separator_5stems = spleeter.separator.Separator("spleeter:5stems", multiprocess=True)

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

session_processed_files = [] # List of ALL processed files in current session
session_current_file_descriptors = [] # List of processed files currently selected in the session
class JS_API():
    def separate(self, filename, *args):
        pass

    def chooseOutputDirectory(self, *args):
        global output_path
        chosen = window.create_file_dialog(webview.FileDialog.FOLDER, directory=output_path)
        print("Chosen output directory:", chosen)
        if chosen:
            output_path = chosen[0]
        return output_path

    def getOutputDirectory(self, *args):
        return output_path
    
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

    def removeFile(self, filename, *args):
        global session_current_file_descriptors, session_processed_files
        session_current_file_descriptors = [fd for fd in session_current_file_descriptors if fd["filename"] != filename]
        # Optionally also remove from processed files cache if you want to free up memory but kept for cache reasons
        # session_processed_files = [pf for pf in session_processed_files if pf["filename"] != filename]
        return [fd["filename"] for fd in session_current_file_descriptors]

    def addFile(self, in_file, *args):
        global session_current_file_descriptors, session_processed_files
        # TODO: Threads or multiprocessing
        # Debug prints
        print("Received file:", in_file["filename"] + ", size:", len(in_file["data"]), "bytes")
        print(in_file["data"][:30])

        # TODO: change cached file logic
        # Check if file already processed
        for pf in session_processed_files:
            if pf["filename"] == in_file["filename"] and pf["data"] == in_file["data"]:
                print("File already processed, returning cached result.")
                return pf["result"]

        # Decode data
        [header, b64data] = in_file["data"].split(",", 1)
        data = base64.b64decode(b64data)

        # If file not in current session file descriptors, add it
        descriptor = { "filename": in_file["filename"], "data": data }
        if not any(fd["filename"] == in_file["filename"] and fd["data"] == in_file["data"] for fd in session_current_file_descriptors):
            session_current_file_descriptors.append(descriptor)

        # File paths
        file_path = os.path.join(SESSION_CACHE_DIR, in_file["filename"])
        waveform_path = file_path + "_waveform.png"
        
        # Save original file
        # TODO: no need to save the file to disk, can we just render the waveform and separate directly from memory?
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
            # TODO: no need to re-encode data and much less to return the same data back to the frontend
            # but wtv
            "file_data": "data:" + mimetype + ";base64," + base64.b64encode(data).decode('utf-8'),
            "waveform_path": waveform_path,
            "waveform_data": "data:image/png;base64," + base64.b64encode(waveform_data.getvalue()).decode('utf-8')
        }

        return result

    # TODO: add option for individual folders
    # TODO: Maybe use a separate process so it doesnt slow down the ui
    def startSeparation(self, file_descriptors: list[dict], *args):
        # Filter 2stems, 4stems and 5stems files to separate lists
        model_2stems_files = [fd for fd in file_descriptors if fd["model"] == "2stems"]
        model_4stems_files = [fd for fd in file_descriptors if fd["model"] == "4stems"]
        model_5stems_files = [fd for fd in file_descriptors if fd["model"] == "5stems"]

        print("Starting separation with file descriptors:", file_descriptors)
        print("Destination output path:", output_path)

        # Separate files for each model
        if len(model_2stems_files) > 0:
            print("Separating 2stems files:", [fd["filename"] for fd in model_2stems_files])
            print("Loading 2stems model")
            separator_2stems = spleeter.separator.Separator(stemu_2stems_model, multiprocess=True)
            for fd in model_2stems_files:
                print("Separating file:", fd["filename"])
                separator_2stems.separate_to_file(os.path.join(SESSION_CACHE_DIR, fd["filename"]), output_path, synchronous=False)
                time.sleep(0.25) # Sleep to avoid overwhelming the system, can be optimized with a proper queue and worker system
            separator_2stems.join() # Wait for all separations to finish before starting next model to avoid overwhelming the system
            # delete separator to free up memory
            del separator_2stems

        if len(model_4stems_files) > 0:
            print("Separating 4stems files:", [fd["filename"] for fd in model_4stems_files])
            print("Loading 4stems model")
            separator_4stems = spleeter.separator.Separator(stemu_4stems_model, multiprocess=True)
            for fd in model_4stems_files:
                print("Separating file:", fd["filename"])
                separator_4stems.separate_to_file(os.path.join(SESSION_CACHE_DIR, fd["filename"]), output_path, synchronous=False)
                time.sleep(0.25)
            separator_4stems.join() # Wait for all separations to finish before starting next model to avoid overwhelming the system
            # delete separator to free up memory
            del separator_4stems
        
        if len(model_5stems_files) > 0:
            print("Separating 5stems files:", [fd["filename"] for fd in model_5stems_files])
            print("Loading 5stems model")
            separator_5stems = spleeter.separator.Separator(stemu_5stems_model, multiprocess=True)
            for fd in model_5stems_files:
                print("Separating file:", fd["filename"])
                separator_5stems.separate_to_file(os.path.join(SESSION_CACHE_DIR, fd["filename"]), output_path, synchronous=False)
                time.sleep(0.25)
            separator_5stems.join() # Wait for all separations to finish
            # delete separator to free up memory
            del separator_5stems

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

if __name__ == "__main__":
    webview.start(debug=args.dev or args.debug, http_server=True, private_mode=False)