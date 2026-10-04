#!/usr/bin/env python3
"""Refresh zattoo_ch.txt from Zattoo Switzerland's public channel page.

Lists every channel included in the Ultimate subscription, in Zattoo's own order,
as "name | quality": the name without "HD", and the picture quality in Ultimate
(SD, HD or Full HD) as a separate field.
The file is rewritten only when the channel list itself changes. If the page
can't be read, or looks wrong, the script fails and the last good list stays.
"""
import datetime, html, json, pathlib, re, sys, urllib.request

URL = "https://zattoo.com/ch/en/channels"
OUT = pathlib.Path(__file__).resolve().parent.parent / "zattoo_ch.txt"
MIN_CHANNELS = 100          # fewer than this means the page changed: keep the old list
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")


def fetch() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


QUALITY = {"fhd": "Full HD", "uhd": "4K", "hd": "HD", "sd": "SD"}


def clean(name: str) -> str:
    """'BBC Two HD' -> 'BBC Two', 'France 24 HD [fr]' -> 'France 24 [fr]'."""
    return " ".join(w for w in name.split() if w.upper() != "HD")


def from_state(page: str) -> list[str]:
    """Channel data embedded in the page (window.__PRELOADED_STATE__)."""
    start = page.find('"locale":{')
    key = page.find('"channels":{"', start if start >= 0 else 0)
    if key < 0:
        return []
    channels, _ = json.JSONDecoder().raw_decode(page, key + len('"channels":'))
    out = []
    for c in channels.values():
        if isinstance(c, dict) and c.get("title") and c.get("ultimate"):
            q = QUALITY.get(str(c["ultimate"]).lower())
            out.append(f"{clean(c['title'])} | {q}" if q else clean(c["title"]))
    return out


def from_markup(page: str) -> list[str]:
    """Fallback: the tick icons in the visible table."""
    return [clean(html.unescape(html.unescape(t))) for t in
            re.findall(r'alt="([^"]+?) included in Ultimate subscription"', page)]


def unique(names):
    seen, out = set(), []
    for n in (" ".join(x.split()) for x in names):
        key = n.split("|")[0].strip().casefold()
        if n and key not in seen:
            seen.add(key)
            out.append(n)
    return out


def current() -> list[str]:
    if not OUT.exists():
        return []
    return [l.strip() for l in OUT.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")]


def main() -> int:
    page = fetch()
    try:
        names = unique(from_state(page))
    except Exception as e:                      # page layout changed
        print(f"Embedded data unreadable ({e}); using the table instead")
        names = []
    if len(names) < MIN_CHANNELS:
        names = unique(from_markup(page))
    if len(names) < MIN_CHANNELS:
        print(f"Only {len(names)} channels found: page changed? Keeping the last list.")
        return 1
    if names == current():
        print(f"No change ({len(names)} channels)")
        return 0
    today = datetime.date.today().isoformat()
    header = (
        "# DNS Switch - TV channels: Zattoo Switzerland (Ultimate)\n"
        f"# updated: {today}\n"
        f"# source: {URL}\n"
        "#\n"
        "# Updated automatically every week from Zattoo's channel page.\n"
        "# One channel per line, in Zattoo's order:  name | picture quality in Ultimate.\n"
        "# Lines starting with # are ignored.\n"
        "# Manual edits are kept until Zattoo's list next changes.\n"
        "#\n"
    )
    OUT.write_text(header + "\n".join(names) + "\n", encoding="utf-8")
    print(f"Updated: {len(names)} channels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
