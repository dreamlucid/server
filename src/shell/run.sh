#!/bin/sh

# Use absolute paths so CEF (and the loader) see a proper executable path.
# CEF on Linux can segfault if argv[0] is relative (e.g. "bin/casparcg").
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_PATH="$SCRIPT_DIR/bin/casparcg"
LIB_PATH="$SCRIPT_DIR/lib"

RET=5

while [ $RET -eq 5 ]
do
  LD_LIBRARY_PATH="${LIB_PATH}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$BIN_PATH" "$@"
  RET=$?
done

