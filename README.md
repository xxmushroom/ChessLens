# ChessLens - Desktop edition

A Python chess-analysis workspace combining board recognition, manual position review, legal move tracking and Stockfish analysis.

## For users of a finished Windows release
Extract the complete release ZIP and double-click **ChessLens.exe**. Keep the `_internal` and `stockfish` directories beside it. No Python installation, terminal commands or engine selection is required in a complete build.

## This download is the source + Windows builder
A compiled executable and Stockfish binary are not included in this source archive. The build must run once on a Windows computer. The editing environment was Linux and did not produce or test a Windows binary.

### Build once on your Windows computer
1. Extract this project into a new folder.
2. Copy your complete extracted Stockfish distribution inside **ChessLens/stockfish/**. Nested folders are supported. Keep its license, matching source reference and any network files. Use a CPU-compatible build; a universal/baseline build is preferable for sharing across PCs.
3. Ensure 64-bit Python 3.11 or newer is installed on the build computer. The builder uses your default Python; it does not demand Python 3.12 specifically.
4. Double-click **BUILD-WINDOWS.cmd**. Internet is required to install build dependencies and download the recognition model. This can take several minutes.
5. On success, open **dist/ChessLens/ChessLens.exe**. Share **dist/ChessLens-Windows.zip** with recipients.

The builder creates its own `.build-venv`, runs regression tests, packages Python and native dependencies with PyInstaller, bundles the recognition model, copies the complete stockfish folder and performs an executable smoke check. If any step fails, the build stops and shows the error. An older release ZIP, if present, is not evidence of a successful new build.

The executable smoke check loads the model, starts the engine and writes an analysis report. It does not test screen capture, mouse input, DPI, or visual layout. Try the actual app on Windows before distributing it, ideally also on a clean Windows machine without Python.

## Updated desktop workspace
- Forest-green styling, stronger typography and a focused board/analysis layout.
- **Analysis:** numbered capture workflow, quick side/orientation controls, board/capture tabs, best move and candidate lines.
- **Settings:** position rights, search time and optional engine override.
- **Practice:** verified automatic-play controls separate from analysis.
- Always-visible Stop control and status/progress footer.
- Automatic Stockfish discovery beside the script or frozen executable, independent of the current working directory.
- Reports and error logs in `%LOCALAPPDATA%/ChessLens`, suitable for a read-only installation directory.

## Using it
Select exactly the board's 64 squares. Set side to move, bottom color, castling rights and en-passant. Capture and compare the **Detected position** with **Original capture**. Click a detected square to fix a piece. Confirm and analyse. Open the interactive report to explore continuations.

A screenshot does not establish castling rights or previous move history. Default `-` means no castling rights; adjust when required. Recognition depends on the board theme. Keep the external board unobstructed and stationary when tracking.

## Source launch (developer alternative)
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe launcher.py
```

Source launches may download the model on first capture. Completed builds include it.

## Demo and post
Open **demo.html** for the interactive saved analysis example without installation. This is the HTML report, not a preview of the native desktop UI. See **LINKEDIN.md** for a post draft and recording outline.

## Validation
23 regression tests pass: existing practice-click/tracking tests, report playback tests and portable-path tests. Python source compiles successfully. Native Windows packaging, UI rendering, screen capture and live Stockfish execution were not available in the Linux editing environment.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Components
`launcher.py`: windowed entry point and startup diagnostics. `desktop_ui.py`: desktop layout. `app_paths.py`: portable discovery/model/report paths. `chess_screen.py`: capture and analysis state. `report_view.py`/`assets`: interactive report. `build_windows.py`: release build. `screen_player.py` and `screen_tracker.py`: verified practice/tracking logic.

See **USAGE.md** for detailed CLI options and practice behavior. See **THIRD-PARTY.md** before distributing the build. Use for local practice, post-game study or games that permit engine assistance.
