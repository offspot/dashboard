#!/bin/sh
set -e

VENV=/usr/local/bin/gen-home_env

# refresh ZIM packages collection (maybe)
$VENV/bin/python3 $VENV/lib/refresh-zims.cpython-312.pyc

# generate homepage from collection
$VENV/bin/python3 $VENV/lib/gen-home.cpython-312.pyc

touch /tmp/.ready

exec "$@"
