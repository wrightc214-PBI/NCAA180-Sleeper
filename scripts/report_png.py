"""
report_png.py -- save reports/latest.png, a full-page image of reports/index.html.

Needs Playwright + Chromium (installed by the workflow step that calls this).
Rendered at 1200px wide, 2x pixel density, light theme, after web fonts load.
CWD must be repo root.
"""
import os
from playwright.sync_api import sync_playwright

SRC = os.path.abspath("reports/index.html")
OUT = "reports/latest.png"

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1200, "height": 800}, device_scale_factor=2, color_scheme="light")
    pg.goto("file://" + SRC, wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pg.screenshot(path=OUT, full_page=True)
    b.close()
print(f"Wrote {OUT}")
