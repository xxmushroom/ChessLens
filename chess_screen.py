"""Windows screen-region chess analysis and verified automatic play."""
import ctypes
import os
import shutil
from io import BytesIO
import base64
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import subprocess
import chess
import chess.engine
from PIL import ImageGrab, ImageTk
from chessvision import BoardPredictor, Orientation, Turn
from chess_image import describe_score, render_report
from screen_tracker import advance_position
from screen_player import WindowsMouse, square_center, verify_played_position


from app_paths import find_engine, report_path, create_predictor
from desktop_ui import build_ui

DEFAULT_ENGINE = find_engine()


class ScreenChess:
    def __init__(self, root):
        self.root = root
        root.title('ChessLens — Analysis studio')
        self.region = self.candidate = self.confirmed = self.latest_image = None
        self.predictor = None
        self.busy = False
        self.locked_widgets = []
        self.events = queue.Queue()
        self.last_signature = None
        self.stable = 0
        self.processed_signature = None
        self.engine_path = tk.StringVar(value=DEFAULT_ENGINE)
        self.turn = tk.StringVar(value='white')
        self.orientation = tk.StringVar(value='white')
        self.castling = tk.StringVar(value='-')
        self.ep = tk.StringVar(value='-')
        self.seconds = tk.StringVar(value='3')
        self.auto = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Select the board area, capture, check every piece, then confirm and analyse.')
        self.generation = 0
        self.autoplay = tk.BooleanVar(value=False)
        self.bot_color = tk.StringVar(value='white')
        self.autoqueen = tk.BooleanVar(value=False)
        self.best_move = None
        self.analysis_fen = self.analysis_signature = None
        self.pending_move = None
        self.pending_since = None
        self.click_job = None
        self.mouse = None
        self.best_text = tk.StringVar(value='—')
        self.eval_text = tk.StringVar(value='Confirm a position to begin')
        self.region_text = tk.StringVar(value='No board selected')
        self.history_text = tk.StringVar(value='Moves tracked after confirmation')
        self.build_ui()
        root.bind('<Escape>', lambda e: self.stop())
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(300, self.tick)

    def build_ui(self):
        build_ui(self)

    def detect_engine(self):
        self.reset()
        self.engine_path.set(find_engine())
        self.status.set('Stockfish detected.' if self.engine_path.get() else 'Place your Stockfish folder inside ChessLens, then click Detect.')

    def clear_analysis(self):
        self.best_move = self.analysis_fen = self.analysis_signature = None
        self.best_text.set('—')
        self.eval_text.set('Confirm a position to begin')

    def stop(self):
        self.generation += 1
        self.autoplay.set(False)
        self.auto.set(False)
        if self.click_job is not None:
            self.root.after_cancel(self.click_job)
            self.click_job = None
        if self.pending_move is not None:
            self.confirmed = None
            self.pending_move = self.pending_since = None
            self.clear_analysis()
        self.status.set('Stopped. Confirm the board again if a move was interrupted.')

    def close(self):
        self.stop()
        self.root.destroy()

    @staticmethod
    def signature(image):
        return bytes(value // 16 for value in image.resize((96, 96)).tobytes())

    def toggle_play(self):
        if not self.autoplay.get():
            self.stop()
            return
        if self.confirmed is None or self.best_move is None:
            self.autoplay.set(False)
            messagebox.showinfo('Confirm first', 'Capture, review and confirm the board before enabling Auto play.')
            return
        try:
            self.mouse = self.mouse or WindowsMouse()
        except Exception as exc:
            self.autoplay.set(False)
            messagebox.showerror('Auto play', str(exc))
            return
        self.auto.set(True)
        self.last_signature = None
        self.stable = 0
        self.status.set('Auto play armed. Bot waits for its color and a stable board. Hold Escape to stop.')

    def board_obstructed(self):
        left, top, right, bottom = self.region
        x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
        return x < right and x+self.root.winfo_width() > left and y < bottom and y+self.root.winfo_height() > top

    def maybe_play(self, image):
        board, move = self.confirmed, self.best_move
        if not self.autoplay.get() or self.pending_move or self.busy or board is None or move is None:
            return
        if board.turn != (self.bot_color.get() == 'white') or board.is_game_over():
            return
        if board.fen() != self.analysis_fen or move not in board.legal_moves or self.signature(image) != self.analysis_signature:
            return
        if self.board_obstructed():
            self.stop()
            self.status.set('Move this window outside the selected board area, then enable Auto play again.')
            return
        if move.promotion and (move.promotion != chess.QUEEN or not self.autoqueen.get()):
            self.autoplay.set(False)
            self.status.set('Promotion requires your choice. Play the suggested promotion manually; tracking stays on.')
            return
        try:
            if self.mouse.stopped():
                self.stop()
                return
            self.pending_move = move
            self.pending_since = time.monotonic()
            self.status.set('Playing ' + board.san(move) + '… waiting for screen confirmation.')
            self.mouse.click(square_center(self.region, move.from_square, self.orientation.get()))
            self.click_job = self.root.after(160, self.finish_click)
        except Exception as exc:
            self.stop()
            self.status.set(str(exc))

    def finish_click(self):
        self.click_job = None
        if not self.autoplay.get() or self.pending_move is None:
            return
        try:
            if self.mouse.stopped():
                self.stop()
                return
            if self.board_obstructed():
                raise ValueError('Assistant window covers the board. Capture and confirm again.')
            self.mouse.click(square_center(self.region, self.pending_move.to_square, self.orientation.get()))
            self.last_signature = self.processed_signature = None
            self.stable = 0
        except Exception as exc:
            self.stop()
            self.status.set(str(exc))

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[('Stockfish executable', '*.exe')])
        if path:
            self.reset()
            self.engine_path.set(path)

    def set_busy(self, value):
        self.busy = value
        if hasattr(self, 'progress'):
            self.progress.start(12) if value else self.progress.stop()
        if value:
            def lock(parent):
                for widget in parent.winfo_children():
                    if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button)) and widget is not self.stop_button:
                        self.locked_widgets.append((widget, str(widget.cget('state'))))
                        widget.configure(state='disabled')
                    lock(widget)
            lock(self.root)
        else:
            for widget, state in self.locked_widgets:
                widget.configure(state=state)
            self.locked_widgets.clear()

    def reset(self, event=None):
        if self.busy:
            return
        self.stop()
        self.clear_analysis()
        self.confirmed = self.candidate = None
        self.processed_signature = None
        self.set_output('')
        self.status.set('Settings changed. Capture again and confirm the position.')

    def select_region(self):
        if self.busy:
            return
        self.stop()
        self.root.withdraw()
        self.root.after(300, self.region_overlay)

    def region_overlay(self):
        try:
            shot = ImageGrab.grab()
            overlay = tk.Toplevel(self.root)
            overlay.overrideredirect(True)
            overlay.geometry(f'{shot.width}x{shot.height}+0+0')
            overlay.attributes('-topmost', True)
            canvas = tk.Canvas(overlay, width=shot.width, height=shot.height, highlightthickness=0, cursor='crosshair')
            canvas.pack()
            overlay.image = ImageTk.PhotoImage(shot)
            canvas.create_image(0, 0, image=overlay.image, anchor='nw')
            canvas.create_text(20, 20, text='Drag around exactly the 64 board squares. Escape cancels.', anchor='nw', fill='red', font=('Segoe UI', 20, 'bold'))
            start = []
            rectangle = [None]

            def down(event):
                start[:] = [event.x, event.y]
                if rectangle[0]:
                    canvas.delete(rectangle[0])
                rectangle[0] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='#00ff88', width=3)

            def drag(event):
                if start:
                    canvas.coords(rectangle[0], start[0], start[1], event.x, event.y)

            def close():
                overlay.destroy()
                self.root.deiconify()

            def up(event):
                if not start:
                    return
                bounds = (min(start[0], event.x), min(start[1], event.y), max(start[0], event.x), max(start[1], event.y))
                width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
                close()
                if min(width, height) < 160 or abs(width-height) > max(width, height)*0.03:
                    messagebox.showerror('Board area', 'Select a square board at least 160 pixels wide, without labels or surrounding UI.')
                    return
                self.region = bounds
                self.region_text.set(f'Board: {width} × {height} px  •  Primary monitor  •  Hold Escape to stop')
                self.reset()
                self.status.set('Board area selected. Set the current turn and move rights, then Capture.')
            canvas.bind('<ButtonPress-1>', down)
            canvas.bind('<B1-Motion>', drag)
            canvas.bind('<ButtonRelease-1>', up)
            overlay.bind('<Escape>', lambda e: close())
            overlay.focus_force()
        except Exception as exc:
            self.root.deiconify()
            messagebox.showerror('Screen capture', str(exc))

    def settings(self):
        engine = Path(self.engine_path.get()).expanduser()
        if not engine.is_file():
            raise ValueError('Stockfish was not found. Put it in the stockfish folder, then use Settings → Detect.')
        seconds = float(self.seconds.get())
        if not 0 < seconds <= 60:
            raise ValueError('Search seconds must be between 0 and 60.')
        rights = self.castling.get().strip()
        if rights != '-' and (not rights or any(c not in 'KQkq' for c in rights) or len(set(rights)) != len(rights)):
            raise ValueError('Castling must be - or a subset of KQkq.')
        return (str(engine.resolve()), seconds, self.turn.get(), self.orientation.get(), rights, self.ep.get().strip())

    def capture(self):
        if self.busy:
            return
        self.stop()
        self.clear_analysis()
        self.confirmed = self.candidate = None
        self.set_output('')
        self.start_recognition(False)

    def start_recognition(self, automatic, image=None, signature=None):
        if self.region is None:
            messagebox.showinfo('Select board', 'Select the board area first.')
            return
        try:
            settings = self.settings()
            image = image if image is not None else ImageGrab.grab(bbox=self.region).convert('RGB')
        except Exception as exc:
            self.auto.set(False)
            messagebox.showerror('Capture', str(exc))
            return
        previous = self.confirmed.copy() if self.confirmed is not None else None
        pending = self.pending_move
        self.set_busy(True)
        self.status.set('Reading board locally... First run may download the recognition model.')

        generation = self.generation
        def emit(event):
            self.events.put((generation, event))
        def work():
            try:
                if self.predictor is None:
                    self.predictor = create_predictor()
                result = self.predictor.predict(image.resize((800, 800)), orientation=Orientation(settings[3]), turn=Turn(settings[2]), castling=settings[4])
                placement = result.fen.split()[0]
                if automatic:
                    if pending is not None:
                        board = verify_played_position(previous, pending, placement)
                        if board is None:
                            emit(('waiting',))
                            return
                        changed = True
                    else:
                        board, changed = advance_position(previous, placement)
                    lines = self.engine_analysis(board, settings) if changed else None
                else:
                    board = chess.Board(f'{placement} {"w" if settings[2] == "white" else "b"} {settings[4]} {settings[5]} 0 1')
                    lines = None
                emit(('position', board, image, lines, automatic, signature))
            except Exception as exc:
                emit(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def engine_analysis(self, board, settings):
        if not board.is_valid():
            raise ValueError('Detected board is invalid. Correct the pieces or move rights.')
        if board.is_game_over():
            return []
        with chess.engine.SimpleEngine.popen_uci(
            settings[0],
            timeout=30,
            cwd=str(Path(settings[0]).parent),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        ) as engine:
            options = {key: value for key, value in {'Threads': 2, 'Hash': 128, 'UCI_LimitStrength': False}.items() if key in engine.options}
            if 'Skill Level' in engine.options:
                options['Skill Level'] = engine.options['Skill Level'].max
            engine.configure(options)
            return engine.analyse(board, chess.engine.Limit(time=settings[1]), multipv=3)

    def analyse(self):
        if self.busy or self.pending_move is not None or self.candidate is None:
            return
        try:
            settings = self.settings()
            board = self.candidate.copy()
            if not board.is_valid():
                raise ValueError('Position is invalid. Correct it before analysis.')
        except Exception as exc:
            messagebox.showerror('Position', str(exc))
            return
        self.set_busy(True)
        self.status.set('Stockfish is analysing...')
        generation = self.generation
        def emit(event):
            self.events.put((generation, event))
        def work():
            try:
                lines = self.engine_analysis(board, settings)
                emit(('position', board, self.latest_image, lines, True, None))
            except Exception as exc:
                emit(('error', str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def toggle_auto(self):
        if not self.auto.get():
            self.stop()
        if self.auto.get() and self.confirmed is None:
            self.auto.set(False)
            messagebox.showinfo('Confirm first', 'Capture, review every piece and click Confirm & analyse before enabling automatic updates.')
        self.last_signature = None
        self.stable = 0

    def tick(self):
        if self.autoplay.get() and self.mouse is not None and self.mouse.stopped():
            self.stop()
        while not self.events.empty():
            generation, event = self.events.get()
            self.set_busy(False)
            if generation != self.generation:
                continue
            if event[0] == 'waiting':
                continue
            if event[0] == 'error':
                self.stop()
                self.clear_analysis()
                self.confirmed = None
                self.candidate = None
                self.set_output('Suggestions cleared. Capture and confirm the position again.')
                self.status.set(event[1])
                continue
            _, board, image, lines, confirmed, signature = event
            self.candidate, self.latest_image = board, image
            self.pending_move = self.pending_since = None
            if confirmed:
                self.confirmed = board.copy()
                self.turn.set('white' if board.turn else 'black')
                fields = board.fen(en_passant='fen').split()
                self.castling.set(fields[2])
                self.ep.set(fields[3])
                moves = board.move_stack
                self.history_text.set(f'{len(moves)} half-moves tracked  •  Last move: {moves[-1].uci() if moves else "—"}')
            self.processed_signature = signature
            self.draw_board()
            if lines is not None:
                self.show_lines(lines)
            elif confirmed and self.analysis_fen == board.fen():
                self.analysis_signature = self.signature(image)
            elif not confirmed:
                self.set_output('Check every square against the captured board. Click a square to fix a piece, then Confirm & analyse.')
            self.status.set(f'{"White" if board.turn else "Black"} to move. ' + ('Tracking confirmed position.' if confirmed else 'Position requires review.'))
        if not self.busy and self.pending_since is not None and time.monotonic() - self.pending_since > 12:
            self.stop()
            self.status.set('Move was not confirmed within 12 seconds. Capture and review again; no retry was sent.')
        if self.auto.get() and not self.busy and self.click_job is None and self.confirmed is not None:
            try:
                image = ImageGrab.grab(bbox=self.region).convert('RGB')
                signature = self.signature(image)
                self.stable = self.stable + 1 if signature == self.last_signature else 0
                self.last_signature = signature
                if self.stable >= 2 and signature != self.processed_signature:
                    self.start_recognition(True, image, signature)
                elif self.stable >= 2:
                    self.maybe_play(image)
            except Exception as exc:
                self.stop()
                self.status.set(str(exc))
        self.root.after(250, self.tick)

    def draw_board(self):
        self.preview = ImageTk.PhotoImage(self.latest_image.resize((400, 400)))
        self.image_label.configure(image=self.preview)
        self.canvas.delete('all')
        for row in range(8):
            for col in range(8):
                square = self.square_at(row, col)
                x, y = col * 50, row * 50
                self.canvas.create_rectangle(x, y, x+50, y+50, fill='#e9eed8' if (row+col)%2 == 0 else '#779681', outline='')
                piece = self.candidate.piece_at(square)
                if piece:
                    self.canvas.create_text(x+25, y+25, text=piece.unicode_symbol(), font=('Segoe UI Symbol', 32), fill='#ffffff' if piece.color else '#152332')
                self.canvas.create_text(x+4, y+4, text=chess.square_name(square), anchor='nw', font=('Segoe UI', 7))

    def square_at(self, row, col):
        return chess.square(col, 7-row) if self.orientation.get() == 'white' else chess.square(7-col, row)

    def edit_square(self, event):
        if self.busy or self.candidate is None or not 0 <= event.x < 400 or not 0 <= event.y < 400:
            return
        self.stop()
        square = self.square_at(event.y//50, event.x//50)
        value = simpledialog.askstring('Correct ' + chess.square_name(square), 'P N B R Q K = White; p n b r q k = Black; . = empty')
        if value is None:
            return
        try:
            piece = None if value.strip() == '.' else chess.Piece.from_symbol(value.strip())
            self.candidate.set_piece_at(square, piece)
        except ValueError:
            messagebox.showerror('Piece', 'Enter exactly one piece letter or .')
            return
        self.stop()
        self.clear_analysis()
        self.confirmed = None
        self.set_output('Position edited. Confirm & analyse again.')
        self.draw_board()

    def set_output(self, text):
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.insert('end', text)
        self.output.configure(state='disabled')

    def show_lines(self, lines):
        board = self.candidate
        self.clear_analysis()
        self.analysis_fen = board.fen()
        self.analysis_signature = self.signature(self.latest_image)
        text = f'{"White" if board.turn else "Black"} to move\n'
        for index, info in enumerate(lines, 1):
            pv = info.get('pv', [])
            if pv:
                move = pv[0]
                text += f'{index}. {board.san(move)} ({chess.square_name(move.from_square)} → {chess.square_name(move.to_square)}) — {describe_score(info["score"], board.turn)}\n'
                text += board.variation_san(pv[:10]) + '\n\n'
        if not lines:
            text += f'Game ended: {board.result()}\n'
        self.set_output(text)
        self.draw_board()
        if lines and lines[0].get('pv'):
            move = lines[0]['pv'][0]
            self.best_move = move
            self.best_text.set(board.san(move))
            self.eval_text.set(describe_score(lines[0]['score'], board.turn))
            def center(square):
                file, rank = chess.square_file(square), chess.square_rank(square)
                return (file*50+25, (7-rank)*50+25) if self.orientation.get() == 'white' else ((7-file)*50+25, rank*50+25)
            self.canvas.create_line(*center(move.from_square), *center(move.to_square), arrow=tk.LAST, width=5, fill='#ffcf70')
        buffer = BytesIO()
        self.latest_image.save(buffer, format='PNG')
        render_report(board, report_path(), base64.b64encode(buffer.getvalue()).decode('ascii'), lines, self.orientation.get(), False)

    def open_report(self):
        import webbrowser
        report = report_path()
        if report.exists():
            webbrowser.open(report.as_uri())
        else:
            messagebox.showinfo('No analysis yet', 'Capture a board and confirm the position to generate your report.')


if __name__ == '__main__':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    ScreenChess(root)
    root.mainloop()
