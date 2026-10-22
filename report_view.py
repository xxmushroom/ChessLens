"""Self-contained analysis reports with legal principal-variation playback."""
import base64
import html
import json
from pathlib import Path
import webbrowser
import chess
import chess.engine
import chess.svg


def score_label(score, color):
    value = score.pov(color)
    if value.is_mate():
        moves = value.mate()
        return 'Checkmate' if moves == 0 else (f'Mate in {moves}' if moves > 0 else f'Opponent mate in {abs(moves)}')
    cp = value.score()
    return 'Unavailable' if cp is None else f'{cp / 100:+.2f}'


def render_report(board, destination, image_data=None, lines=None, orientation='white', open_browser=True):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    colors = {'square light':'#edf0df','square dark':'#8da991','margin':'#ffffff','coord dark':'#63776b','coord light':'#63776b','arrow green':'#d4b848dd'}
    def frame(position, move=None):
        arrows = [chess.svg.Arrow(move.from_square, move.to_square)] if move else []
        return [chess.svg.board(position, size=560, orientation=color, arrows=arrows, colors=colors) for color in (chess.WHITE, chess.BLACK)]
    candidates = []
    for info in lines or []:
        pv = info.get('pv', [])[:12]
        if not pv:
            continue
        position = board.copy()
        frames = [frame(position, pv[0])]
        for move in pv:
            if move not in position.legal_moves:
                raise ValueError('Analysis continuation contains an illegal move.')
            position.push(move)
            frames.append(frame(position))
        candidates.append({'move':board.san(pv[0]),'score':score_label(info['score'], board.turn), 'san':board.variation_san(pv), 'depth':info.get('depth'), 'frames':frames})
    esc = html.escape
    best = candidates[0] if candidates else None
    rows = ''.join(f'<button class="candidate{ " active" if i == 0 else ""}" data-index="{i}" aria-pressed="{str(i == 0).lower()}"><span class="candidate-top"><span><span class="rank">0{i+1}</span><strong>{esc(c["move"])}</strong></span><span>{esc(c["score"])}</span></span><small>{esc(c["san"])}</small></button>' for i,c in enumerate(candidates))
    fen = board.fen(en_passant='fen')
    source = f'<details class="source"><summary>Compare with original capture</summary><img alt="Original captured chessboard" src="data:image/png;base64,{image_data}"></details>' if image_data else ''
    outcome = board.outcome()
    subtitle = 'Position complete' if outcome else ('Your next move, in focus.' if best else 'A clearer view of the board.')
    explanation = 'Review each piece before returning to the app to confirm and analyse.' if not best else 'Explore candidate moves and step through each continuation.'
    payload = json.dumps({'candidates':candidates,'initial':frame(board),'orientation':int(orientation == 'black')}).replace('<','\\u003c')
    css = (Path(__file__).parent/'assets'/'report.css').read_text(encoding='utf-8')
    script = (Path(__file__).parent/'assets'/'report.js').read_text(encoding='utf-8')
    content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ChessLens · Position analysis</title><style>{css}</style></head><body>
<header><div class="brand">♞ Chess<span>Lens</span></div><span class="tag live">Local chess analysis</span></header><main>
<div class="intro"><div><div class="tag">THE ANALYSIS WORKSPACE</div><h1>{subtitle}</h1><p>{explanation}</p></div><button id="flip">Flip board ↻</button></div>
<div class="workspace"><section class="board-card" aria-label="Chessboard"><div class="card-top"><span class="tag">Detected position</span><span>{'White' if board.turn else 'Black'} to move</span></div><div id="board"></div><div class="board-foot"><span id="step" aria-live="polite">Starting position</span><div class="controls"><button id="reset" aria-label="Reset variation">↺</button><button id="prev" aria-label="Previous move">←</button><button id="next" aria-label="Next move">→</button></div></div></section>
<aside class="panel"><div class="hero"><div class="tag">{'ENGINE TOP CHOICE' if best else 'POSITION REVIEW'}</div><div class="move-row"><span class="best">{esc(best['move']) if best else 'Ready?'}</span><span class="evaluation">{esc(best['score']) if best else 'Review'}</span></div><p>{'Stockfish analysis · score from the side to move' if best else 'Capture → Review → Analyse'}</p></div><div class="panel-body"><div class="section-title"><span class="tag">Candidate moves</span><span class="tag">{len(candidates):02d} LINES</span></div>{rows or '<p class="empty">No engine lines yet. Confirm the detected board in the app to begin.</p>'}<p class="note">Select a line, then use the arrows below the board to explore it. Scores are search estimates, not guaranteed outcomes.</p>{source}</div></aside></div>
<div class="position"><span class="tag">POSITION / FEN</span><code id="fen">{esc(fen)}</code><button id="copy">Copy FEN</button></div><footer><span>ChessLens · Python / Computer vision / Stockfish</span><span>Local practice & post-game study · Single images do not include repetition history</span></footer></main><script type="application/json" id="data">{payload}</script><script>{script}</script></body></html>'''
    destination.write_text(content, encoding='utf-8')
    if open_browser:
        webbrowser.open(destination.as_uri())
