# Claude Legal Skills

Skills for [Claude](https://claude.ai) that help lawyers with recurring legal work.  Each skill is a folder containing a `SKILL.md` file (instructions Claude follows) and, where needed, helper scripts.  Download a skill, upload it to Claude, and Claude will use it automatically when a task calls for it.

These skills are shared to help other practitioners.  They assist with legal work; they do not replace professional judgment, a citator, or attorney review.

## Skills

| Skill | What it does | Download |
|---|---|---|
| [citation-verification](citation-verification/) | Checks every case, statute, rule, and quotation in a brief or draft: confirms each case exists, compares every quotation word for word against the opinion, tests whether each case supports the proposition cited, confirms pin cites against star-paged copies of the opinions, screens for negative treatment, and produces a Word report with links to free copies of each case. | See [Releases](../../releases) |

## Installing a skill in Claude

1. Download the skill's ZIP file from the [Releases](../../releases) page.
2. In Claude on the web or desktop, open **Customize > Skills**, click **+**, choose **Create skill**, then **Upload a skill**, and select the ZIP file.  (Menu names change from time to time; Anthropic's help article "Use skills in Claude" has current steps.)
3. Make sure **Code execution and file creation** is turned on in your Claude settings.  On Team and Enterprise plans, an organization owner may need to enable code execution and skills first.
4. Start a new chat.  Claude will use the skill when your request matches its description, or you can ask for it by name.

If you are updating a skill, delete the older version in Claude first, then upload the new one.

## citation-verification: requirements

- **Descrybe Legal Engine connector.**  The skill uses Descrybe's case lookup, passage, quote verification, treatment, and PDF tools.  Connect it in Claude before use.  Without it, the skill falls back to web search and checks far less.
- **Code execution** must be enabled.  The skill runs Python and Node scripts to compare quotations, check pin cites, and build the Word report.
- **Allowed domain for pin cites.**  Pin cites are checked against star-paged PDFs of each opinion from Descrybe.  Add `descrybe-opinion-pdfs-public.nyc3.digitaloceanspaces.com` to the additional allowed domains in your Claude code execution settings, then start a new chat.  Without it, the skill still runs but confirms far fewer pin cites and will tell you so.

### Example prompt

> Use the citation-verification skill to check every case, quotation, and pin cite in the attached brief, and give me a Word report.

### What the report contains

- The problems found, listed first.
- For every case: what it was cited for, whether it exists and says what the brief claims, each quotation with its own result, the pin cite result, a treatment signal, a link to a free copy (CourtListener), and a link to a PDF copy (Descrybe).
- Statutes and rules checked against free code websites.
- Issues visible on the face of the document (table of authorities errors, caption inconsistencies).
- Everything that could not be verified, stated plainly.

### Limits

- The treatment signal is a rough screen, not a citator.  Run KeyCite, Shepard's, or a similar tool before filing.
- Pin cites are confirmed against Descrybe's copies of the opinions, which state they are not court-certified.  Confirm against the official reporter before filing.
- Record citations (depositions, exhibits) can be checked only against documents you provide.
- Citation formats are set up for California state court (California Style Manual) and federal court (Bluebook).  Edit `SKILL.md` for other jurisdictions.
- The skill includes an optional house style (no em or en dashes, two spaces after periods, a specific statute citation form).  Edit or delete the "Optional house style" section in `SKILL.md` to match your own.

## Confidentiality

Research tools such as Descrybe are third-party services, and text sent to them leaves your Claude session.  The skill is written to send only citations, quotations from public authority, and generic statements of law, never client names or confidential facts.  Review your own obligations (for example, California Rules of Professional Conduct, rule 1.6, and Business and Professions Code section 6068(e)) and your firm's policies before using any AI tool with client matters.

## Disclaimer

These skills are provided as-is, without warranty of any kind, and are not legal advice.  You are responsible for verifying all work product before relying on it or filing it.

## Contributing

Suggestions and corrections are welcome through GitHub Issues.

## License

[MIT](LICENSE)
