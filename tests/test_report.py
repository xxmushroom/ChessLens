import tempfile
import unittest
from pathlib import Path
import chess
import chess.engine
from report_view import render_report, score_label

class ReportTests(unittest.TestCase):
    def test_both_orientations_and_legal_playback(self):
        board = chess.Board()
        lines = [{'pv':[chess.Move.from_uci('e2e4'),chess.Move.from_uci('e7e5')], 'score':chess.engine.PovScore(chess.engine.Cp(25),chess.WHITE)}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'report.html'
            render_report(board,path,lines=lines,open_browser=False)
            import re,json
            data=json.loads(re.search(r'id="data">(.*?)</script>',path.read_text(encoding='utf-8')).group(1))
            self.assertEqual(len(data['candidates'][0]['frames']),3)
            self.assertEqual(len(data['candidates'][0]['frames'][2]),2)
            self.assertEqual(data['candidates'][0]['san'],'1. e4 e5')
            self.assertEqual(board.fen(),chess.STARTING_FEN)
    def test_invalid_variation_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                render_report(chess.Board(),Path(folder)/'bad.html',lines=[{'pv':[chess.Move.from_uci('e2e5')]}],open_browser=False)
    def test_checkmate_score(self):
        self.assertEqual(score_label(chess.engine.PovScore(chess.engine.Mate(0),chess.WHITE),chess.WHITE),'Checkmate')
    def test_empty_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'review.html'
            render_report(chess.Board(),path,open_browser=False)
            self.assertIn('No engine lines yet',path.read_text(encoding='utf-8'))
