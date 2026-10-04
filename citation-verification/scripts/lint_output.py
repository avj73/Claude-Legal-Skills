#!/usr/bin/env python3
"""Lint finished legal text against an optional house style (see "Optional house style" in SKILL.md).

Usage:
  python lint_output.py draft.txt
  python lint_output.py draft.md --strict
  python lint_output.py draft.txt --skip spaces,subd     # turn off individual checks

Checks can be skipped with --skip and a comma-separated list of: dashes, subd, parens, spaces.

Checks:
  1. Em dashes and en dashes (never allowed).
  2. "subd." and "subdivision" forms in code citations (use section 1950.5(g) instead).
  3. Statute citations wrapped in parentheses at the end of a sentence, for example
     "... security deposit. (Civ. Code, § 1950.5(g)(2).)" (should be its own sentence
     after the period, unparenthesized).
  4. Likely single spaces after a sentence-ending period (two spaces are required).
     This check is heuristic and skips common abbreviations and citation fragments,
     so treat hits as warnings to review.

Exit code is 1 if any error-level finding exists, 0 otherwise. With --strict,
warnings also cause exit code 1.
"""
import re
import sys

ABBREVIATIONS = {
    "v", "vs", "no", "nos", "inc", "co", "corp", "ltd", "llc", "llp", "lp", "mr", "mrs", "ms", "dr",
    "jr", "sr", "st", "cal", "app", "supp", "f", "d", "ct", "cir", "dist", "u.s", "u", "s", "p", "pp",
    "e.g", "i.e", "etc", "cf", "id", "ibid", "supra", "infra", "subd", "subds", "ch", "art", "sec",
    "civ", "code", "proc", "evid", "pen", "gov", "bus", "prof", "lab", "ins", "fam", "prob", "corp",
    "reg", "regs", "ex", "exh", "dep", "decl", "mot", "op", "opp", "rev", "stat", "stats", "fed",
    "r", "rule", "rules", "ann", "am", "pm", "a.m", "p.m", "jan", "feb", "mar", "apr", "jun", "jul",
    "aug", "sep", "sept", "oct", "nov", "dec", "approx", "dept", "div", "ed", "eds", "vol", "para",
    "ry", "ass'n", "assn", "bros", "mfg", "bd", "comm", "svcs", "natl", "intl", "cnty", "ca", "cal.rptr", "rptr", "wl", "lexis", "fn", "n", "pl", "def", "plf", "ca4th", "th", "d.c",
}

DASH_RE = re.compile(r"[\u2013\u2014]")
SUBD_RE = re.compile(r"\bsubds?\.|\bsubdivisions?\b", re.IGNORECASE)
# Sentence ends, then a parenthesized code cite such as (Civ. Code, § 1950.5.) or (Code Civ. Proc., § 430.10.)
PAREN_CITE_RE = re.compile(r"[.!?][\"\u201d]?\s+\((?:[A-Z][\w.&' ]*?(?:Code|Const\.|Rules? of Court|Reg\.)[^()\u00a7]*\u00a7)")
PAREN_CITE_INLINE_END_RE = re.compile(r"\((?:[A-Z][\w.&' ]*?Code[^()]*?§+[^()]*?)\)\.\s*$")
SINGLE_SPACE_RE = re.compile(r"([A-Za-z0-9\)\]\"'\u201d])([.!?])( )(?=[A-Z\"\u201c\(])")


def lint(text, skip=()):
    findings = []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in ([] if 'dashes' in skip else DASH_RE.finditer(line)):
            findings.append(("ERROR", ln, "em or en dash", _ctx(line, m.start())))
        for m in ([] if 'subd' in skip else SUBD_RE.finditer(line)):
            findings.append(("ERROR", ln, "'subd.' or 'subdivision' form; append subdivision to the section number",
                             _ctx(line, m.start())))
        for m in ([] if 'parens' in skip else PAREN_CITE_RE.finditer(line)):
            findings.append(("ERROR", ln, "parenthesized code citation after a sentence; use its own sentence",
                             _ctx(line, m.start())))
        if 'parens' not in skip and PAREN_CITE_INLINE_END_RE.search(line):
            findings.append(("ERROR", ln, "sentence ends with a parenthesized code citation; move it after the period unparenthesized",
                             line.strip()[-80:]))
        for m in ([] if 'spaces' in skip else SINGLE_SPACE_RE.finditer(line)):
            before = line[: m.start(2)]
            word_match = re.search(r"([A-Za-z.]+)$", before)
            word = word_match.group(1).lower().strip(".") if word_match else ""
            # skip abbreviations, initials, reporter fragments like "Cal.App.4th" and numbered cites
            if word in ABBREVIATIONS or len(word) == 1:
                continue
            if re.search(r"\d$", before) and re.search(r"\b(?:Cal|F|U\.S|P|A|N\.E|S\.E|S\.W|N\.W|So)\.?\s?\d?[a-z]*\s?\d*$", before):
                continue
            findings.append(("WARN", ln, "possible single space after period (two required)", _ctx(line, m.start(2))))
    return findings


def _ctx(line, idx, width=40):
    lo, hi = max(0, idx - width), min(len(line), idx + width)
    return ("..." if lo else "") + line[lo:hi].strip() + ("..." if hi < len(line) else "")


def main():
    argv = sys.argv[1:]
    skip = ()
    if "--skip" in argv:
        i = argv.index("--skip")
        skip = tuple(x.strip() for x in argv[i + 1].split(",")) if i + 1 < len(argv) else ()
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
    strict = "--strict" in argv
    if not args:
        print(__doc__)
        sys.exit(2)
    with open(args[0], encoding="utf-8", errors="replace") as f:
        text = f.read()
    findings = lint(text, skip)
    for level, ln, msg, ctx in findings:
        print(f"{level} line {ln}: {msg}\n    {ctx}")
    errors = sum(1 for f in findings if f[0] == "ERROR")
    warns = sum(1 for f in findings if f[0] == "WARN")
    print(f"\n{errors} error(s), {warns} warning(s).")
    sys.exit(1 if errors or (strict and warns) else 0)


if __name__ == "__main__":
    main()
