"""Color helpers for DO View."""

BG = "#0d0d0f"
PANEL = "#13141a"
BORDER = "#1e2030"
FG = "#c8ccd8"
FG_DIM = "#4a4e60"

GREEN = "#44ff88"
YELLOW = "#ffcc44"
RED = "#ff4466"
CYAN = "#44ccff"
PURPLE = "#aa88ff"
ORANGE = "#ff8844"

NODE_DEFAULT = "#1e2a3a"
NODE_SELECTED = "#2a4a6a"
EDGE_DEFAULT = "#1e2535"

HEALTH_COLORS = {
    "healthy": GREEN,
    "warning": YELLOW,
    "critical": RED,
}


def distortion_color(score: float) -> str:
    """0.0 (clean) → green, 1.0 (distorted) → red."""
    r = int(68 + (255 - 68) * score)
    g = int(255 - (255 - 68) * score)
    b = int(136 - 136 * score)
    return f"#{r:02x}{g:02x}{b:02x}"


def health_color(score: float) -> str:
    """0-100 health score → color."""
    return distortion_color(1.0 - score / 100.0)


def alpha_hex(color: str, alpha: float) -> str:
    """Simulate alpha by blending with BG (#0d0d0f)."""
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    br, bg, bb = 13, 13, 15
    r = int(br + (r - br) * alpha)
    g = int(bg + (g - bg) * alpha)
    b = int(bb + (b - bb) * alpha)
    return f"#{r:02x}{g:02x}{b:02x}"
