---
name: citation-verification
description: Verify every case, statute, rule, regulation, treatise, and quotation before it appears in legal work product. Use whenever Claude is about to write or deliver anything containing legal authority or a quotation from a case, statute, contract, transcript, or document, including briefs, motions, oppositions, demurrers, memos, meet-and-confer and demand letters, client advisories, blog posts and articles, and answers to legal research questions. Also use when the user asks to cite check, verify a quote, confirm a pin cite, find the citation for a proposition, or review another party's or another tool's citations (for example a CoCounsel memo or opposing brief). Trigger even when the user does not mention verification, because unverified authority and unverified quotes are the most common reason legal drafts need rework.
---

# Citation and Quotation Verification

## Why this skill exists

AI-drafted legal work often arrives with notes such as "verify pin cites," "recalled but not verified," or "placeholder citation," which pushes the verification work back onto the lawyer. The goal of this skill is to move that work to Claude, so that what is delivered has already been checked, and anything that could not be checked is clearly labeled and kept out of the polished text.

The standard is simple: nothing is presented as authority, and nothing is placed inside quotation marks, unless Claude has confirmed it against a source in this session. Memory is a lead to investigate, never a source.

## What must be verified

Verify every item in the draft that falls into one of these categories:

1. Cases: existence, name, court, year, reporter citation, and pin cite.
2. The proposition each case is cited for: does the case actually hold or say that?
3. Statutes, rules, and regulations: section exists, subdivision letters and numbers are right, text is current, and any quoted language matches.
4. Treatises, Judicial Council forms, jury instructions, ethics opinions, and secondary sources.
5. Every quotation, whether from a case, statute, contract, deposition transcript, discovery response, email, or any document the user supplied.
6. Subsequent history and citability: reversed, superseded, depublished, review granted, or unpublished.

## Workflow

### Step 1: Inventory

Before touching any tool, list every authority and every quotation in the draft or planned answer. If the user supplied a draft, the Descrybe tool `extract_case_references` can pull case references from text. Number the items. This list becomes the verification report in Step 7.

### Step 2: Load tools and protect confidentiality

The legal research tools are deferred, so call `tool_search` first (for example "Descrybe case" and "CourtListener") to load their exact parameters. Do not guess parameter names.

Descrybe is a third party. Text sent in a tool call is transmitted to its servers. Send only citations, short quoted passages from public authority, and generic statements of the legal doctrine. Do not put client names, confidential facts, or privileged analysis into queries. Use neutral descriptions ("nonresident sends demand letter into forum state") rather than the client's facts.

### Step 3: Verify cases

Work through the cases in this order, batching independent calls in parallel:

1. `find_case_from_reference` with the citation or case name to confirm the case exists and to get its ID. Confirm party names, court, year, and reporter match the draft.
2. `get_case_passages` with a detailed `focus` describing the exact proposition. This works better than `get_case_summary`, which tends to be too general to confirm a specific holding.
3. `verify_quote` for each quotation attributed to the case.
4. `check_case_status` for a treatment signal. Treat this as a screening tool only (see Step 6).

If Descrybe does not return the case or the passage is incomplete, escalate in this order:

1. `get_case_pdf`, then `web_fetch` the returned URL and read the opinion text directly.
2. CourtListener, if its tools are connected.
3. `web_search` using the Westlaw citation in quotation marks together with party names. This works well for unpublished district court orders, which Descrybe covers unevenly.
4. Official court or government sites for the opinion text.

Pin cites: check them against the Descrybe PDF, which carries the reporter's star-page markers (for example "*1253") even when `get_case_passages` text does not.

1. Call `get_case_pdf` for the case to get its public PDF URL.
2. Run `scripts/pin_check.py <PDF URL> --first-page <first page of the opinion> --checks checks.json`, where each check is a quotation (or a short distinctive phrase from the passage relied on for a paraphrase) and the cited pin. The script downloads the PDF with curl, extracts the text, and reports CONFIRMED, WRONG PAGE (with the correct page), NOT FOUND, or NO MARKERS.
3. If the download fails with `host_not_allowed`, the PDF domain (descrybe-opinion-pdfs-public.nyc3.digitaloceanspaces.com) is not on this environment's allowlist. Tell the user in one line that they can add it to the additional allowed domains in their Claude code execution settings (an organization admin may control this) and start a new chat, then fall back to the methods below.
4. Fallbacks when the PDF cannot be used: star-page markers in passage text, or a free full-text page (CourtListener, Justia, Syfert, scocal.stanford.edu) that appears in search results.
5. Never fill in a pin cite from memory. If none of these sources confirms it, mark the pin unverified.

