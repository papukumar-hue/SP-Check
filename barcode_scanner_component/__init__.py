import streamlit.components.v1 as components
from pathlib import Path

_FRONTEND_DIR = Path(__file__).parent / "frontend"

_barcode_scanner = components.declare_component(
    "barcode_scanner",
    path=str(_FRONTEND_DIR),
)

def barcode_scanner(key: str = "barcode_scanner") -> str | None:
    """
    Renders a live camera barcode scanner.
    Returns the scanned barcode string, or None if nothing scanned yet.
    """
    return _barcode_scanner(key=key, default=None)
