"""Build a portable folder on Windows; recipients need neither Python nor a shell."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def run(args):
    subprocess.run([str(x) for x in args],cwd=ROOT,check=True)


def main():
    if sys.platform != 'win32':
        raise RuntimeError('Build this Windows executable on Windows.')
    if sys.version_info < (3,11):
        raise RuntimeError('The builder needs Python 3.11 or newer. End users do not need Python.')
    engines=[p for p in (ROOT/'stockfish').rglob('*.exe') if p.name.lower().startswith('stockfish')]
    if not engines:
        raise RuntimeError('First copy your extracted Stockfish distribution into the stockfish folder beside BUILD-WINDOWS.cmd.')
    venv=ROOT/'.build-venv';python=venv/'Scripts'/'python.exe'
    if not python.exists():run([sys.executable,'-m','venv',venv])
    run([python,'-m','pip','install','-r',ROOT/'requirements.txt','pyinstaller>=6.0,<7'])
    # Package the verified model so recipients do not need a first-run download.
    run([python,'-c',"from chessvision.classifier import PieceClassifier; from pathlib import Path; import shutil; p=Path('models'); p.mkdir(exist_ok=True); model=PieceClassifier.get_model_path(); shutil.copy2(model,p/model.name)"])
    run([python,'-m','unittest','discover','-s','tests','-v'])
    run([python,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','ChessLens',
         '--add-data','assets;assets','--add-data','models;models',
         '--collect-all','chessvision','--collect-all','onnxruntime','--collect-all','numpy',
         '--copy-metadata','python-chess','--copy-metadata','chess','launcher.py'])
    target=ROOT/'dist'/'ChessLens'
    # Refresh only the generated engine subtree, so old binaries cannot win discovery.
    if (target/'stockfish').exists():shutil.rmtree(target/'stockfish')
    shutil.copytree(ROOT/'stockfish',target/'stockfish')
    shutil.copy2(ROOT/'END-USER.txt',target/'START-HERE.txt')
    shutil.copy2(ROOT/'THIRD-PARTY.md',target/'THIRD-PARTY.md')
    source=target/'source';source.mkdir(exist_ok=True)
    for pattern in ('*.py','*.md','requirements.txt'):
        for item in ROOT.glob(pattern):shutil.copy2(item,source/item.name)
    for folder in ('assets','tests','licenses'):
        shutil.copytree(ROOT/folder,source/folder,dirs_exist_ok=True)
    # Keep dependency license notices with the release, including transitive packages.
    run([python,'-c',"from importlib.metadata import distributions; from pathlib import Path; import shutil; out=Path('dist/ChessLens/licenses'); out.mkdir(exist_ok=True); [(shutil.copy2(d.locate_file(f), (out/(d.metadata['Name']+'-'+str(f).replace('/', '_').replace('\\\\','_'))))) for d in distributions() for f in (d.files or []) if any(t in str(f).lower() for t in ('license','copying','notice')) and d.locate_file(f).is_file()]"])
    print('Testing the actual packaged engine, model and report renderer...')
    subprocess.run([str(target/'ChessLens.exe'),'--self-test'],cwd=target,check=True,timeout=180)
    archive=shutil.make_archive(str(ROOT/'dist'/'ChessLens-Windows'),'zip',root_dir=ROOT/'dist',base_dir='ChessLens')
    print('\nREADY:',archive,'\nUsers extract it and double-click ChessLens.exe. Share the entire ZIP.')


if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print('\nBUILD FAILED:',exc)
        print('No new release ZIP was created. Correct the issue above and run the builder again.')
        sys.exit(1)
