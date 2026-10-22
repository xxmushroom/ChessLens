import sys
import types
import unittest
import queue
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import chess
from PIL import Image
from screen_player import square_center, verify_played_position
from screen_tracker import advance_position
# Recognition is injected so these tests never download a model or click a desktop.
try:
    import chessvision
except ImportError:
    sys.modules['chessvision'] = types.SimpleNamespace(BoardPredictor=None, Orientation=None, Turn=None)
from chess_screen import ScreenChess


class Var:
    def __init__(self, value=None): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class Root:
    def __init__(self): self.jobs = {}
    def after(self, delay, fn): self.jobs['click'] = fn; return 'click'
    def after_cancel(self, job): self.jobs.pop(job, None)
    def winfo_rootx(self): return 900
    def winfo_rooty(self): return 0
    def winfo_width(self): return 400
    def winfo_height(self): return 400


class Mouse:
    def __init__(self): self.points = []; self.escape = False
    def stopped(self): return self.escape
    def click(self, point): self.points.append(point)


def app():
    obj = ScreenChess.__new__(ScreenChess)
    obj.root = Root(); obj.mouse = Mouse(); obj.generation = 0
    obj.region = (100, 200, 900, 1000)
    obj.orientation = Var('white'); obj.bot_color = Var('white')
    obj.autoplay = Var(True); obj.auto = Var(True); obj.autoqueen = Var(False)
    obj.status = Var(); obj.best_text = Var(); obj.eval_text = Var()
    obj.confirmed = chess.Board(); obj.best_move = chess.Move.from_uci('e2e4')
    obj.analysis_fen = obj.confirmed.fen()
    obj.image = Image.new('RGB', (800, 800), 'white')
    obj.analysis_signature = obj.signature(obj.image)
    obj.pending_move = obj.pending_since = obj.click_job = None
    obj.busy = False
    return obj


