import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import app_paths

class PathTests(unittest.TestCase):
    def test_nested_stockfish_folder_is_discovered(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/'stockfish'/'official-release'/'stockfish-windows-x86-64.exe'
            exe.parent.mkdir(parents=True);exe.touch()
            self.assertEqual(app_paths.find_engine(folder),str(exe.resolve()))
    def test_local_engine_precedes_environment_and_prefers_universal(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'stockfish';root.mkdir()
            for name in ['stockfish-avx2.exe','stockfish-universal.exe','installer.exe']:(root/name).touch()
            with patch.dict(os.environ,{'STOCKFISH_PATH':'nonexistent.exe'}):
                self.assertEqual(Path(app_paths.find_engine(folder)).name,'stockfish-universal.exe')
    def test_frozen_base_is_executable_folder_not_working_directory(self):
        with patch.object(app_paths.sys,'frozen',True,create=True),patch.object(app_paths.sys,'executable','/portable/ChessLens.exe'):
            self.assertEqual(app_paths.app_dir(), Path('/portable').resolve())
    def test_missing_engine_is_empty(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'STOCKFISH_PATH':''}),patch.object(app_paths.shutil,'which',return_value=None):
            self.assertEqual(app_paths.find_engine(folder),'')
    def test_report_uses_writable_user_data(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            self.assertEqual(app_paths.report_path(),Path(folder)/'ChessLens'/'screen_analysis.html')
            self.assertTrue(app_paths.report_path().parent.is_dir())
