# Image Recognition Macro

<!-- Image Recognition Macro v0.2.0 -->

Windows-first image recognition macro tool.

## MVP

- Select a template image.
- Capture the current Windows screen.
- Search the whole screen with OpenCV template matching.
- Report the best match, confidence, and center coordinates.
- Click the detected location.
- Run repeated detection/click loops.
- Stop safely with the Stop button or F8.

## Setup

1. Install Python 3.11+.
2. Open Command Prompt in this folder.
3. Run:
   `pip install -r requirements.txt`
4. Run `run.bat` or `python main.py`.

The first version intentionally keeps the UI simple so the recognition engine can be tested before the macro editor is expanded.