The Descrybe PDF states that it is not issued or certified by the court. Its star paging has matched the official reporter in testing, but say once in the report that pin cites were confirmed against the Descrybe copy and should be confirmed against the official reporter or a citator before filing.

### Step 4: Verify statutes, rules, and regulations

Descrybe's `search_laws_and_rules` helps locate a provision, but confirm exact current text from an official or near-official source using `web_fetch`:

- California statutes: leginfo.legislature.ca.gov
- California Rules of Court and Judicial Council forms and CACI: courts.ca.gov
- Federal statutes: uscode.house.gov or law.cornell.edu
- Federal rules: law.cornell.edu or uscourts.gov
- Federal regulations: ecfr.gov
- California regulations: Cornell's CCR mirror, with a note if the official OAL source was not reached

Check the section number, the subdivision structure, and the operative language. Check whether the provision was amended in 2025 or 2026, whether a bill is pending that would change it, and the effective date. For anything enacted or signed recently, search for the chaptered version, because bill numbers and subdivision lettering often change between introduction and chaptering.

### Step 5: Verify every quotation

A quotation is accurate only if every word, the punctuation inside it, and any alteration marks match the source. Close paraphrase inside quotation marks is a failure.

1. Obtain the source text from Step 3 or 4, or from the user's own document or transcript.
2. Run each quotation through `scripts/quote_check.py` against the source text. It normalizes curly quotes and whitespace, handles ellipses and bracketed alterations, and reports EXACT, NORMALIZED, NEAR, or NOT FOUND, with a diff for near matches. For case quotations, `verify_quote` and `quote_check.py` serve as two independent checks when the full opinion text is available.
3. Fix any quote that is not EXACT or NORMALIZED. If the source cannot be obtained, do not leave the words in quotation marks. Paraphrase and say so in the report.
4. Confirm the attribution: who said it, and in what role. A court quoting another case is not the court's own language, so use "(internal quotation marks omitted)" or "quoting" form as the style requires. Language from a dissent, concurrence, headnote, syllabus, or dicta must not be described as the holding.
5. Confirm context. Read enough before and after the quoted words to be sure the quote is not describing a rule the court went on to reject, a party's argument, or a hypothetical.
6. Alterations: ellipses, brackets, emphasis added, and omitted citations must be marked correctly for the forum's citation style.

For quotations from the user's own record (deposition testimony, discovery responses, contracts, emails), verify against the actual document in the conversation or on disk. If the document is not available, say so and do not reproduce the quote.

### Step 6: Verify the proposition and the case's current status

Existence is not enough. For each case, confirm from the passage text that:

- It holds what the draft says it holds, in the posture stated (motion to dismiss versus summary judgment, state versus federal, party versus nonparty).
- The language relied on is a holding, not dicta, and not from a dissent or concurrence.
- The jurisdiction matches or the draft correctly describes the authority as persuasive.

Check status with `check_case_status`, `find_cases_that_cite` for negative treatment, and a targeted web search for "review granted," "depublished," "superseded by statute," or "abrogated." In California, also confirm citability under Cal. Rules of Court, rules 8.1105 and 8.1115. In federal court, check local rules on citing unpublished dispositions.

Be candid about limits. These tools do not replace KeyCite, Shepard's, or Quick Check. State this once in the report, in one sentence, and recommend running the citator as the final step. Do not scatter repeated disclaimers through the work product.

### Step 7: Resolve problems, then report

Resolve each item before delivering:

- **Not found or wrong:** replace it with verified authority from the research, or remove it. Do not leave a doubtful cite in the text on the theory that the attorney will check it.
- **Real but does not support the proposition:** say so, and either soften the proposition to what the case does support or find better authority.
- **Cannot be fully verified but is worth keeping:** keep it out of the clean text where possible. If it must stay, bracket it in the draft as [VERIFY: reason] so it cannot be mistaken for checked authority, and list it in the report.
- **No reporter cite available (new or unreported):** cite by court, docket number, and date. Use a Westlaw or Lexis cite only if it was confirmed from a source in this session. Never use placeholder cites.

Deliver the work product clean, followed by a verification report. Use this status vocabulary:

- **VERIFIED:** existence, citation, proposition, quote (if any), and pin cite confirmed against source text.
- **PARTIAL:** exists and supports the proposition, but the pin cite, a quotation, or status could not be confirmed. State exactly which part.
- **UNVERIFIED:** could not locate or confirm. State what was tried.
- **PROBLEM:** does not say what the draft says, has negative history, is not citable, or the quote did not match. State the issue and what was done about it.

