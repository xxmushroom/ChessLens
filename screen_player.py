"""Board coordinates and Windows mouse input, independent of the UI."""
import ctypes
import sys

import chess


def square_center(region, square, orientation):
    left, top, right, bottom = region
    if right <= left or bottom <= top or orientation not in ('white', 'black'):
        raise ValueError('Invalid board region or orientation.')
    file, rank = chess.square_file(square), chess.square_rank(square)
    col, row = (file, 7-rank) if orientation == 'white' else (7-file, rank)
    return round(left + (col + 0.5) * (right-left)/8), round(top + (row + 0.5) * (bottom-top)/8)


def verify_played_position(previous, move, placement):
    """Accept our expected move, optionally followed by one fast opponent reply."""
    expected = previous.copy()
    if move not in expected.legal_moves:
        raise ValueError('The suggested move is no longer legal.')
    expected.push(move)
    if expected.board_fen() == placement:
        return expected
    matches = []
    for reply in expected.legal_moves:
        result = expected.copy()
        result.push(reply)
        if result.board_fen() == placement:
            matches.append(result)
    if len(matches) == 1:
        return matches[0]
    if placement == previous.board_fen():
        return None
    raise ValueError('The screen does not match the played move. Bot stopped; capture and confirm again.')


class WindowsMouse:
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('Automatic screen clicks require Windows.')
        self.api = ctypes.WinDLL('user32', use_last_error=True)
        self.api.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self.api.SetCursorPos.restype = ctypes.c_int
        self.api.mouse_event.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_size_t]
        self.api.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.api.GetAsyncKeyState.restype = ctypes.c_short

    def stopped(self):
        return bool(self.api.GetAsyncKeyState(0x1B) & 0x8000)

    def click(self, point):
        if self.stopped():
            raise RuntimeError('Stopped with Escape.')
        if not self.api.SetCursorPos(*point):
            raise ctypes.WinError(ctypes.get_last_error())
        self.api.mouse_event(0x0002, 0, 0, 0, 0)
        self.api.mouse_event(0x0004, 0, 0, 0, 0)
