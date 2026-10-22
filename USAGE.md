# ChessLens — detailed usage

## Screen capture mode (no image file needed)

Launch the new window from PowerShell in this folder:

```powershell
.\.venv\Scripts\python.exe chess_screen.py
```

Stockfish is detected automatically inside the stockfish folder beside the app. Settings also offers Detect and Browse for custom locations. Click **Select board area** and drag over exactly the 64 squares on your primary monitor. Set the current turn, color at the bottom, castling rights and en-passant target. The castling default `-` is only correct if neither side can castle.

Click **Capture / reset position**. Compare the captured board on the left with the detected pieces on the right. Click a detected square to correct a piece. Click **Confirm & analyse**, then enable **Auto update**. Enable **Auto play** and choose **Bot plays: white / black** to have the bot click the source and destination of its best move on your visible board. Auto play enables tracking and only plays the selected color. The window displays Stockfish's three candidate moves, evaluations, continuations and an arrow for the best move. **Open result** opens a larger local HTML view.

Tracking checks every quarter-second and waits for three matching captures before recognition. Stockfish runs for 3 seconds per changed position by default. It follows exactly one legal move between positions, preserving the move history after the initial capture. If a move is missed or recognition fails, automatic mode stops and clears suggestions. Capture the current board again, set the current turn and rights, review and confirm, then re-enable auto. Initial halfmove/fullmove counters are assumed to be 0/1; history before the initial capture is unavailable.

Keep the board visible, unobstructed, and at the same size and location. Keep the assistant window outside the selected area. After moving/resizing/flipping the board or starting another game, reselect the area and confirm again. This version requires selection of the board region; it does not search arbitrary screens for boards. Auto play uses two Windows mouse clicks on the centers of the chosen squares. Your chess app must support click-source / click-destination input. Keep the pointer and other windows away from the board during play. Use this for local practice or games that permit engine assistance. Screen captures remain local; only the chosen region is processed during monitoring. The temporary full primary-monitor screenshot used for region selection stays in memory. Captured board images appear in the local `screen_analysis.html` output.

The screen UI targets Windows with standard Python/Tkinter. Current automated checks use fake mouse input; Windows rendering, recognition and live engine integration require a first-run check on the target machine.

## New UI and automatic play

The screen window now uses a dark theme with separate capture and detected-board cards, a highlighted best move, readable candidate lines, move tracking, and a scrolling layout for shorter displays. The **Stop / Esc** button stays available while recognition or Stockfish is running.

1. Select exactly the 64 board squares on your primary monitor.
2. Set the current turn, orientation and move rights; capture and review every square.
3. Click **Confirm & analyse**.
4. Choose the bot's color, then enable **Auto play**. Leave the actual game board visible and outside the assistant window.
5. Hold **Escape** anywhere on Windows, or click **Stop / Esc**, to stop tracking and clicks. After an interrupted move, capture and confirm the actual board again.

The bot checks a stable screenshot against the analysed position before clicking, sends each move once, and verifies the result through recognition. It never advances the internal board merely because a click was sent. It can also recognize the expected move plus one immediate opponent reply. Unexpected positions or an unconfirmed move stop play without a blind retry. Unconfirmed clicks time out after roughly 12 seconds, excluding an in-progress recognition/search operation. Stop discards outstanding worker results.

Castling and en-passant use the ordinary legal move source and destination. Promotion pauses auto play by default while board tracking remains enabled: select the suggested piece manually. Check **Board auto-promotes to queen** only if your chess app is already configured to promote automatically; this app does not click promotion menus. Underpromotions always require manual selection.

Do not move, resize, flip or obscure the external board while auto play is enabled. There is no target-window detection; selection fixes the screen coordinates. Screen recognition can misread piece themes, so review the initial position carefully. Capture/reset, settings changes and piece corrections disarm auto play. The Windows click integration still requires a first-run check on your display; automated tests use a fake mouse and never operate a real desktop.

Run regression tests from this folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Image-file mode

Requires 64-bit Python 3.11 or newer (3.12 recommended), your extracted Stockfish executable, and a clear image of a **2D** chessboard. This version does not support photos of a physical 3D chess set. Images are processed locally. Installing packages and downloading the recognition model on the first run require internet. No API key is needed.

## Setup in PowerShell

Open PowerShell in this extracted folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If your Python version differs, replace `py -3.12` with the appropriate launcher command.

Crop the image to exactly the 64 squares, removing external coordinate labels, margins and surrounding UI. Save it as `board.png` in this folder. Keep the entire board visible without obstructing pieces.

## Run

Replace the Stockfish path below with the actual `.exe` you downloaded. Select an executable compatible with your CPU; keep accompanying Stockfish files in their extracted folder.

```powershell
.\.venv\Scripts\python.exe chess_image.py --image board.png --stockfish "C:\Stockfish\stockfish.exe" --turn white --orientation white --castling=- --seconds 10
```

- `--turn white` / `--turn black`: whose turn it is.
- `--orientation white` / `--orientation black`: which color is at the bottom of the image.
- `--castling=-`: no castling rights. **Only use this when neither player can still castle.** Use `--castling KQkq` when both sides retain both rights, or a subset such as `Kq`. K = White kingside; Q = White queenside; k = Black kingside; q = Black queenside. A king/rook standing on its starting square does not prove it has never moved.
- `--ep e3`: en-passant target if the immediately previous move permits it; default `-` means none. This depends on move history.
- `--halfmove 0 --fullmove 1`: supply actual counters when known. The halfmove counter can affect draw evaluation; defaults assume 0 and 1.
- `--top 3`: up to three candidate moves, default 3.
- `--seconds 30`: allow more search time.
- `--crop 100 200 900 1000`: crop to these pixel bounds before recognition.

The script opens a local HTML page showing the input and detected position side by side. Check **every square**. In PowerShell, type `ok` to analyse, or fix a piece with `e4 P`, `e4 p`, or `e4 .` (empty). Uppercase pieces are White, lowercase are Black: P pawn, N knight, B bishop, R rook, Q queen, K king. You can also enter `fen <complete FEN>` to replace the whole position, including turn and move rights.

The script rejects structurally invalid boards. A valid board can still have misidentified pieces, so visual review is always required. Recognition depends on the board/piece theme and is not guaranteed for every image.

After analysis, `chess_analysis.html` highlights the best move with an arrow and lists candidate moves, evaluations, and likely continuations against strong replies. Positive scores favor the side to move. These are search estimates, not guaranteed outcomes. Promotion appears in notation such as `e8=Q`.

To analyse an already-known FEN:

```powershell
.\.venv\Scripts\python.exe chess_image.py --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" --stockfish "C:\Stockfish\stockfish.exe"
```

A single image or FEN does not provide repetition history. For exact game-history-dependent draw analysis, use the full game's moves instead.

Sources: https://pypi.org/project/chessvision/ and https://python-chess.readthedocs.io/en/stable/engine.html
