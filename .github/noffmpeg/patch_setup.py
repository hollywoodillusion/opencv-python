"""Drop the bundled FFmpeg DLL from setup.py's required CMake outputs.

On Windows, setup.py at tag 93 requires bin/opencv_videoio_ffmpeg*.dll and fails packaging
with "Not found" when FFmpeg is disabled. The working tree is patched only (no commit), so
`git describe --tags` still yields the release version.
"""
import sys

path = sys.argv[1]
src = open(path, encoding="utf-8").read()
old = '''            [r"bin/opencv_videoio_ffmpeg\\d{3}%s\\.dll" % ("_64" if is64 else "")]
            if os.name == "nt"
            else []
'''
if old not in src:
    sys.exit("patch_setup.py: FFmpeg DLL entry not found in %s" % path)
open(path, "w", encoding="utf-8", newline="\n").write(src.replace(old, "            []\n"))
print("patch_setup.py: removed opencv_videoio_ffmpeg DLL from required outputs")
