#!/usr/bin/env node
/**
 * Build the Word verification report with a hyperlink to each case.
 *
 * Usage:  node build_report.js report.json output.docx
 *
 * report.json shape (all text fields are plain strings; use two spaces after periods and no em or en dashes):
 * {
 *   "title": "Citation Verification Report",
 *   "subtitle": "Defendant's Reply in Support of Motion for Summary Judgment (Smith v. Jones)",
 *   "meta": ["Prepared January 1, 2027", "Reviewed for: [attorney name]"],
 *   "summary": ["paragraph", "paragraph"],
 *   "problems": [{"heading": "Korea Supply quote", "text": "..."}],
 *   "cases": [{
 *     "n": 1,
 *     "name": "Laabs v. City of Victorville",
 *     "cite": "(2008) 163 Cal.App.4th 1242",       // citation as it should appear
 *     "lookup": "163 Cal.App.4th 1242",            // reporter citation used for the free link
 *     "url": "https://...",                        // optional: overrides the generated link
 *     "pdf_url": "https://...",                    // optional: Descrybe get_case_pdf link, shown as "Open case PDF"
 *     "link_source": "CourtListener",              // optional label for the link
 *     "status": "VERIFIED|PARTIAL|UNVERIFIED|PROBLEM",
 *     "cited_for": "what the brief cites it for",
 *     "analysis": "what was checked and found",
 *     "quotes": [{"text": "quoted words", "status": "VERIFIED", "note": "..."}]
 *   }],
 *   "statutes": [{"cite": "Corp. Code, section 17704.09(e)", "status": "VERIFIED", "analysis": "...", "url": "optional"}],
 *   "face_issues": ["text", "text"],
 *   "unchecked": ["text", "text"],
 *   "method": ["text", "text"]
 * }
 *
 * Link rule: if "url" is given it is used as is. Otherwise a CourtListener citation link is built from
 * "lookup". CourtListener's /c/ citation URLs are a free, stable lookup that open the opinion (or a short
 * list if the citation is ambiguous). A URL that came from a search result always beats a constructed one.
 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ExternalHyperlink,
  AlignmentType, BorderStyle, WidthType, ShadingType, Header, Footer, PageNumber, HeadingLevel,
  LevelFormat,
} = require("docx");

const FONT = "Times New Roman";
const SZ = 24;      // 12 pt
const SZ_SMALL = 20; // 10 pt

const REPORTER_SEGMENTS = {
  "Cal.App.4th": "Cal.%20App.%204th",
  "Cal.App.5th": "Cal.%20App.%205th",
  "Cal.App.3d": "Cal.%20App.%203d",
  "Cal.App.2d": "Cal.%20App.%202d",
  "Cal.4th": "Cal.%204th",
  "Cal.3d": "Cal.%203d",
  "Cal.2d": "Cal.%202d",
  "Cal.5th": "Cal.%205th",
  "U.S.": "U.S.",
  "F.3d": "F.3d",
  "F.4th": "F.4th",
  "F.2d": "F.2d",
  "F.Supp.2d": "F.%20Supp.%202d",
  "F.Supp.3d": "F.%20Supp.%203d",
};

function courtListenerUrl(lookup) {
  const m = /^(\d+)\s+([A-Za-z.\s0-9]+?)\s+(\d+)$/.exec(String(lookup).trim());
  if (!m) return null;
  const reporter = m[2].replace(/\s+/g, "");
  const seg = REPORTER_SEGMENTS[reporter];
  if (!seg) return null;
  return `https://www.courtlistener.com/c/${seg}/${m[1]}/${m[3]}/`;
}

const STATUS_COLORS = { VERIFIED: "E2F0D9", PARTIAL: "FFF2CC", UNVERIFIED: "EDEDED", PROBLEM: "F8CBAD" };

const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };

function run(text, o = {}) {
  return new TextRun({ text, font: FONT, size: o.size || SZ, bold: o.bold, italics: o.italics, color: o.color, underline: o.underline });
}
function para(children, o = {}) {
  return new Paragraph({
    children: Array.isArray(children) ? children : [run(children, o)],
    spacing: { after: o.after === undefined ? 120 : o.after, line: o.line || 276 },
    alignment: o.align,
    keepNext: o.keepNext,
    indent: o.indent,
  });
}
function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({
    heading: level,
    spacing: { before: 240, after: 120 },
    keepNext: true,
    children: [new TextRun({ text, font: FONT, size: level === HeadingLevel.HEADING_1 ? 28 : 24, bold: true })],
  });
}
function link(text, url, size = SZ) {
  return new ExternalHyperlink({
    link: url,
    children: [new TextRun({ text, font: FONT, size, color: "0563C1", underline: {} })],
  });
}
function cell(children, width, o = {}) {
  const kids = Array.isArray(children) ? children : [children];
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    children: kids,
  });
}
function cellPara(text, o = {}) {
  return new Paragraph({ spacing: { after: 40 }, children: [run(text, { size: SZ_SMALL, bold: o.bold })] });
}
function bullets(items) {
  return items.map((t) => new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80, line: 276 },
    children: [run(t)],
  }));
}

function build(data) {
  const children = [];
  children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new TextRun({ text: data.title || "Citation Verification Report", font: FONT, size: 32, bold: true })] }));
  if (data.subtitle) children.push(para([run(data.subtitle, { bold: true })], { align: AlignmentType.CENTER, after: 60 }));
  (data.meta || []).forEach((m) => children.push(para([run(m, { size: SZ_SMALL })], { align: AlignmentType.CENTER, after: 40 })));
  children.push(new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "000000", space: 4 } }, spacing: { after: 200 }, children: [] }));

  if ((data.summary || []).length) {
    children.push(heading("Summary"));
    data.summary.forEach((t) => children.push(para(t)));
  }
  if ((data.problems || []).length) {
    children.push(heading("Problems Found"));
    data.problems.forEach((p) => {
      children.push(para([run(p.heading + ".  ", { bold: true }), run(p.text)]));
    });
  }

  // Status legend
  children.push(heading("Status Key"));
  children.push(para([run("VERIFIED", { bold: true }), run(":  existence, citation, proposition, and quotation confirmed against opinion or statute text.  "),
    run("PARTIAL", { bold: true }), run(":  confirmed in part; the note says what could not be confirmed.  "),
    run("UNVERIFIED", { bold: true }), run(":  not confirmed.  "),
    run("PROBLEM", { bold: true }), run(":  the source does not say what is claimed, or the quotation differs from the source.")], { }));

  // Cases
  if ((data.cases || []).length) {
    children.push(heading("Case Authorities"));
    children.push(para([run("Each case name links to a free copy of the opinion so that you can read it yourself.  Pin cites were not confirmed unless the note says so.", { italics: true, size: SZ_SMALL })]));
    const W = [500, 2900, 1200, 4760]; // 9360
    const header = new TableRow({ tableHeader: true, children: [
      cell(cellPara("No.", { bold: true }), W[0], { fill: "D9D9D9" }),
      cell(cellPara("Case (click to read)", { bold: true }), W[1], { fill: "D9D9D9" }),
      cell(cellPara("Status", { bold: true }), W[2], { fill: "D9D9D9" }),
      cell(cellPara("Analysis", { bold: true }), W[3], { fill: "D9D9D9" }),
    ]});
    const rows = [header];
    data.cases.forEach((c) => {
      const url = c.url || courtListenerUrl(c.lookup || "");
      const nameKids = [new Paragraph({ spacing: { after: 40 }, children: [
        url ? link(c.name, url, SZ_SMALL) : run(c.name, { size: SZ_SMALL, bold: true }),
      ]}), cellPara(c.cite || "")];
      if (c.pdf_url) nameKids.push(new Paragraph({ spacing: { after: 20 }, children: [link("Open case PDF", c.pdf_url, 16)] }));
      if (url && !c.url) nameKids.push(new Paragraph({ spacing: { after: 20 }, children: [run("Link: CourtListener citation lookup", { size: 16, italics: true })] }));
      if (url && c.url && c.link_source) nameKids.push(new Paragraph({ spacing: { after: 20 }, children: [run("Link: " + c.link_source, { size: 16, italics: true })] }));
      const analysis = [];
      if (c.cited_for) analysis.push(new Paragraph({ spacing: { after: 40 }, children: [run("Cited for:  ", { size: SZ_SMALL, bold: true }), run(c.cited_for, { size: SZ_SMALL })] }));
      if (c.analysis) analysis.push(new Paragraph({ spacing: { after: 40 }, children: [run(c.analysis, { size: SZ_SMALL })] }));
      (c.quotes || []).forEach((q) => {
        analysis.push(new Paragraph({ spacing: { after: 40 }, children: [
          run("Quote (" + q.status + "):  ", { size: SZ_SMALL, bold: true }),
          run("\u201C" + q.text + "\u201D", { size: SZ_SMALL, italics: true }),
          run(q.note ? "  " + q.note : "", { size: SZ_SMALL }),
        ]}));
      });
      rows.push(new TableRow({ cantSplit: false, children: [
        cell(cellPara(String(c.n)), W[0]),
        cell(nameKids, W[1]),
        cell(cellPara(c.status, { bold: true }), W[2], { fill: STATUS_COLORS[c.status] }),
        cell(analysis.length ? analysis : cellPara(""), W[3]),
      ]}));
    });
    children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: W, rows }));
  }

  // Statutes
  if ((data.statutes || []).length) {
    children.push(heading("Statutes, Rules, and Regulations"));
    const W = [3000, 1200, 5160];
    const header = new TableRow({ tableHeader: true, children: [
      cell(cellPara("Provision", { bold: true }), W[0], { fill: "D9D9D9" }),
      cell(cellPara("Status", { bold: true }), W[1], { fill: "D9D9D9" }),
      cell(cellPara("Analysis", { bold: true }), W[2], { fill: "D9D9D9" }),
    ]});
    const rows = [header];
    data.statutes.forEach((s) => {
      rows.push(new TableRow({ children: [
        cell(s.url ? new Paragraph({ spacing: { after: 40 }, children: [link(s.cite, s.url, SZ_SMALL)] }) : cellPara(s.cite), W[0]),
        cell(cellPara(s.status, { bold: true }), W[1], { fill: STATUS_COLORS[s.status] }),
        cell(cellPara(s.analysis || ""), W[2]),
      ]}));
    });
    children.push(new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: W, rows }));
  }

  if ((data.face_issues || []).length) {
    children.push(heading("Other Issues Visible on the Face of the Document"));
    children.push(...bullets(data.face_issues));
  }
  if ((data.unchecked || []).length) {
    children.push(heading("Not Yet Verified"));
    children.push(...bullets(data.unchecked));
  }
  if ((data.method || []).length) {
    children.push(heading("Method and Limits"));
    data.method.forEach((t) => children.push(para(t)));
  }

  return new Document({
    creator: "Claude",
    title: data.title || "Citation Verification Report",
    styles: {
      default: { document: { run: { font: FONT, size: SZ } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 24, bold: true, font: FONT }, paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 1 } },
      ],
    },
    numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }] },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [run("Privileged and Confidential, Attorney Work Product", { size: 18, italics: true })] })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [run("Page ", { size: 18 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })] })] }) },
      children,
    }],
  });
}

const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) { console.error("Usage: node build_report.js report.json output.docx"); process.exit(2); }
const data = JSON.parse(fs.readFileSync(inPath, "utf8"));
Packer.toBuffer(build(data)).then((buf) => { fs.writeFileSync(outPath, buf); console.log("Wrote " + outPath); });
