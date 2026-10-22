"""Paths shared by source launches and the portable Windows distribution."""
import os
from pathlib import Path
import shutil
import sys


def app_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


def resource_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def find_engine(base=None):
    folder = (Path(base) if base else app_dir()) / 'stockfish'
    candidates = [p for p in folder.rglob('*.exe') if p.name.lower().startswith('stockfish')] if folder.exists() else []
    # Prefer the neutral name, then a universal/baseline build over CPU-specific builds.
    candidates.sort(key=lambda p: (0 if p.name.lower() == 'stockfish.exe' else 1 if 'universal' in p.name.lower() else 2 if 'x86-64.exe' in p.name.lower() else 3, len(p.parts), str(p).lower()))
    if candidates:
        return str(candidates[0].resolve())
    override = os.environ.get('STOCKFISH_PATH', '')
    if override and Path(override).is_file():
        return str(Path(override).resolve())
    return shutil.which('stockfish') or ''


def data_dir():
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local'/'share'))/'ChessLens'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def report_path():
    return data_dir()/'screen_analysis.html'


def create_predictor():
    from chessvision import BoardPredictor
    from chessvision.classifier import PieceClassifier, MODEL_NAME
    model = resource_dir()/'models'/MODEL_NAME
    return BoardPredictor(classifier=PieceClassifier(model_path=model)) if model.is_file() else BoardPredictor()
