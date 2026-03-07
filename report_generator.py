#!/usr/bin/env python3
"""
=============================================================================
  Report Generator — Converts scan_results.json into a styled HTML report
=============================================================================
"""

import json
import sys
import argparse
from datetime import datetime


# ─────────────────────────────────────────────
#  SEVERITY STYLES
# ─────────────────────────────────────────────

SEVERITY_STYLE = {
    "CRITICAL": {"color": "#c0392b", "bg": "#fdecea", "icon": "🔴", "badge": "#c0392b"},
    "HIGH":     {"color": "#e67e22", "bg": "#fef5e7", "icon": "🟠", "badge": "#e67e22"},
    "MEDIUM":   {"color": "#f39c12", "bg": "#fffde7", "icon": "🟡", "badge": "#f39c12"},
    "LOW":      {"color": "#2980b9", "bg": "#eaf4fb", "icon": "🔵", "badge": "#2980b9"},
    "INFO":     {"color": "#7f8c8d", "bg": "#f4f6f7", "icon": "⚪", "badge": "#7f8c8d"},
}


# ─────────────────────────────────────────────
#  HTML TEMPLATE
# ─────────────────────────────────────────────

def build_html(report: dict) -> str:
    meta = report["report_metadata"]
    osint = report.get("osint_data", {})
    findings = report.get("vulnerability_findings", [])
    summary = meta.get("severity_summary", {})

    # ── Build findings HTML ──────────────────────────────────────
    findings_html = ""
    for idx, f in enumerate(findings, 1):
        sev = f["severity"]
        style = SEVERITY_STYLE.get(sev, SEVERITY_STYLE["INFO"])
        findings_html += f"""
        <div class="finding-card" style="border-left: 5px solid {style['badge']}; background:{style['bg']};">
          <div class="finding-header">
            <span class="badge" style="background:{style['badge']};">{style['icon']} {sev}</span>
            <span class="finding-title">#{idx} — {f['title']}</span>
          </div>
          <div class="finding-body">
            <p><strong>Category:</strong> {f.get('category','N/A')}</p>
            <p><strong>Description:</strong> {f.get('description','')}</p>
            {"<p><strong>Evidence:</strong> <code>" + f['evidence'] + "</code></p>" if f.get('evidence') else ""}
            {"<p><strong>Remediation:</strong> " + f['remediation'] + "</p>" if f.get('remediation') else ""}
            <p class="timestamp"><small>Detected at: {f.get('found_at','N/A')}</small></p>
          </div>
        </div>"""

    # ── Build OSINT HTML ─────────────────────────────────────────
    def list_items(items):
        if not items:
            return "<em>None found</em>"
        return "<ul>" + "".join(f"<li>{i}</li>" for i in items[:50]) + "</ul>"

    def dict_table(d):
        if not d:
            return "<em>None found</em>"
        rows = "".join(
            f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>"
            for k, v in list(d.items())[:40]
        )
        return f"<table class='info-table'><tbody>{rows}</tbody></table>"

    images_html = ""
    for img in osint.get("images", [])[:20]:
        src = img.get("src", "")
        alt = img.get("alt", "")
        images_html += f"<div class='img-item'><code>{src}</code><br><small>{alt}</small></div>"

    # ── Summary bar ──────────────────────────────────────────────
    total = meta.get("total_findings", 0)
    bar_html = ""
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        count = summary.get(sev, 0)
        style = SEVERITY_STYLE[sev]
        bar_html += f"""
        <div class="summary-box" style="background:{style['bg']}; border-top:4px solid {style['badge']};">
          <div class="count" style="color:{style['badge']};">{count}</div>
          <div class="label">{style['icon']} {sev}</div>
        </div>"""

    # ── Full HTML ────────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Security Scan Report — {meta.get('target','')}</title>
  <style>
    /* ── Reset & Base ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f0f2f5;
      color: #1c1e21;
      line-height: 1.6;
    }}

    /* ── Header ── */
    .report-header {{
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
      color: #fff;
      padding: 40px;
      text-align: center;
    }}
    .report-header h1 {{ font-size: 2.2rem; margin-bottom: 8px; }}
    .report-header .subtitle {{ color: #a8d8ea; font-size: 1rem; }}
    .report-header .meta-grid {{
      display: flex; flex-wrap: wrap; justify-content: center;
      gap: 20px; margin-top: 20px;
    }}
    .meta-item {{
      background: rgba(255,255,255,0.1);
      border-radius: 8px; padding: 10px 20px;
      font-size: 0.9rem;
    }}
    .meta-item strong {{ display: block; color: #a8d8ea; }}

    /* ── Container ── */
    .container {{ max-width: 1200px; margin: 30px auto; padding: 0 20px; }}

    /* ── Section ── */
    .section {{
      background: #fff; border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      margin-bottom: 28px; overflow: hidden;
    }}
    .section-title {{
      background: #1a1a2e; color: #fff;
      padding: 16px 24px; font-size: 1.15rem;
      display: flex; align-items: center; gap: 10px;
    }}
    .section-body {{ padding: 24px; }}

    /* ── Summary Boxes ── */
    .summary-grid {{
      display: flex; flex-wrap: wrap; gap: 16px;
      padding: 24px;
    }}
    .summary-box {{
      flex: 1; min-width: 130px;
      border-radius: 10px; padding: 20px;
      text-align: center;
    }}
    .summary-box .count {{ font-size: 2.5rem; font-weight: 700; }}
    .summary-box .label {{ font-size: 0.85rem; margin-top: 4px; font-weight: 600; }}

    /* ── Finding Cards ── */
    .finding-card {{
      border-radius: 8px; margin-bottom: 16px;
      padding: 16px 20px;
    }}
    .finding-header {{
      display: flex; align-items: center; gap: 12px; margin-bottom: 10px;
    }}
    .badge {{
      color: #fff; padding: 3px 10px;
      border-radius: 12px; font-size: 0.78rem; font-weight: 700;
      white-space: nowrap;
    }}
    .finding-title {{ font-weight: 700; font-size: 1rem; }}
    .finding-body p {{ margin-bottom: 6px; font-size: 0.93rem; }}
    .finding-body code {{
      background: rgba(0,0,0,0.06); padding: 2px 6px;
      border-radius: 4px; font-size: 0.85rem; word-break: break-all;
    }}
    .timestamp {{ color: #888; margin-top: 8px !important; }}

    /* ── OSINT Tables ── */
    .info-table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
    .info-table td {{ padding: 8px 12px; border-bottom: 1px solid #eee; }}
    .info-table tr:hover {{ background: #f9f9f9; }}

    /* ── Images ── */
    .img-grid {{ display: flex; flex-wrap: wrap; gap: 12px; }}
    .img-item {{
      background: #f4f6f7; border-radius: 8px;
      padding: 10px; font-size: 0.8rem;
      max-width: 300px; word-break: break-all;
    }}

    /* ── Footer ── */
    .footer {{
      text-align: center; padding: 30px;
      color: #888; font-size: 0.85rem;
    }}
    .warning-banner {{
      background: #fff3cd; border-left: 5px solid #ffc107;
      padding: 16px 24px; margin-bottom: 24px;
      border-radius: 8px; font-size: 0.9rem;
    }}

    ul {{ padding-left: 20px; font-size: 0.9rem; }}
    ul li {{ margin-bottom: 4px; word-break: break-all; }}
  </style>
</head>
<body>

<!-- ── HEADER ── -->
<div class="report-header">
  <h1>🔐 Security Scan Report</h1>
  <div class="subtitle">Facebook-Clone Penetration Testing — Educational Use Only</div>
  <div class="meta-grid">
    <div class="meta-item"><strong>Target</strong>{meta.get('target','N/A')}</div>
    <div class="meta-item"><strong>Profile</strong>{meta.get('profile_path','N/A')}</div>
    <div class="meta-item"><strong>Generated</strong>{meta.get('generated_at','N/A')}</div>
    <div class="meta-item"><strong>Authenticated</strong>{'✅ Yes' if meta.get('authenticated') else '❌ No'}</div>
    <div class="meta-item"><strong>Total Findings</strong>{total}</div>
  </div>
</div>

<div class="container">

  <!-- ── LEGAL BANNER ── -->
  <div class="warning-banner">
    ⚠️ <strong>For Authorized Use Only:</strong> This report was generated for educational
    and ethical penetration testing purposes on a controlled environment with explicit written
    permission. Unauthorized use of these techniques is illegal under cybercrime laws.
  </div>

  <!-- ── SEVERITY SUMMARY ── -->
  <div class="section">
    <div class="section-title">📊 Severity Summary</div>
    <div class="summary-grid">{bar_html}</div>
  </div>

  <!-- ── VULNERABILITY FINDINGS ── -->
  <div class="section">
    <div class="section-title">🐛 Vulnerability Findings ({len(findings)})</div>
    <div class="section-body">
      {findings_html if findings_html else "<em>No findings recorded.</em>"}
    </div>
  </div>

  <!-- ── OSINT: BASIC INFO ── -->
  <div class="section">
    <div class="section-title">🧑 OSINT — Profile Basic Info</div>
    <div class="section-body">
      {dict_table(osint.get('basic_info', {}))}
      <br/>
      <strong>Open Graph Tags:</strong>
      {dict_table(osint.get('open_graph', {}))}
      <br/>
      <strong>Meta Tags:</strong>
      {dict_table(osint.get('meta_tags', {}))}
    </div>
  </div>

  <!-- ── OSINT: CONTACT ── -->
  <div class="section">
    <div class="section-title">📧 OSINT — Discovered Emails & Phones</div>
    <div class="section-body">
      <strong>Emails Found ({len(osint.get('raw_emails', []))}):</strong>
      {list_items(osint.get('raw_emails', []))}
      <br/>
      <strong>Phone Numbers Found ({len(osint.get('raw_phones', []))}):</strong>
      {list_items(osint.get('raw_phones', []))}
    </div>
  </div>

  <!-- ── OSINT: IMAGES ── -->
  <div class="section">
    <div class="section-title">🖼️ OSINT — Discovered Images ({len(osint.get('images', []))})</div>
    <div class="section-body">
      <div class="img-grid">{images_html if images_html else "<em>None found</em>"}</div>
    </div>
  </div>

  <!-- ── OSINT: SCRIPTS & LINKS ── -->
  <div class="section">
    <div class="section-title">🔗 OSINT — Scripts & External Links</div>
    <div class="section-body">
      <strong>Scripts / Potential API Leaks:</strong>
      {list_items(osint.get('scripts_found', []))}
      <br/>
      <strong>External Links ({len(osint.get('external_links', []))}):</strong>
      {list_items(osint.get('external_links', []))}
      <br/>
      <strong>Social Profile Links:</strong>
      {list_items(osint.get('social_links', []))}
    </div>
  </div>

</div><!-- /container -->

<div class="footer">
  Generated by Facebook-Clone Security Scanner | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC<br/>
  <strong>For educational and authorized penetration testing use only.</strong>
</div>

</body>
</html>"""


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate HTML report from scan JSON")
    parser.add_argument("--input", default="scan_results.json", help="Input JSON file")
    parser.add_argument("--output", default="security_report.html", help="Output HTML file")
    args = parser.parse_args()

    print(f"[*] Reading scan results from: {args.input}")
    with open(args.input, "r", encoding="utf-8") as f:
        report = json.load(f)

    html = build_html(report)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[✔] HTML report saved to: {args.output}")


if __name__ == "__main__":
    main()
