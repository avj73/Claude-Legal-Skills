#!/usr/bin/env python3
"""Confirm pin cites by locating quotations between star-page markers in an opinion's text.

Descrybe case PDFs (from get_case_pdf) carry inline star-page markers such as "*1253" at the
point where each reporter page begins. This script finds a quotation (or a distinctive phrase for a
paraphrased proposition) in that text and reports the reporter page(s) it falls on.

Usage:
  python pin_check.py SOURCE --first-page 1242 --quote "text" --pin 1253
  python pin_check.py SOURCE --first-page 1242 --checks checks.json

SOURCE may be a local .pdf, a local .txt, or an https URL to a PDF (downloaded with curl).
checks.json: [{"id": "1", "quote": "...", "pin": "1253"}, {"id": "2", "quote": "...", "pin": "1194-1195"}]

--first-page is the opinion's first reporter page (from the citation, e.g. 163 Cal.App.4th 1242 -> 1242).
It anchors text before the first marker and filters out stray asterisks (footnote stars, etc.).

Results per check:
  CONFIRMED   the quotation lies on the cited page or within the cited range
  WRONG PAGE  the quotation was found on a different page (the correct page is reported)
  NOT FOUND   the quotation was not found in the text (check wording with quote_check.py)
  NO MARKERS  the text has no usable star-page markers, so the pin cannot be checked

Exit code 0 if every check is CONFIRMED, otherwise 1.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

MARKER_RE = re.compile(r"\[?\*(\d{1,5})\]?")
ELLIPSIS_RE = re.compile(r"\s*(?:\.\s?\.\s?\.|\u2026)\s*")
BRACKET_RE = re.compile(r"\[[^\]]*\]")

PDF_DOMAIN = "descrybe-opinion-pdfs-public.nyc3.digitaloceanspaces.com"


def fetch(source):
    if not source.lower().startswith("http"):
        return source
    fd, path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    hdr = path + ".hdr"
    res = subprocess.run(["curl", "-s", "-L", "-o", path, "-D", hdr, "-w", "%{http_code}", source],
                         capture_output=True, text=True)
    code = res.stdout.strip()
    if code != "200":
        deny = ""
        if os.path.exists(hdr):
            for line in open(hdr, errors="replace"):
                if line.lower().startswith("x-deny-reason"):
                    deny = line.strip()
        msg = f"DOWNLOAD FAILED: HTTP {code} {deny}"
        if "host_not_allowed" in deny:
            msg += (f"\nThe domain {PDF_DOMAIN} is not on this environment's network allowlist. "
                    "The user can add it to the additional allowed domains in their Claude code execution settings "
                    "(an organization admin may control this), then start a new chat.")
        print(msg)
        sys.exit(2)
    return path


def load_text(path):
    if path.lower().endswith(".pdf"):
        out = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True)
        return out.stdout
    return open(path, encoding="utf-8", errors="replace").read()


def normalize_chunk(s):
    s = s.replace("\u00a0", " ")
    s = re.sub(r"-\s*\n\s*", "", s)  # hyphenated line breaks
    s = (s.replace("\u2018", "'").replace("\u2019", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2013", "-").replace("\u2014", "-"))
    return re.sub(r"\s+", " ", s)


def build_index(raw, first_page):
    """Return (clean_text, markers) where markers is a sorted list of (offset, page)."""
    clean_parts, markers, length = [], [], 0
    pos, last_page = 0, first_page
    for m in MARKER_RE.finditer(raw):
        page = int(m.group(1))
        # accept only plausible, increasing page markers within the opinion
        if not (first_page < page <= first_page + 400) or page <= last_page or page > last_page + 30:
            continue
        chunk = normalize_chunk(raw[pos:m.start()])
        clean_parts.append(chunk)
        length += len(chunk)
        markers.append((length, page))
        last_page = page
        pos = m.end()
    tail = normalize_chunk(raw[pos:])
    clean_parts.append(tail)
    clean = "".join(clean_parts)
    # collapse doubled spaces created at marker joins, adjusting offsets
    out, mapping = [], []
    prev_space = False
    for i, ch in enumerate(clean):
        if ch == " " and prev_space:
            mapping.append(len(out) - 1)
            continue
        prev_space = ch == " "
        mapping.append(len(out))
        out.append(ch)
    mapping.append(len(out))
    markers = [(mapping[min(o, len(mapping) - 1)], p) for (o, p) in markers]
    return "".join(out), markers


def page_at(offset, markers, first_page):
    page = first_page
    for o, p in markers:
        if o <= offset:
            page = p
        else:
            break
    return page


def locate(quote, text):
    """Find quote (handling ellipses and bracketed alterations). Return (start, end) or None."""
    segments = []
    for piece in ELLIPSIS_RE.split(quote):
        segments.extend(p.strip(" .,;:") for p in BRACKET_RE.split(piece) if p.strip(" .,;:"))
    segments = [normalize_chunk(s).strip() for s in segments if s]
    if not segments:
        return None
    for ci in (False, True):  # exact case first, then case-insensitive
        hay = text.lower() if ci else text
        start = end = None
        pos = 0
        ok = True
        for seg in segments:
            needle = seg.lower() if ci else seg
            idx = hay.find(needle, pos)
            if idx == -1:
                ok = False
                break
            if start is None:
                start = idx
            end = idx + len(needle)
            pos = end
        if ok:
            return start, end
    return None


def parse_pin(pin):
    nums = [int(n) for n in re.findall(r"\d+", str(pin))]
    if not nums:
        return None
    return (nums[0], nums[-1]) if len(nums) > 1 else (nums[0], nums[0])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--first-page", type=int, required=True)
    ap.add_argument("--quote")
    ap.add_argument("--pin")
    ap.add_argument("--checks")
    args = ap.parse_args()

    raw = load_text(fetch(args.source))
    text, markers = build_index(raw, args.first_page)
    if not markers:
        print("NO MARKERS: the text has no usable star-page markers; pin cites cannot be checked from this source.")
        sys.exit(1)
    print(f"Markers found: pages {args.first_page} (start) through {markers[-1][1]}")

    checks = []
    if args.quote:
        checks.append({"id": "1", "quote": args.quote, "pin": args.pin})
    if args.checks:
        checks.extend(json.load(open(args.checks)))
    failed = False
    for c in checks:
        loc = locate(c["quote"], text)
        label = f"[{c.get('id', '?')}]"
        if not loc:
            print(f"{label} NOT FOUND: {c['quote'][:80]}")
            failed = True
            continue
        p1, p2 = page_at(loc[0], markers, args.first_page), page_at(max(loc[1] - 1, loc[0]), markers, args.first_page)
        found = str(p1) if p1 == p2 else f"{p1}-{p2}"
        pin = parse_pin(c.get("pin"))
        if pin is None:
            print(f"{label} FOUND on p. {found} (no pin given)")
            continue
        if pin[0] <= p1 and p2 <= pin[1]:
            print(f"{label} CONFIRMED: cited {c['pin']}, found on p. {found}")
        else:
            print(f"{label} WRONG PAGE: cited {c['pin']}, found on p. {found}")
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
