"""Re-render the saved analysis supplied with this project; no engine required."""
from pathlib import Path
import chess
import chess.engine
from report_view import render_report
board = chess.Board('5r2/Q6p/2R4b/3kp1p1/4p3/4BP1P/1PP2P2/4K2R w - - 0 5')
lines = []
for san, mate in [('Qc5#', 1), ('Qd7#', 1), ('Qa4 exf3 Qc4#', 2)]:
    position = board.copy()
    pv = []
    for token in san.split():
        move = position.parse_san(token)
        pv.append(move)
        position.push(move)
    lines.append({'pv':pv,'score':chess.engine.PovScore(chess.engine.Mate(mate),chess.WHITE)})
render_report(board, Path(__file__).parent/'demo.html', lines=lines, open_browser=False)
print('Open demo.html. This is a saved analysis example, not a live engine session.')
