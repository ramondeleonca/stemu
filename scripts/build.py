import os
import subprocess as sp
import sys
from PyInstaller import __main__ as pyinstaller

def main():
    # Build frontend first
    # sp.run(args="npm run build", shell=True, cwd="frontend")

    import spleeter
    spleeter_resources_root_path = os.path.join(os.path.dirname(os.path.abspath(spleeter.__file__)), "resources")
    
    frontend_dist_path = os.path.abspath("frontend/dist")

    # Build distributable
    pyinstaller.run([
        '--name=STEMu',
        # '--onefile',
        # '--no-console',
        f'--add-data={frontend_dist_path}{os.pathsep}frontend/dist',
        f'--add-data={spleeter_resources_root_path}{os.pathsep}spleeter/resources',
        '-y',
        # '--icon=frontend/public/static/STEMuIcon.ico',
        'main.py'
    ])

if __name__ == "__main__":
    main()