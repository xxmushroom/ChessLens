"""Conservative move-history tracking between recognized screen positions."""
import chess


def advance_position(previous, placement):
    if previous.board_fen() == placement:
        return previous.copy(), False
    matches = []
    for move in previous.legal_moves:
        candidate = previous.copy()
        candidate.push(move)
        if candidate.board_fen() == placement:
            matches.append(candidate)
    if len(matches) != 1:
        raise ValueError('Position did not match exactly one legal move. A move may have been missed, or a piece misread. Capture again and confirm the current turn and rights.')
    return matches[0], True