class PlayerTests(unittest.TestCase):
    def test_coordinates_both_orientations(self):
        for orientation in ('white', 'black'):
            points = {square_center((100, 200, 900, 1000), square, orientation) for square in chess.SQUARES}
            self.assertEqual(len(points), 64)
            self.assertTrue(all(100 < x < 900 and 200 < y < 1000 for x, y in points))
        self.assertEqual(square_center((100, 200, 900, 1000), chess.E2, 'white'), (550, 850))
        self.assertEqual(square_center((100, 200, 900, 1000), chess.E2, 'black'), (450, 350))

    def test_verified_move_preserves_history_and_reply(self):
        board = chess.Board(); move = chess.Move.from_uci('e2e4')
        expected = board.copy(); expected.push(move)
        result = verify_played_position(board, move, expected.board_fen())
        self.assertEqual(result.fen(), expected.fen())
        expected.push_uci('e7e5')
        result = verify_played_position(board, move, expected.board_fen())
        self.assertEqual(result.fen(), expected.fen())
        self.assertEqual(len(result.move_stack), 2)
        self.assertIsNone(verify_played_position(board, move, board.board_fen()))
        wrong = board.copy(); wrong.push_uci('d2d4')
        with self.assertRaises(ValueError): verify_played_position(board, move, wrong.board_fen())

    def test_special_moves(self):
        for fen, uci in [
            ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1', 'e1g1'),
            ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6'),
            ('4k3/P7/8/8/8/8/8/4K3 w - - 0 1', 'a7a8q')]:
            board = chess.Board(fen); move = chess.Move.from_uci(uci)
            expected = board.copy(); expected.push(move)
            self.assertEqual(verify_played_position(board, move, expected.board_fen()).fen(), expected.fen())

    def test_clicks_once_and_waits_for_verification(self):
        obj = app(); before = obj.confirmed.fen()
        obj.maybe_play(obj.image); obj.maybe_play(obj.image)
        self.assertEqual(len(obj.mouse.points), 1)
        obj.finish_click()
        self.assertEqual(obj.mouse.points, [(550, 850), (550, 650)])
        self.assertEqual(obj.confirmed.fen(), before)
        obj.maybe_play(obj.image)
        self.assertEqual(len(obj.mouse.points), 2)

    def test_wrong_turn_stale_image_and_illegal_move(self):
        for change in ('turn', 'image', 'fen', 'illegal', 'busy', 'off', 'overlap'):
            obj = app(); image = obj.image
            if change == 'turn': obj.bot_color.set('black')
            if change == 'image': image = Image.new('RGB', (800, 800), 'black')
            if change == 'fen': obj.analysis_fen = 'stale'
            if change == 'illegal': obj.best_move = chess.Move.from_uci('e2e5')
            if change == 'busy': obj.busy = True
            if change == 'off': obj.autoplay.set(False)
            if change == 'overlap': obj.root.winfo_rootx = lambda: 500
            obj.maybe_play(image)
            self.assertEqual(obj.mouse.points, [], change)

    def test_stop_cancels_destination_and_invalidates_position(self):
        obj = app(); obj.maybe_play(obj.image); obj.stop(); obj.finish_click()
        self.assertFalse(obj.autoplay.get()); self.assertFalse(obj.auto.get())
        self.assertIsNone(obj.confirmed); self.assertEqual(len(obj.mouse.points), 1)
        self.assertEqual(obj.root.jobs, {})

    def test_escape_between_clicks(self):
        obj = app(); obj.maybe_play(obj.image); obj.mouse.escape = True
        # WindowsMouse itself rejects a click when Escape is held; test scheduled guard too.
        obj.finish_click()
        self.assertEqual(len(obj.mouse.points), 1)

    def test_manual_promotion(self):
        obj = app(); obj.confirmed = chess.Board('4k3/P7/8/8/8/8/8/4K3 w - - 0 1')
        obj.best_move = chess.Move.from_uci('a7a8q'); obj.analysis_fen = obj.confirmed.fen()
        obj.maybe_play(obj.image)
        self.assertFalse(obj.autoplay.get()); self.assertTrue(obj.auto.get())
        self.assertEqual(obj.mouse.points, [])

    def test_normal_tracker_still_rejects_missed_move(self):
        board = chess.Board(); other = board.copy(); other.push_uci('e2e4'); other.push_uci('e7e5')
        with self.assertRaises(ValueError): advance_position(board, other.board_fen())

    def test_cancelled_worker_results_are_discarded(self):
        obj = app(); obj.events = queue.Queue(); obj.busy = True
        obj.set_busy = lambda value: setattr(obj, 'busy', value)
        obj.stop()
        obj.events.put((0, ('error', 'outdated error')))
        obj.tick()
        self.assertFalse(obj.busy)
        self.assertNotEqual(obj.status.get(), 'outdated error')
        self.assertFalse(obj.autoplay.get())

    def test_timeout_stops_without_retry(self):
        obj = app(); obj.events = queue.Queue()
        obj.maybe_play(obj.image); obj.finish_click()
        obj.pending_since = 0
        obj.tick()
        self.assertFalse(obj.autoplay.get())
        self.assertIsNone(obj.confirmed)
        self.assertEqual(len(obj.mouse.points), 2)
        self.assertIn('no retry', obj.status.get())

    def test_black_bot_on_flipped_board(self):
        obj = app(); obj.confirmed.push_uci('e2e4')
        obj.best_move = chess.Move.from_uci('e7e5')
        obj.analysis_fen = obj.confirmed.fen()
        obj.bot_color.set('black'); obj.orientation.set('black')
        obj.maybe_play(obj.image); obj.finish_click()
        self.assertEqual(obj.mouse.points, [(450, 850), (450, 650)])

    def test_enabled_autoqueen(self):
        obj = app(); obj.confirmed = chess.Board('4k3/P7/8/8/8/8/8/4K3 w - - 0 1')
        obj.best_move = chess.Move.from_uci('a7a8q'); obj.analysis_fen = obj.confirmed.fen()
        obj.autoqueen.set(True)
        obj.maybe_play(obj.image); obj.finish_click()
        self.assertEqual(len(obj.mouse.points), 2)


    def test_timeout_after_recognition_returns_unchanged_board(self):
        obj = app(); obj.events = queue.Queue()
        obj.maybe_play(obj.image); obj.finish_click()
        obj.pending_since = 0; obj.busy = True
        obj.set_busy = lambda value: setattr(obj, 'busy', value)
        obj.events.put((obj.generation, ('waiting',)))
        obj.tick()
        self.assertFalse(obj.autoplay.get())
        self.assertIn('no retry', obj.status.get())



if __name__ == '__main__': unittest.main()
