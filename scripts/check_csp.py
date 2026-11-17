#!/usr/bin/env python3
"""Fail when a module would need more than the AI-Hydro preview allows.

Installed modules run under a content-security policy of roughly: inline script and style, fonts from
the Google Fonts hosts, images from data: URLs, no network from the page. This check scans every
modules/*/module.html (the text inside code cells and JSON blobs is ignored) for what that policy
would block:

  * any <script src>, <iframe>, <embed>, <object>, <base>, <form action=http...>, <meta http-equiv>;
  * a <link> or CSS url()/@import to any host other than fonts.googleapis.com / fonts.gstatic.com;
  * <img>/<source>/<video>/<audio> with an http(s) source;
  * fetch(), XMLHttpRequest, WebSocket, EventSource, navigator.sendBeacon, eval(), new Function(),
    document.write() in the page's own scripts.

Plain <a href="https://..."> links are navigation, not loads, and are allowed.

Usage:  python scripts/check_csp.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from repo_lib import ROOT  # noqa: E402

ALLOWED_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com"}
HOST = re.compile(r"(?:https?:)?//([^/\"')\s?#]+)")

TAGS_BANNED = [
    (re.compile(r"<script\b[^>]*\bsrc\s*=", re.I), "external <script src>"),
    (re.compile(r"<(iframe|embed|object|base)\b", re.I), "<{0}> element"),
    (re.compile(r"<meta\b[^>]*http-equiv", re.I), "<meta http-equiv>"),
    (re.compile(r"<form\b[^>]*\baction\s*=\s*[\"']?(?:https?:)?//", re.I), "<form> posting to another host"),
]
JS_BANNED = [
    (re.compile(r"(?<![\w.$])fetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
    (re.compile(r"\bnew\s+(WebSocket|EventSource)\b"), "WebSocket/EventSource"),
    (re.compile(r"\bsendBeacon\b"), "sendBeacon"),
    (re.compile(r"(?<![\w.$])eval\s*\("), "eval()"),
    (re.compile(r"\bnew\s+Function\s*\("), "new Function()"),
    (re.compile(r"\bdocument\.write\s*\("), "document.write()"),
]


def strip_inert(html: str) -> tuple[str, list[str]]:
    """Return (markup with inert text removed, list of the page's own script bodies)."""
    html = re.sub(r"<pre class=\"aihydro-source\"[^>]*>.*?</pre>", "<pre></pre>", html, flags=re.S)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    scripts = []

    def grab(m: re.Match) -> str:
        attrs = m["attrs"]
        if "json" in attrs:
            return ""
        scripts.append(m["body"])
        return "<script></script>" if "src" not in attrs else m[0]

    html = re.sub(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", grab, html, flags=re.S)
    return html, scripts


def scan(path: Path) -> list[str]:
    html = path.read_text(encoding="utf-8")
    markup, scripts = strip_inert(html)
    mod = path.parent.name
    errs = []
    for rx, what in TAGS_BANNED:
        m = rx.search(markup)
        if m:
            errs.append(f"{mod}: {what.format(*(m.groups() or ('',)))}")
    for m in re.finditer(r"<link\b[^>]*\bhref\s*=\s*[\"']([^\"']+)", markup, re.I):
        h = HOST.match(m[1])
        if h and h[1] not in ALLOWED_HOSTS:
            errs.append(f"{mod}: <link> to {h[1]}")
    for m in re.finditer(r"<(?:img|source|video|audio|track|input)\b[^>]*\bsrc\s*=\s*[\"'](https?:)?//([^\"'/]+)", markup, re.I):
        errs.append(f"{mod}: media loaded from {m[2]} (use a data: URL)")
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", markup, re.S)) + "\n" + "\n".join(re.findall(r"style\s*=\s*\"([^\"]*)\"", markup))
    for m in re.finditer(r"(?:url\(\s*[\"']?|@import\s+[\"']?)((?:https?:)?//[^\"')\s]+)", css):
        h = HOST.match(m[1])
        if h and h[1] not in ALLOWED_HOSTS:
            errs.append(f"{mod}: CSS reference to {h[1]}")
    js = "\n".join(scripts)
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js = re.sub(r"(?m)^\s*//.*$", "", js)
    js = re.sub(r"\"(?:[^\"\\\n]|\\.)*\"|'(?:[^'\\\n]|\\.)*'", '""', js)      # string literals (python sources, messages)
    for rx, what in JS_BANNED:
        if rx.search(js):
            errs.append(f"{mod}: {what} in page script")
    return errs


def main() -> int:
    errs = []
    paths = sorted((ROOT / "modules").glob("*/module.html"))
    for p in paths:
        errs += scan(p)
    for e in errs:
        print("FAIL " + e)
    if not errs:
        print(f"csp/external-host check passed for {len(paths)} modules (allowed hosts: {', '.join(sorted(ALLOWED_HOSTS))})")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
