"""Windowed executable entry point with a visible startup error and local log."""
from pathlib import Path
import sys
import traceback
from app_paths import data_dir, find_engine, create_predictor, report_path


def main():
    if '--self-test' in sys.argv:
        import chess
        import chess.engine
        from report_view import render_report
        create_predictor()  # Ensure the packaged ONNX model and native runtime load.
        engine = find_engine()
        if not engine:
            raise RuntimeError('Packaged stockfish executable not found')
        with chess.engine.SimpleEngine.popen_uci(engine, timeout=30, cwd=str(Path(engine).parent)) as process:
            lines = process.analyse(chess.Board(), chess.engine.Limit(time=0.1), multipv=1)
        render_report(chess.Board(), report_path(), lines=lines, open_browser=False)
        (data_dir()/'build-check.txt').write_text('Engine, recognition model, native runtime and HTML assets loaded successfully.\n')
        return
    import ctypes
    import tkinter as tk
    from chess_screen import ScreenChess
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    def report_callback_exception(kind, value, tb):
        from tkinter import messagebox
        log=data_dir()/'error.log'
        log.write_text(''.join(traceback.format_exception(kind,value,tb)),encoding='utf-8')
        messagebox.showerror('ChessLens', f'Something went wrong: {value}\n\nDetails saved to {log}')
    root.report_callback_exception=report_callback_exception
    ScreenChess(root)
    root.mainloop()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log=data_dir()/'error.log'
        log.write_text(traceback.format_exc(),encoding='utf-8')
        if '--self-test' not in sys.argv:
            import tkinter as tk
            from tkinter import messagebox
            root=tk.Tk();root.withdraw()
            messagebox.showerror('ChessLens could not start',f'Please keep the complete ChessLens folder together.\n\nError details: {log}')
            root.destroy()
        sys.exit(1)
