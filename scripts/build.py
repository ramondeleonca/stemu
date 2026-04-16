import os
import subprocess as sp
import sys
from PyInstaller import __main__ as pyinstaller


def _write_runtime_hook(hooks_dir: str) -> str:
    os.makedirs(hooks_dir, exist_ok=True)
    hook_path = os.path.join(hooks_dir, "strip_multiprocessing_args.py")
    hook_source = """import sys


def _strip_multiprocessing_args(argv):
    cleaned = []
    for arg in argv:
        if arg.startswith("--multiprocessing-fork"):
            continue
        if arg.startswith("parent_pid="):
            continue
        if arg.startswith("pipe_handle="):
            continue
        cleaned.append(arg)
    argv[:] = cleaned


_strip_multiprocessing_args(sys.argv)
"""
    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(hook_source)
    return hook_path

def main():
    # Build frontend first
    # sp.run(args="npm run build", shell=True, cwd="frontend")

    import spleeter
    spleeter_resources_root_path = os.path.join(os.path.dirname(os.path.abspath(spleeter.__file__)), "resources")
    runtime_hooks_dir = os.path.abspath(os.path.join("scripts", "_pyinstaller_runtime_hooks"))
    strip_mp_args_hook = _write_runtime_hook(runtime_hooks_dir)
    
    frontend_dist_path = os.path.abspath("frontend/dist")

    # Build distributable
    pyinstaller.run([
        '--name=STEMu',
        # '--onefile',
        # '--no-console',
        f'--add-data={frontend_dist_path}{os.pathsep}frontend/dist',
        f'--add-data={spleeter_resources_root_path}{os.pathsep}spleeter/resources',
        '--collect-submodules=spleeter.model.functions',
        # f'--runtime-hook={strip_mp_args_hook}',
        '-y',
        # '--icon=frontend/public/static/STEMuIcon.ico',
        'main.py'
    ])

if __name__ == "__main__":
    main()