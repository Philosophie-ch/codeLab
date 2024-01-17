# Automouse

A simple Python script to record mouse and keyboard events and play them back.

This version is taken directly from [this article](https://www.shedloadofcode.com/blog/record-mouse-and-keyboard-for-automation-scripts-with-python).
Augmented a bit to allow for scrolling, and other minor changes.

**NOTE**: Works on Windows, Mac, and Linux Xorg, but doesn't work on Linux Wayland.


## Usage

Install the requirements.

Then, run in the following order:

```bash
python3 record.py  # To start recording
# Once you're finished with your task:
#  - Press 'ESC' to stop recording the keyboard
#  - Press and hold left-click for 3 seconds to stop recording the mouse
#  Both need to happen for the recording to stop
# A file called 'recording.json' will be created
python3 convert.py

# A file called 'play.py' will be created
python3 play.py  # To play the recording
```