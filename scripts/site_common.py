"""
site_common.py -- pieces shared by every page under reports/ (imported, not run).

nav_html(current)   the tab bar: one tab per built week, then Roster Map and Standings.
                    `current` is an int week, "map", or "standings".
page_head(title)    <head> with the same fonts + stylesheet as the weekly report
                    (style block lifted from templates/weekly_report.html, so every page
                    stays visually identical without a second copy of the CSS).
"""
import glob
import html
import os
import re

TEMPLATE = "templates/weekly_report.html"
OUT_DIR = "reports"


def built_weeks():
    out = []
    for f in glob.glob(os.path.join(OUT_DIR, "data", "week-*.json")):
        m = re.search(r"week-(\d+)\.json$", f)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def nav_html(current, weeks=None):
    weeks = built_weeks() if weeks is None else weeks
    cur = ' aria-current="page"'
    links = [f'<a href="week-{w:02d}.html"{cur if current == w else ""}>Wk {w}</a>' for w in weeks]
    links.append(f'<a href="roster-map.html"{cur if current == "map" else ""}>Roster Map</a>')
    links.append(f'<a href="standings.html"{cur if current == "standings" else ""}>Standings</a>')
    return "".join(links)


def page_head(title, extra_css=""):
    tpl = open(TEMPLATE, encoding="utf-8").read()
    style = re.search(r"<style>.*?</style>", tpl, re.S).group(0)
    fonts = re.findall(r"<link [^>]*>", tpl)
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            f"<title>{html.escape(title)}</title>\n" + "\n".join(fonts) + "\n" + style +
            (f"\n<style>{extra_css}</style>" if extra_css else "") + "\n</head><body>")
