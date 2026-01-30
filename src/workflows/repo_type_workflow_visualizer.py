# visualize_repo_type_graph.py
# ----------------------------
"""Render the Repo-Type workflow graph as a PNG.

Usage
-----
▶ In a notebook / IPython console
    >>> from visualize_repo_type_graph import show_graph
    >>> show_graph()

▶ From the shell (writes repo_type_graph.png)
    $ python -m visualize_repo_type_graph
"""

from __future__ import annotations

import pathlib
from typing import Final

from IPython import get_ipython
from IPython.display import Image, display

from src.workflows.repo_type_workflow import generate_repo_type_workflow    # ← adjust the import!


PNG_FILENAME: Final[str] = "repo_type_graph.png"


def _build_png() -> bytes:
    """Compile the graph and return its Mermaid PNG as raw bytes."""
    compiled = generate_repo_type_workflow()       # -> CompiledStateGraph
    return compiled.get_graph().draw_mermaid_png() # <- use the inner graph


def show_graph() -> None:                     # noqa: D401 – simple wrapper
    """Display the PNG inline (for notebooks / IPython)."""
    png = _build_png()
    display(Image(png))


def save_graph(path: str | pathlib.Path = PNG_FILENAME) -> pathlib.Path:
    """Write the PNG to *path* and return the `Path` object."""
    p = pathlib.Path(path).expanduser().resolve()
    p.write_bytes(_build_png())
    return p


# ─── CLI entry-point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if get_ipython():                # running inside IPython or Jupyter?
        show_graph()
    else:
        out = save_graph()
        print(f"Graph written to {out}")
