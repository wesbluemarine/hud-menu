#!/bin/bash

APP="$1"

# Check if the window is already open
if wmctrl -lx | grep -i "$APP" >/dev/null; then
    # Raise the window to the foreground
    wmctrl -xa "$APP"
else
    # Otherwise, launch the program
    "$APP" &
fi