Format the report as a compact table with columns: number, authority, status, note. For chat answers (not documents), keep the report short and put the status inline or in a short list beneath the answer. For long documents, put the report in a separate section after the document or in a separate file, never inside the filed or sent text.

Lead with the problems. If everything verified, say so in one line before the table.

### Step 8: Build the Word report with case links

At the end of every verification (except a quick single-question chat answer, where an offer is enough), produce a Word document containing the full analysis, with a hyperlink on each case name so the user can read the opinion for free, plus an "Open case PDF" link to the Descrybe PDF of each case. Use `scripts/build_report.js` (docx-js, already installed). Write a JSON file in the shape documented at the top of the script (title, summary, problems, cases, statutes, face_issues, unchecked, method), then run:

```
node scripts/build_report.js report.json /mnt/user-data/outputs/Citation_Verification_Report_<matter>.docx
```

Then render it to check layout (see the docx skill), and deliver it with `present_files`. Before building, read `/mnt/skills/public/docx/SKILL.md` as the environment requires.

Link rules, in order of preference:

1. A free opinion URL that actually appeared in a search or fetch result in this session (CourtListener, Justia, a court website, Cornell LII, Harvard's Caselaw Access Project). Put it in the case's `url` field. Never paste a URL from memory.
2. Otherwise leave `url` empty and fill `lookup` with the reporter citation (for example `163 Cal.App.4th 1242`). The script then builds a CourtListener citation lookup link (`https://www.courtlistener.com/c/<reporter>/<volume>/<page>/`), which is free and opens the opinion or a short list of matches. The pattern was confirmed from CourtListener volume pages returned in search results. Because `web_fetch` cannot open constructed URLs, these links cannot be click-tested in this environment, so the report's method note says so. Do not claim the links were tested.
3. For cases with no reporter citation (new or unreported), search for the opinion and use the URL from the result, or leave the case unlinked and say so in the analysis.
4. Also add a PDF link for every case: call Descrybe `get_case_pdf` with the case ID and put the returned URL in the case's `pdf_url` field. The script shows it as "Open case PDF" under the case name. These URLs point to public files (descrybe-opinion-pdfs-public), so they open without a Descrybe login. The PDF cannot be embedded in the Word file because this environment cannot download it; a link is the substitute. Do not claim the PDFs show reporter page numbers unless the user confirms it.
5. Never use Descrybe share-viewer links (descrybe.com/share/case-viewer/...) as the reader link (they are tied to the user's account tooling), and never use paywalled sources such as Westlaw or Lexis.

For statutes and rules, add a `url` only when it came from a free source returned by search (california.public.law, leginfo, Justia, FindLaw, Cornell LII, jamsadr.com, courts.ca.gov).

Content rules for the report:

- It carries all of the analysis, not a summary of it: each case gets a status, what it was cited for, what was found, and each quotation with its own status and note.
- Lead with the problems found, then the status key, then the case table, then statutes, then issues visible on the face of the document, then everything not yet verified, then a short method and limits note.
- Quotations that fail or drop words are shown with the source's actual wording so the user can compare.
- Honor the user's formatting preferences (and the optional house style, if kept) in the report text itself, and run `scripts/lint_output.py` over the report text before building if the house style is in use.
- Keep the chat reply short. Name the three or four most important findings, point to the file, and list what remains unchecked.

### Step 9: Format check

If you use the optional house style below, run `scripts/lint_output.py` on the final text before delivering (including the text going into the Word report). It flags em and en dashes, parenthetical statute citations at the end of a sentence, "subd." and "subdivision" forms, and likely single spaces after periods. Fix what it finds.

Apply the citation style that matches the forum and do not mix the two within one document:

- California state court: California Style Manual, for example *Blank v. Kirwan* (1985) 39 Cal.3d 311, 318.
- Federal court: Bluebook, for example *King v. Atiyeh*, 814 F.2d 565, 567 (9th Cir. 1987).

For other jurisdictions, use the forum's required or customary citation style.

### Optional house style

The rules below are one firm's house style. They are enforced by `scripts/lint_output.py` and applied to the Word report. Edit or delete this section to match your own preferences, and adjust the linter flags to match (see the script's help text). If the user's own saved preferences in Claude conflict with this section, the user's preferences control.

- When a code citation falls at the end of a sentence, do not wrap it in parentheses. Put it in its own citation sentence after the period, for example: "... security deposit." Civ. Code, § 1950.5(g)(2).
- Do not use "subd." or "subdivision." Append the subdivision directly to the section number, for example § 1950.5(g).
- Use no em dashes or en dashes. Use commas, parentheses, or other punctuation. For page ranges use a hyphen or the word "to."
- Use two spaces after every period.

## Tool quirks learned in use

- `verify_quote` can return "not found" for a quotation that is verbatim in the opinion (this happened with Prouty and Schuster). Before flagging a quote as inaccurate, test a shorter distinctive fragment, then run `get_case_passages` with the quote as the focus and read the passage text. Only call a quote inaccurate after the passage text itself shows different words.
- `verify_quote` matches fragments. A "found" result for a short excerpt does not prove the full quotation is accurate. Compare the full quoted string, including its first words, against a passage before marking it VERIFIED. (Example: a quote beginning "returning funds in which..." was found only as a fragment, and the opinion actually reads "returning to the plaintiff funds in which...", so words had been dropped without an ellipsis.)
- `extract_case_references` truncates long results (roughly ten items shown per call) and can merge adjacent citations into one cluster. Send citations in batches of about ten, and resolve any "ambiguous" item with `find_case_from_reference`.
- Descrybe PDF links from `get_case_pdf` cannot be opened with `web_fetch`, because the URL did not come from a search or earlier fetch. Use `web_search` to find the opinion text elsewhere (court sites, other opinions quoting the passage) and say which source was used.
- A later opinion that quotes the language and attributes it to the cited case is acceptable secondary confirmation of wording, but not of the pin cite. Mark such items PARTIAL.
- `get_case_passages` usually returns text without page markers, so use the PDF and `pin_check.py` for pin cites (Step 3).
- Check for omitted words inside quotation marks. A quote that drops words from the middle without an ellipsis, or ends mid-sentence where the omitted words change the meaning, belongs in the report as a PROBLEM or PARTIAL item even if every remaining word is accurate.
- Check that statutes are cited to the right code. A brief that cites "Code Civ. Code" or puts a Civil Code section under "Code Civ. Proc." has a citation error to report.
- When reviewing an opposing party's brief, also report mismatches between the table of authorities and the body, missing authorities in the table, wrong code names, and case number or caption inconsistencies. These are useful to the user and cheap to catch.

- Look for star-page markers (for example "*1195" or "[*990]") in passage and full-text output. A quotation that appears before a marker such as "*1195" is on page 1194. This is the main way to confirm pin cites from free text; mark only those pins VERIFIED.
- Check whether quoted language is the court's own words or the court quoting an earlier case, a treatise, or a party. If the source shows the language in quotation marks with a citation, the brief should say "quoting" or note internal quotation marks; report it if it does not.
- Read the sentences before and after each quotation. Cited authority often contains language that cuts against the citing party (for example, a case quoted for "reliance may be decided as a matter of law" that says one sentence earlier that reliance is generally a question of fact). Report these as findings useful to the user, separate from accuracy problems.
- Check parentheticals and case descriptions against the facts of the opinion (party roles, ownership percentages, procedural posture). Descriptive parentheticals are a common source of error.
- The `check_case_status` signal is noisy: it has flagged foundational California Supreme Court cases as "caution." Treat a caution flag as meaningful only when it lines up with a known development (for example, pre-2013 reliance cases after Riverisland), and say so in the report.
- When `get_case_passages` cannot surface the needed sentence, search the web for the exact phrase plus the case name. Free full-text sites such as syfert.com, CourtListener, Justia, and scocal.stanford.edu often appear in results; fetch the page from the result and read the opinion directly. These pages usually include star paging.
- Published commentary that describes a holding (law firm articles, bar journals) can confirm context when the opinion text is unavailable. Label it as secondary confirmation.

## Scaling the effort

- **A single legal question answered in chat:** verify each authority that will appear in the answer before including it. Cite only what was verified. Add a short line on anything partial.
- **A brief, motion, memo, or letter:** run the full workflow. Batch tool calls across authorities to keep it fast.
- **Reviewing someone else's draft or another tool's memo:** run the same workflow on their citations and quotations, and report discrepancies as the main deliverable. Quotations that do not match are common in machine-generated memos, so check them all.
- **User-supplied authority:** the user telling Claude a case says X does not make it verified. Verify it, and if it does not check out, tell the user plainly.

## Things that go wrong

- Treating a case summary or headnote as the opinion. Quote only from the opinion text.
- Verifying that a case exists and stopping there. The proposition and the quote are where most errors hide.
- Correcting a quote by memory. Correct it from the source text only.
- Trusting a secondary source's pin cite. Secondary sources are leads.
- Using a recent statute number from a news article. Confirm against the chaptered bill or the code.
- Relying on the tool's "no negative treatment" signal as a clean bill of health.
- Reporting verification that did not happen. If a step was skipped or a tool failed, say so in the report.
