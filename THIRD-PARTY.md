# Components and redistribution

Stockfish is an external GPLv3 chess engine. Keep its license and the source code (or a reference to the exact corresponding source) with the executable that you place in stockfish/. Copy the full official distribution, not just an executable. Upstream: https://github.com/official-stockfish/Stockfish . Use the release tag/commit matching your binary when recording its source, not just the moving main branch.

python-chess/chess is GPLv3-or-later: https://github.com/niklasf/python-chess . The builder retains installed dependency notices and ChessLens source files. The supplied python-chess license is under licenses/. Before public release, choose and include a compatible license for your own ChessLens code and provide the corresponding sources required by the dependencies' licenses.

chessvision provides board recognition: https://pypi.org/project/chessvision/0.10.0/ . Its model is obtained by the installed classifier's checksum-verified download routine and bundled into _internal/models/. Preserve applicable package/model licenses and attribution with the release. Other runtime components include Python/Tk, Pillow, NumPy and ONNX Runtime. The build collects available dependency notices; that collection does not independently establish redistribution rights for every asset.
