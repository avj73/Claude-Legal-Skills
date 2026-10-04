#!/usr/bin/env python3
"""Check whether quotations appear accurately in a source text.

Usage:
  python quote_check.py --source opinion.txt --quote "text to check"
  python quote_check.py --source opinion.txt --quotes quotes.json

quotes.json is a list of strings, or a list of {"id": "...", "quote": "..."} objects.

How a quote is treated:
  * Ellipses ("...", ". . .", or the single ellipsis character) split the quote into
    segments. Every segment must appear in the source, in order.
  * Bracketed alterations such as [t]he or [the court] are treated as wildcards for
    that bracketed span, so the surrounding words are still checked exactly.
  * Curly quotes, dash variants, non-breaking spaces, line-break hyphenation, and runs
    of whitespace are normalized before comparison.

Statuses:
  EXACT       every segment found exactly (case-sensitive, original punctuation)
  NORMALIZED  found only after normalizing quote style, dashes, or whitespace
  NEAR        not found exactly, but a close passage exists; a diff is shown
  NOT FOUND   no close passage in the source

Exit code is 0 if every quote is EXACT or NORMALIZED, otherwise 1.
"""
import argparse
import difflib
import json
import re
import sys

ELLIPSIS_RE = re.compile(r"\s*(?:\.\s?\.\s?\.|\u2026)\s*")
BRACKET_RE = re.compile(r"\[[^\]]*\]")


def light_norm(s):
    """Whitespace-only normalization, keeps punctuation and case."""
    s = s.replace("\u00a0", " ")
    s = re.sub(r"-\s*\n\s*", "", s)  # hyphenated line breaks
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def heavy_norm(s):
    """Normalize quote marks, dashes, and whitespace. Keeps case and words."""
    s = light_norm(s)
    s = (s.replace("\u2018", "'").replace("\u2019", "'")
          .replace("\u201c", '"').replace("\u201d", '"')
          .replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-"))
    s = re.sub(r"\s*-\s*", "-", s)
    return s


def split_segments(quote):
    """Split on ellipses, then split each piece on bracketed alterations."""
    segments = []
    for piece in ELLIPSIS_RE.split(quote):
        piece = piece.strip()
        if not piece:
            continue
        parts = [p.strip() for p in BRACKET_RE.split(piece)]
        segments.extend(p for p in parts if len(p) > 0)
    return segments


def find_in_order(segments, source, normalizer):
    """Return True if all segments occur in order in source after normalization."""
    src = normalizer(source)
    pos = 0
    for seg in segments:
        s = normalizer(seg).strip(" .,;:")  # edge punctuation may be altered by ellipsis use
        if not s:
            continue
        idx = src.find(s, pos)
        if idx == -1:
            return False
        pos = idx + len(s)
    return True


def best_window(quote, source):
    """Find the closest passage in source to the quote, for diffing."""
    q = heavy_norm(re.sub(BRACKET_RE, "", ELLIPSIS_RE.sub(" ", quote)))
    src = heavy_norm(source)
    if not q or not src:
        return None, 0.0
    qlen = len(q)
    anchor_words = q.split()[:4]
    candidates = set()
    if anchor_words:
        anchor = " ".join(anchor_words)
        for m in re.finditer(re.escape(anchor), src, flags=re.IGNORECASE):
            candidates.add(m.start())
    if not candidates:
        # fall back to scanning in coarse steps
        step = max(20, qlen // 4)
        candidates = set(range(0, max(1, len(src) - qlen + 1), step))
    best, best_ratio = None, 0.0
    for start in candidates:
        for pad in (0, int(qlen * 0.15)):
            window = src[start: start + qlen + pad]
            ratio = difflib.SequenceMatcher(None, q, window, autojunk=False).ratio()
            if ratio > best_ratio:
                best, best_ratio = window, ratio
    return best, best_ratio


def word_diff(a, b):
    out = []
    sm = difflib.SequenceMatcher(None, a.split(), b.split(), autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        out.append(f"  {tag}: quote has [{' '.join(a.split()[i1:i2])}] / source has [{' '.join(b.split()[j1:j2])}]")
    return "\n".join(out)


def check(quote, source):
    segments = split_segments(quote)
    if not segments:
        return {"status": "NOT FOUND", "detail": "Empty quote."}
    if find_in_order(segments, source, light_norm):
        return {"status": "EXACT", "detail": ""}
    if find_in_order(segments, source, heavy_norm):
        return {"status": "NORMALIZED",
                "detail": "Matches after normalizing quote marks, dashes, or whitespace. "
                          "Confirm the punctuation style is what you want in the final text."}
    window, ratio = best_window(quote, source)
    if window and ratio >= 0.80:
        q = heavy_norm(re.sub(BRACKET_RE, "", ELLIPSIS_RE.sub(" ", quote)))
        return {"status": "NEAR",
                "detail": f"Closest passage similarity {ratio:.0%}.\n  Source: {window}\n{word_diff(q, window)}"}
    return {"status": "NOT FOUND",
            "detail": f"No close passage found (best similarity {ratio:.0%})." if window else "No close passage found."}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True, help="Path to a text file with the source text")
    ap.add_argument("--quote", help="A single quotation to check")
    ap.add_argument("--quotes", help="JSON file with a list of quotations")
    args = ap.parse_args()

    with open(args.source, encoding="utf-8", errors="replace") as f:
        source = f.read()

    items = []
    if args.quote:
        items.append(("1", args.quote))
    if args.quotes:
        with open(args.quotes, encoding="utf-8") as f:
            data = json.load(f)
        for i, d in enumerate(data, 1):
            if isinstance(d, dict):
                items.append((str(d.get("id", i)), d["quote"]))
            else:
                items.append((str(i), d))
    if not items:
        ap.error("Provide --quote or --quotes")

    failed = False
    for qid, q in items:
        res = check(q, source)
        preview = q if len(q) <= 90 else q[:87] + "..."
        print(f"[{qid}] {res['status']}: {preview}")
        if res["detail"]:
            print(res["detail"])
        if res["status"] not in ("EXACT", "NORMALIZED"):
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
