"""Verification for the no-FFmpeg opencv-python-headless wheels.

  verify.py zip <wheel>          check the wheel contents for FFmpeg/x264/x265/Qt/GStreamer
  verify.py runtime <linux|mac|windows>  run inside a clean venv with the wheel installed
"""
import os
import re
import sys
import tempfile
import zipfile

FORBIDDEN = re.compile(r"ffmpeg|avcodec|avformat|avutil|avdevice|avfilter|swscale|swresample|postproc"
                       r"|x264|x265|qt|gstreamer|gst", re.I)


def check_zip(wheel):
    names = zipfile.ZipFile(wheel).namelist()
    print("Wheel:", os.path.basename(wheel))
    print("Bundled native libraries:")
    for n in names:
        if re.search(r"\.(so|dylib|dll|pyd)(\.|$)", n, re.I):
            print("   ", n)
    bad = [n for n in names if FORBIDDEN.search(n)]
    if bad:
        print("FORBIDDEN FILES FOUND:\n  " + "\n  ".join(bad))
        print("::error::forbidden files in wheel: " + ", ".join(bad))
        return 1
    print("Forbidden-file check: OK (no ffmpeg/avcodec/avformat/x264/x265/qt/gstreamer)")
    return 0


def section_value(info, key):
    m = re.search(r"^\s*%s:\s*(.*)$" % re.escape(key), info, re.M)
    return m.group(1).strip() if m else None


def check_runtime(plat):
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    import numpy as np
    import cv2

    info = cv2.getBuildInformation()
    print(info)
    print("cv2", cv2.__version__, "from", cv2.__file__)
    errors = []

    def fail(msg):
        errors.append(msg)
        print("::error::%s: %s" % (plat, msg))  # annotation, readable without log access

    ffmpeg = section_value(info, "FFMPEG")
    gst = section_value(info, "GStreamer")
    gui = section_value(info, "GUI")
    exr = section_value(info, "OpenEXR")
    print("FFMPEG:", ffmpeg, "| GStreamer:", gst, "| GUI:", gui, "| OpenEXR:", exr)

    if ffmpeg is not None and not ffmpeg.upper().startswith("NO"):
        fail("FFMPEG enabled: %s" % ffmpeg)
    if gst is not None and not gst.upper().startswith("NO"):
        fail("GStreamer enabled: %s" % gst)
    for name, cap in (("FFMPEG", cv2.CAP_FFMPEG), ("GSTREAMER", cv2.CAP_GSTREAMER)):
        if cv2.videoio_registry.isBackendBuiltIn(cap):
            fail("%s video backend is built in" % name)
        # A plugin backend could only load an external opencv_videoio_ffmpeg library, never shipped here
        print("%s: built-in=%s available=%s" % (name, cv2.videoio_registry.isBackendBuiltIn(cap),
                                                cv2.videoio_registry.hasBackend(cap)))
    if not exr or exr.upper().startswith("NO"):
        fail("OpenEXR not enabled: %s" % exr)
    # macOS always builds the Cocoa backend (OpenCVFindLibsGUI.cmake), Apple system framework
    if plat != "mac" and (gui or "").upper() != "NONE":
        fail("GUI is not NONE: %s" % gui)
    print("Video I/O backends:", [cv2.videoio_registry.getBackendName(b)
                                  for b in cv2.videoio_registry.getBackends()])

    tmp = tempfile.mkdtemp()
    rng = np.random.default_rng(0)

    def roundtrip(name, img, ext, params=(), exact=True):
        p = os.path.join(tmp, name + ext)
        try:
            if not cv2.imwrite(p, img, list(params)):
                return fail("%s: imwrite returned False" % name)
            back = cv2.imread(p, cv2.IMREAD_UNCHANGED)
            if back is None or back.dtype != img.dtype or back.shape != img.shape:
                return fail("%s: read back %s" % (name, None if back is None else (back.dtype, back.shape)))
            if exact and not np.array_equal(back, img):
                return fail("%s: pixel mismatch" % name)
            print("%s: OK" % name)
        except Exception as e:
            fail("%s: %s" % (name, str(e).strip().splitlines()[-1]))

    roundtrip("png16_rgba", rng.integers(0, 65535, (64, 80, 4), dtype=np.uint16), ".png")
    rgb8 = rng.integers(0, 255, (64, 80, 3), dtype=np.uint8)
    roundtrip("png8_rgb", rgb8, ".png")
    roundtrip("jpeg8_rgb", rgb8, ".jpg", [cv2.IMWRITE_JPEG_QUALITY, 95], exact=False)
    roundtrip("exr_f32_3ch", rng.random((32, 48, 3), dtype=np.float32) * 4.0, ".exr")
    roundtrip("exr_f32_4ch", rng.random((32, 48, 4), dtype=np.float32) * 4.0, ".exr")

    try:
        img = cv2.resize(rgb8, (40, 32), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [39, 0], [39, 31], [0, 31]]),
                                        np.float32([[2, 1], [37, 3], [38, 30], [1, 29]]))
        cv2.warpPerspective(img, M, (40, 32))
        _, bw = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        cv2.morphologyEx(bw, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
        cv2.distanceTransform(bw, cv2.DIST_L2, 5)
        cv2.connectedComponentsWithStats(bw)
        print("Image ops: OK (resize, cvtColor, warpPerspective, morphology, distanceTransform,"
              " connectedComponents)")
    except Exception as e:
        fail("image ops: %s" % str(e).strip().splitlines()[-1])

    if errors:
        print("VERIFICATION FAILED:\n  " + "\n  ".join(errors))
        return 1
    print("VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    mode, arg = sys.argv[1], sys.argv[2]
    sys.exit(check_zip(arg) if mode == "zip" else check_runtime(arg))
