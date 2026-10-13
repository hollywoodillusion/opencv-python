#!/usr/bin/env bash
# OpenCV 5 no longer bundles OpenEXR (opencv commit b96e9fd1ce "imgcodecs: drop bundled OpenEXR")
# and only picks it up via find_package(OpenEXR 3). Build a static OpenEXR 3 (BSD-3-Clause)
# with its internal Imath and libdeflate, and install it into the prefix given as $1.
set -euo pipefail
PREFIX=$1
VERSION=${OPENEXR_VERSION:-3.3.14}
WORK=${RUNNER_TEMP:-/tmp}/openexr-build

EXTRA=""
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*) EXTRA="-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded" ;;  # OpenCV static build uses /MT
esac

rm -rf "$WORK"
git clone --depth 1 --branch "v$VERSION" https://github.com/AcademySoftwareFoundation/openexr.git "$WORK/src"
cmake -S "$WORK/src" -B "$WORK/build" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_TESTING=OFF \
  -DOPENEXR_BUILD_TOOLS=OFF \
  -DOPENEXR_INSTALL_TOOLS=OFF \
  -DOPENEXR_BUILD_EXAMPLES=OFF \
  -DOPENEXR_INSTALL_EXAMPLES=OFF \
  -DOPENEXR_BUILD_DOCS=OFF \
  -DOPENEXR_FORCE_INTERNAL_IMATH=ON \
  -DOPENEXR_FORCE_INTERNAL_DEFLATE=ON \
  $EXTRA
cmake --build "$WORK/build" --config Release --parallel 4
cmake --install "$WORK/build" --config Release
ls "$PREFIX/lib" "$PREFIX/lib/cmake"
