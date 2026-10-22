"""Read a cropped 2D chessboard locally, review it, then analyse with Stockfish."""
import argparse
import base64
import html
import os
from pathlib import Path
import sys
import webbrowser

import chess
import chess.engine
import chess.svg


def positive_float(value):
    result = float(value)
    if not 0 < result < float('inf'):
        raise argparse.ArgumentTypeError('Must be a finite positive number.')
    return result


from report_view import render_report


def describe_score(score, color):
    relative = score.pov(color)
    if relative.is_mate():
        mate = relative.mate()
        return 'Checkmate' if mate == 0 else f'Mate in {mate}' if mate > 0 else f'Opponent has mate in {abs(mate)}'
    return f'{relative.score() / 100:+.2f} pawns for the side to move'


def review(board, args, image_data, report):
    while True:
        render_report(board, report, image_data, orientation=args.orientation,
                      open_browser=not args.no_browser)
        print('\nReview:', report)
        print('FEN:', board.fen(en_passant='fen'))
        if not board.is_valid():
            print('INVALID POSITION: status', board.status(), '(correct it before analysis).')
        print('Compare every piece with the image. Validity alone does not prove correct recognition.')
        print('Enter "ok", "quit", "e4 P" (white pawn), "e4 p" (black pawn),')
        print('"e4 ." (empty), or "fen <complete FEN>" to replace the position.')
        command = input('> ').strip()
        if command.lower() == 'quit':
            raise KeyboardInterrupt
        if command.lower() == 'ok':
            if board.is_valid():
                return board
            print('Please fix the invalid position first.')
            continue
        try:
            if command.startswith('fen '):
                board = chess.Board(command[4:].strip())
            else:
                square, symbol = command.split()
                board.set_piece_at(chess.parse_square(square),
                                   None if symbol == '.' else chess.Piece.from_symbol(symbol))
        except ValueError as exc:
            print('Could not apply correction:', exc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--image', type=Path, help='PNG/JPG cropped to the 64 squares of a 2D board.')
    source.add_argument('--fen', help='Use an existing complete FEN instead of recognizing an image.')
    parser.add_argument('--stockfish', required=True, type=Path, help='Path to your Stockfish executable.')
    parser.add_argument('--turn', choices=['white', 'black'], help='Required with --image.')
    parser.add_argument('--orientation', choices=['white', 'black'], default='white', help='Color at the bottom of the image.')
    parser.add_argument('--castling', help='Required with --image: KQkq, a subset, or - for no rights.')
    parser.add_argument('--ep', default='-', help='En-passant target square, such as e3; default none.')
    parser.add_argument('--halfmove', type=int, default=0, help='Halfmove clock (default 0).')
    parser.add_argument('--fullmove', type=int, default=1, help='Move number (default 1).')
    parser.add_argument('--seconds', type=positive_float, default=5.0, help='Total analysis time, default 5 seconds.')
    parser.add_argument('--top', type=int, choices=range(1, 6), default=3, help='Number of candidate moves, 1–5.')
    parser.add_argument('--crop', type=int, nargs=4, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'), help='Crop an image to board pixel bounds first.')
    parser.add_argument('--output', type=Path, default=Path('chess_analysis.html'))
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not args.stockfish.is_file():
        parser.error('--stockfish must point to the extracted executable, not a ZIP or folder.')
    if args.halfmove < 0 or args.fullmove < 1:
        parser.error('Halfmove must be >= 0 and fullmove must be >= 1.')
    image_data = None
    if args.image:
        if args.turn is None or args.castling is None:
            parser.error('--image requires explicit --turn and --castling; these cannot be inferred reliably from pixels.')
        if args.castling != '-' and (not args.castling or any(c not in 'KQkq' for c in args.castling) or len(set(args.castling)) != len(args.castling)):
            parser.error('--castling must be - or a subset of KQkq without duplicates.')
        from io import BytesIO
        from PIL import Image, ImageOps
        from chessvision import BoardPredictor, Orientation, Turn
        with Image.open(args.image) as original:
            image = ImageOps.exif_transpose(original).convert('RGB')
        if args.crop:
            left, top, right, bottom = args.crop
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                parser.error('--crop bounds must lie inside the input image.')
            image = image.crop(tuple(args.crop))
        if abs(image.width - image.height) > max(image.size) * 0.02:
            parser.error('Crop to a square showing exactly the 8x8 board. Remove surrounding UI, borders and coordinates.')
        image = image.resize((800, 800))
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('ascii')
        print('Reading board locally (first run downloads the recognition model)...')
        prediction = BoardPredictor().predict(image, orientation=Orientation(args.orientation),
                                              turn=Turn(args.turn), castling=args.castling)
        placement = prediction.fen.split()[0]
        active = 'w' if args.turn == 'white' else 'b'
        board = chess.Board(f'{placement} {active} {args.castling} {args.ep} {args.halfmove} {args.fullmove}')
        print(f'Classifier mean confidence: {prediction.confidence:.1%} (not a guarantee of correctness).')
    else:
        board = chess.Board(args.fen)
    report = args.output.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    board = review(board, args, image_data, report)
    outcome = board.outcome(claim_draw=False)
    if outcome is not None:
        print('Game already ended:', outcome.termination.name, outcome.result())
        return 0
    print(f'Analysing for {args.seconds:g} seconds...')
    with chess.engine.SimpleEngine.popen_uci(str(args.stockfish.resolve()), timeout=30) as engine:
        options = {}
        if 'Threads' in engine.options:
            options['Threads'] = min(4, max(1, (os.cpu_count() or 2) - 1))
        if 'Hash' in engine.options:
            options['Hash'] = 128
        if 'UCI_LimitStrength' in engine.options:
            options['UCI_LimitStrength'] = False
        if 'Skill Level' in engine.options:
            options['Skill Level'] = engine.options['Skill Level'].max
        engine.configure(options)
        lines = engine.analyse(board, chess.engine.Limit(time=args.seconds), multipv=args.top)
    for index, info in enumerate(lines, 1):
        pv = info.get('pv', [])
        if not pv:
            continue
        move = pv[0]
        print(f'\n{index}. {board.san(move)} ({chess.square_name(move.from_square)} -> {chess.square_name(move.to_square)})')
        print('Evaluation:', describe_score(info['score'], board.turn))
        print('Continuation:', board.variation_san(pv[:12]))
        print('Search depth:', info.get('depth', '?'))
    render_report(board, report, image_data, lines, args.orientation, not args.no_browser)
    print('\nResult:', report)
    print('A finite search does not guarantee a win. Repetition history is unavailable from a single image/FEN.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.')
        sys.exit(130)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        print('Check your image, installed packages and Stockfish executable. First-run model download needs internet.', file=sys.stderr)
        sys.exit(1)
