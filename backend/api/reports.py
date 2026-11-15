from flask import Blueprint, jsonify, request, send_file
from api.database.connection import get_db
import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, ListFlowable, ListItem
)
from reportlab.lib import colors

reports_bp = Blueprint("reports", __name__)

# Color palette for reports
REPORT_COLORS = {
    'primary': HexColor('#14532D'),      # Dark green
    'secondary': HexColor('#2E6B44'),    # Medium green
    'accent': HexColor('#A6431F'),       # Rust/brown
    'light_bg': HexColor('#F0F5F0'),     # Light green background
    'dark_text': HexColor('#1A2E1A'),    # Dark text
    'muted_text': HexColor('#5B6560'),   # Muted text
    'risk_high': HexColor('#A6431F'),    # High risk
    'risk_medium': HexColor('#C08A28'),  # Medium risk
    'risk_low': HexColor('#2E6B44'),     # Low risk
    'table_header': HexColor('#14532D'), # Table header
    'table_row_alt': HexColor('#F8FAF8'), # Alternate row
}

def serializable_doc(data):
    """Convert ObjectId to string for JSON serialization in a list of documents"""
    for doc in data:
        if "_id" in doc:
            doc["_id"] = str(doc["_id"])
    return data

def serializable_single(doc):
    """Convert ObjectId to string for a single document"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ============================================================
# PDF Report Generation Helpers
# ============================================================

def get_report_styles():
    """Get custom styles for PDF reports."""
    styles = getSampleStyleSheet()

    # Title style
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=REPORT_COLORS['primary'],
        spaceAfter=6,
        alignment=TA_CENTER,
    ))

    # Subtitle style
    styles.add(ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=REPORT_COLORS['muted_text'],
        spaceAfter=4,
        alignment=TA_CENTER,
    ))

    # Section heading
    styles.add(ParagraphStyle(
        name='SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=REPORT_COLORS['primary'],
        spaceBefore=16,
        spaceAfter=8,
        borderWidth=0,
        borderPadding=0,
    ))

    # Subsection heading
    styles.add(ParagraphStyle(
        name='SubsectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=REPORT_COLORS['secondary'],
        spaceBefore=10,
        spaceAfter=4,
    ))

    # Body text
    styles.add(ParagraphStyle(
        name='ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=REPORT_COLORS['dark_text'],
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=14,
    ))

    # Bullet text
    styles.add(ParagraphStyle(
        name='ReportBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=REPORT_COLORS['dark_text'],
        spaceAfter=3,
        leftIndent=20,
        bulletIndent=8,
        leading=14,
    ))

    # Footer style
    styles.add(ParagraphStyle(
        name='Footer',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=REPORT_COLORS['muted_text'],
        alignment=TA_CENTER,
    ))

    # Table cell style
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=REPORT_COLORS['dark_text'],
        leading=10,
    ))

    # Table header style
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=white,
        leading=10,
        alignment=TA_CENTER,
    ))

    return styles


def add_page_number(canvas, doc):
    """Add page numbers to PDF pages."""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(REPORT_COLORS['muted_text'])
    canvas.drawCentredString(A4[0] / 2, 0.5 * inch, text)
    canvas.restoreState()


def add_header_footer(canvas, doc, title, entity_name):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header line
    canvas.setStrokeColor(REPORT_COLORS['primary'])
    canvas.setLineWidth(1.5)
    canvas.line(0.75 * inch, A4[1] - 0.6 * inch, A4[0] - 0.75 * inch, A4[1] - 0.6 * inch)

    # Header text
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(REPORT_COLORS['muted_text'])
    canvas.drawString(0.75 * inch, A4[1] - 0.5 * inch, f"{title} — {entity_name}")
    canvas.drawRightString(A4[0] - 0.75 * inch, A4[1] - 0.5 * inch, datetime.now().strftime("%B %d, %Y"))

    # Footer
    canvas.setStrokeColor(REPORT_COLORS['muted_text'])
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.7 * inch, A4[0] - 0.75 * inch, 0.7 * inch)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(REPORT_COLORS['muted_text'])
    canvas.drawString(0.75 * inch, 0.5 * inch, "Accountability Platform — www.accountability-platform.org")
    canvas.drawCentredString(A4[0] / 2, 0.5 * inch, f"Page {canvas.getPageNumber()}")
    canvas.drawRightString(A4[0] - 0.75 * inch, 0.5 * inch, "CONFIDENTIAL")

    canvas.restoreState()


def create_score_badge(score, styles):
    """Create a score badge for the report."""
    if score >= 75:
        color = REPORT_COLORS['risk_low']
        label = "Strong"
    elif score >= 55:
        color = REPORT_COLORS['risk_medium']
        label = "Moderate"
    else:
        color = REPORT_COLORS['risk_high']
        label = "Needs Attention"

    # Create a table for the score badge
    data = [[f"{score}/100", label]]
    table = Table(data, colWidths=[1.2*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color),
        ('TEXTCOLOR', (0, 0), (-1, -1), white),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, 0), 24),
        ('FONTSIZE', (1, 0), (1, 0), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    return table


def create_finding_table(findings, styles):
    """Create a formatted table for audit findings."""
    if not findings:
        return Paragraph("No audit findings recorded.", styles['ReportBody'])

    # Headers
    headers = ['ID', 'Type', 'Category', 'Amount at Risk', 'Severity', 'Year']
    data = [headers]

    for f in findings:
        finding_type = f.get('finding_type', '').replace('_', ' ').title()
        category = f.get('category', f.get('finding_type', ''))
        amount = f.get('amount_flagged_kshm', f.get('amount_at_risk', 'N/A'))
        if isinstance(amount, (int, float)):
            amount = f"KSh {amount:,.1f}M"
        severity = f.get('severity', f.get('finding_type', ''))
        year = f.get('financial_year', f.get('fy_reviewed', 'N/A'))

        data.append([
            f.get('id', f.get('_id', 'N/A')),
            finding_type,
            category,
            str(amount),
            severity,
            str(year),
        ])

    # Create table
    col_widths = [0.7*inch, 0.9*inch, 1.5*inch, 1*inch, 0.8*inch, 0.7*inch]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    # Style the table
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), REPORT_COLORS['table_header']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, REPORT_COLORS['muted_text']),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]

    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_commands.append(('BACKGROUND', (0, i), (-1, i), REPORT_COLORS['table_row_alt']))

    # Color severity column
    for i in range(1, len(data)):
        severity = data[i][4].lower()
        if 'high' in severity or 'adverse' in severity:
            style_commands.append(('TEXTCOLOR', (4, i), (4, i), REPORT_COLORS['risk_high']))
        elif 'medium' in severity or 'qualified' in severity:
            style_commands.append(('TEXTCOLOR', (4, i), (4, i), REPORT_COLORS['risk_medium']))
        elif 'low' in severity or 'unqualified' in severity:
            style_commands.append(('TEXTCOLOR', (4, i), (4, i), REPORT_COLORS['risk_low']))

    table.setStyle(TableStyle(style_commands))
    return table


def build_governor_report_story(db, governor_name, styles):
    """Build the PDF story (content) for a governor report."""
    story = []

    # Get data - use 'name' field for county_leaders
    profile = db.county_leaders.find_one({"name": governor_name})
    if not profile:
        return None

    # County finances and audit are county-level, not governor-specific
    finances = list(db.county_finances.find({}))
    audit = list(db.county_audit_findings.find({}))
    departments = list(db.department_absorption.find({}))

    # Calculate score
    absorption_rates = [d.get("absorption_rate", 0) for d in departments]
    avg_absorption = sum(absorption_rates) / len(absorption_rates) if absorption_rates else 0

    total_flagged_kshm = sum(
        a.get("amount_flagged_kshm", 0)
        for a in audit
        if a.get("finding_type") == "misappropriation"
    )
    total_revenue_kshm = sum(f.get("amount_kshb", 0) for f in finances) * 1000
    flagged_ratio = (total_flagged_kshm / total_revenue_kshm) if total_revenue_kshm else 0
    audit_score = max(0, 100 - (flagged_ratio * 100))
    score = round((0.6 * avg_absorption) + (0.4 * audit_score), 1)

    # Title page
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("ACCOUNTABILITY REPORT", styles['ReportTitle']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"County Governor: {profile.get('name', governor_name)}", styles['ReportSubtitle']))
    story.append(Paragraph(f"{profile.get('county', 'Nyeri')} County Government", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Financial Year: 2024/25", styles['ReportSubtitle']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.5*inch))

    # Score badge
    score_table = create_score_badge(score, styles)
    story.append(score_table)
    story.append(Spacer(1, 0.3*inch))

    # Executive Summary
    story.append(PageBreak())
    story.append(Paragraph("1. EXECUTIVE SUMMARY", styles['SectionHeading']))

    summary_text = (
        f"This report provides a comprehensive accountability assessment of {profile.get('county', 'Nyeri')} "
        f"County under the leadership of Governor {profile.get('name', governor_name)} "
        f"({profile.get('party', 'N/A')}, {profile.get('tenure', 'N/A')}). "
        f"The overall accountability score is <b>{score}/100</b>, reflecting "
        f"{'strong' if score >= 75 else 'moderate' if score >= 55 else 'concerning'} "
        f"performance across financial management, audit outcomes, and service delivery."
    )
    story.append(Paragraph(summary_text, styles['ReportBody']))

    # Key metrics table
    story.append(Paragraph("Key Metrics at a Glance", styles['SubsectionHeading']))

    total_revenue = sum(f.get("amount_kshb", 0) for f in finances)
    total_development = sum(f.get("development_kshb", 0) for f in finances)
    total_recurrent = sum(f.get("recurrent_kshb", 0) for f in finances)

    metrics_data = [
        ['Metric', 'Value'],
        ['Accountability Score', f"{score}/100"],
        ['Avg. Dept. Absorption', f"{avg_absorption:.1f}%"],
        ['Total Revenue (FY24/25)', f"KSh {total_revenue:.2f}B"],
        ['Development Expenditure', f"KSh {total_development:.2f}B"],
        ['Recurrent Expenditure', f"KSh {total_recurrent:.2f}B"],
        ['Audit Findings (Total)', str(len(audit))],
        ['Misappropriation Findings', str(sum(1 for a in audit if a.get('finding_type') == 'misappropriation'))],
        ['Amount Flagged', f"KSh {total_flagged_kshm:,.1f}M"],
    ]

    metrics_table = Table(metrics_data, colWidths=[2.5*inch, 2.5*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), REPORT_COLORS['table_header']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, REPORT_COLORS['muted_text']),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, REPORT_COLORS['table_row_alt']]),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3*inch))

    # Financial Performance
    story.append(Paragraph("2. FINANCIAL PERFORMANCE", styles['SectionHeading']))

    if finances:
        story.append(Paragraph("Revenue & Expenditure Overview", styles['SubsectionHeading']))

        fin_data = [['Financial Year', 'Total Revenue (B)', 'Development (B)', 'Recurrent (B)', 'OSR (B)']]
        for f in finances:
            fin_data.append([
                f.get('financial_year', 'N/A'),
                f"{f.get('amount_kshb', 0):.2f}",
                f"{f.get('development_kshb', 0):.2f}",
                f"{f.get('recurrent_kshb', 0):.2f}",
                f"{f.get('osr_kshb', 0):.2f}",
            ])

        fin_table = Table(fin_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), REPORT_COLORS['table_header']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, REPORT_COLORS['muted_text']),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, REPORT_COLORS['table_row_alt']]),
        ]))
        story.append(fin_table)
        story.append(Spacer(1, 0.2*inch))

    # Department Absorption
    story.append(Paragraph("Departmental Budget Absorption", styles['SubsectionHeading']))

    if departments:
        dept_data = [['Department', 'Approved Budget (M)', 'Q3 Spend (M)', 'Absorption Rate', 'Status']]
        for d in departments:
            dept_data.append([
                d.get('department', 'N/A'),
                f"{d.get('approved_budget_kshm', 0):,.0f}",
                f"{d.get('q3_spend_kshm', 0):,.0f}",
                f"{d.get('absorption_rate', 0):.1f}%",
                d.get('status', 'N/A'),
            ])

        dept_table = Table(dept_data, colWidths=[1.8*inch, 1.2*inch, 1.2*inch, 1*inch, 0.8*inch])
        dept_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), REPORT_COLORS['table_header']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, REPORT_COLORS['muted_text']),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, REPORT_COLORS['table_row_alt']]),
        ]))
        story.append(dept_table)
        story.append(Spacer(1, 0.2*inch))

    # Audit Findings
    story.append(Paragraph("3. AUDIT FINDINGS & COMPLIANCE", styles['SectionHeading']))

    misappropriation_findings = [a for a in audit if a.get('finding_type') == 'misappropriation']
    correct_findings = [a for a in audit if a.get('finding_type') in ['correct', 'correct_appropriation']]

    story.append(Paragraph(
        f"The Office of the Auditor-General issued {len(audit)} findings for the review period. "
        f"Of these, <b>{len(misappropriation_findings)} flag misappropriation</b> totaling "
        f"KSh {total_flagged_kshm:,.1f}M, while <b>{len(correct_findings)} confirm correct appropriation</b>.",
        styles['ReportBody']
    ))
    story.append(Spacer(1, 0.1*inch))

    if misappropriation_findings:
        story.append(Paragraph("Misappropriation Findings", styles['SubsectionHeading']))
        story.append(create_finding_table(misappropriation_findings, styles))
        story.append(Spacer(1, 0.2*inch))

    if correct_findings:
        story.append(Paragraph("Correct Appropriation Findings", styles['SubsectionHeading']))
        story.append(create_finding_table(correct_findings, styles))
        story.append(Spacer(1, 0.2*inch))

    # Risk Assessment
    story.append(Paragraph("4. RISK ASSESSMENT & RECOMMENDATIONS", styles['SectionHeading']))

    if score >= 75:
        risk_level = "LOW"
        risk_color = REPORT_COLORS['risk_low']
        risk_text = (
            "The county demonstrates strong financial stewardship with high budget absorption "
            "and minimal audit flags. Continued transparency and proactive oversight are recommended."
        )
    elif score >= 55:
        risk_level = "MODERATE"
        risk_color = REPORT_COLORS['risk_medium']
        risk_text = (
            "The county shows mixed performance. While some departments perform well, audit findings "
            "indicate areas needing improvement. Strengthening internal controls and procurement "
            "processes should be prioritized."
        )
    else:
        risk_level = "HIGH"
        risk_color = REPORT_COLORS['risk_high']
        risk_text = (
            "Significant concerns exist regarding financial management and compliance. "
            "Multiple adverse audit findings and low absorption rates suggest systemic issues. "
            "Immediate corrective action and enhanced oversight are required."
        )

    story.append(Paragraph(f"Overall Risk Level: <font color='{risk_color}'><b>{risk_level}</b></font>", styles['ReportBody']))
    story.append(Paragraph(risk_text, styles['ReportBody']))
    story.append(Spacer(1, 0.2*inch))

    # Recommendations
    story.append(Paragraph("Key Recommendations", styles['SubsectionHeading']))
    recommendations = [
        "Implement stricter procurement oversight to prevent misappropriation",
        "Improve budget absorption rates, particularly in underperforming departments",
        "Strengthen internal audit function and follow-up on recommendations",
        "Enhance public participation in budget formulation and monitoring",
        "Digitize financial records for real-time transparency",
    ]
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", styles['ReportBullet']))

    return story


def build_constituency_report_story(db, constituency_slug, styles):
    """Build the PDF story (content) for a constituency/MP report."""
    story = []

    # Get data
    constituency = db.constituencies.find_one({"slug": constituency_slug})
    if not constituency:
        return None

    mp = db.mps.find_one({"constituency_slug": constituency_slug})
    allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
    audit = list(db.audit_findings.find({"constituency_slug": constituency_slug}))

    # Calculate score using the same algorithm as the API
    total_findings = len(audit)
    correct_findings = sum(1 for a in audit if a.get("finding_type") == "correct_appropriation")
    misappropriation_findings_count = sum(1 for a in audit if a.get("finding_type") == "misappropriation")

    if total_findings > 0:
        utilization_ratio = correct_findings / total_findings
        utilization_score = utilization_ratio * 100
    else:
        utilization_score = 50

    # Audit score
    total_amount_at_risk = 0
    for a in audit:
        if a.get("finding_type") == "misappropriation":
            amount = a.get("amount_at_risk", 0)
            if isinstance(amount, str):
                import re
                num_match = re.search(r'[\d,]+\.?\d*', amount.replace(',', ''))
                if num_match:
                    amount = float(num_match.group())
                else:
                    amount = 0
            total_amount_at_risk += amount

    if misappropriation_findings_count > 0:
        audit_score = max(0, 100 - (total_amount_at_risk / 100 * 100))
    else:
        audit_score = 100

    # OAG score
    opinion_scores = {"Unqualified": 90, "Unqualified*": 85, "Qualified": 60, "Adverse": 30, "Disclaimer": 20}
    status_scores = {"Clean": 90, "Concerning": 40, "Unknown": 50}
    oag_opinion = mp.get("oag_opinion", "") if mp else ""
    audit_status = mp.get("audit_status", "") if mp else ""
    opinion_score = opinion_scores.get(oag_opinion, 50)
    status_score = status_scores.get(audit_status, 50)
    oag_score = (opinion_score + status_score) / 2

    score = round((0.3 * utilization_score) + (0.4 * audit_score) + (0.3 * oag_score), 1)

    # Title page
    story.append(Spacer(1, 1.5*inch))
    story.append(Paragraph("ACCOUNTABILITY REPORT", styles['ReportTitle']))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Constituency: {constituency.get('name', constituency_slug)}", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.1*inch))
    mp_name = mp.get('name', 'N/A') if mp else 'N/A'
    story.append(Paragraph(f"Member of Parliament: {mp_name}", styles['ReportSubtitle']))
    story.append(Paragraph(f"Party: {mp.get('party', 'N/A') if mp else 'N/A'} | {mp.get('tenure', 'N/A') if mp else 'N/A'}", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Financial Year: 2024/25", styles['ReportSubtitle']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['ReportSubtitle']))
    story.append(Spacer(1, 0.5*inch))

    # Score badge
    score_table = create_score_badge(score, styles)
    story.append(score_table)
    story.append(Spacer(1, 0.3*inch))

    # Executive Summary
    story.append(PageBreak())
    story.append(Paragraph("1. EXECUTIVE SUMMARY", styles['SectionHeading']))

    total_allocation = sum(a.get("amount_kshm", 0) for a in allocations)

    summary_text = (
        f"This report provides an accountability assessment of the NG-CDF (National Government "
        f"Constituencies Development Fund) for <b>{constituency.get('name', constituency_slug)} "
        f"Constituency</b>, represented by <b>{mp_name}</b> "
        f"({mp.get('party', 'N/A') if mp else 'N/A'}). "
        f"The overall accountability score is <b>{score}/100</b>, reflecting "
        f"{'strong' if score >= 75 else 'moderate' if score >= 55 else 'concerning'} "
        f"performance across fund utilization, audit outcomes, and legislative oversight."
    )
    story.append(Paragraph(summary_text, styles['ReportBody']))

    # Key metrics
    story.append(Paragraph("Key Metrics at a Glance", styles['SubsectionHeading']))

    metrics_data = [
        ['Metric', 'Value'],
        ['Accountability Score', f"{score}/100"],
        ['Total NG-CDF Allocation', f"KSh {total_allocation:,.1f}M"],
        ['Audit Findings (Total)', str(total_findings)],
        ['Misappropriation Findings', str(misappropriation_findings_count)],
        ['Correct Appropriation Findings', str(correct_findings)],
        ['Amount at Risk', f"KSh {total_amount_at_risk:,.1f}M"],
        ['OAG Opinion', oag_opinion or 'N/A'],
        ['Audit Status', audit_status or 'N/A'],
    ]

    metrics_table = Table(metrics_data, colWidths=[2.5*inch, 2.5*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), REPORT_COLORS['table_header']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, REPORT_COLORS['muted_text']),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, REPORT_COLORS['table_row_alt']]),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.3*inch))

    # Allocation Trend
    story.append(Paragraph("2. NG-CDF ALLOCATION TRENDS", styles['SectionHeading']))

    if allocations:
        alloc_data = [['Financial Year', 'Amount (KSh M)', 'Category', 'Status']]
        for a in allocations:
            alloc_data.append([
                a.get('fy_key', a.get('financial_year', 'N/A')).replace('FY', '').replace('_', '/'),
                f"{a.get('amount_kshm', 0):,.1f}",
                a.get('category', 'General'),
                a.get('status', 'Disbursed'),
            ])

        alloc_table = Table(alloc_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        alloc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), REPORT_COLORS['table_header']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, REPORT_COLORS['muted_text']),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, REPORT_COLORS['table_row_alt']]),
        ]))
        story.append(alloc_table)
        story.append(Spacer(1, 0.2*inch))

    # Audit Findings
    story.append(Paragraph("3. AUDIT FINDINGS & COMPLIANCE", styles['SectionHeading']))

    misappropriation_findings = [a for a in audit if a.get('finding_type') == 'misappropriation']
    correct_findings = [a for a in audit if a.get('finding_type') == 'correct_appropriation']

    story.append(Paragraph(
        f"The Office of the Auditor-General issued {total_findings} findings for the review period. "
        f"Of these, <b>{len(misappropriation_findings)} flag misappropriation</b> with "
        f"KSh {total_amount_at_risk:,.1f}M at risk, while "
        f"<b>{len(correct_findings)} confirm correct appropriation</b>.",
        styles['ReportBody']
    ))
    story.append(Spacer(1, 0.1*inch))

    if misappropriation_findings:
        story.append(Paragraph("Misappropriation Findings", styles['SubsectionHeading']))
        story.append(create_finding_table(misappropriation_findings, styles))
        story.append(Spacer(1, 0.2*inch))

    if correct_findings:
        story.append(Paragraph("Correct Appropriation Findings", styles['SubsectionHeading']))
        story.append(create_finding_table(correct_findings, styles))
        story.append(Spacer(1, 0.2*inch))

    # Risk Assessment
    story.append(Paragraph("4. RISK ASSESSMENT & RECOMMENDATIONS", styles['SectionHeading']))

    if score >= 75:
        risk_level = "LOW"
        risk_color = REPORT_COLORS['risk_low']
        risk_text = (
            "The constituency demonstrates strong NG-CDF management with high correct appropriation "
            "rates and minimal audit flags. Continued transparency and community engagement are recommended."
        )
    elif score >= 55:
        risk_level = "MODERATE"
        risk_color = REPORT_COLORS['risk_medium']
        risk_text = (
            "The constituency shows mixed NG-CDF performance. While some funds are well-utilized, "
            "audit findings indicate areas needing improvement. Strengthening project monitoring and "
            "procurement processes should be prioritized."
        )
    else:
        risk_level = "HIGH"
        risk_color = REPORT_COLORS['risk_high']
        risk_text = (
            "Significant concerns exist regarding NG-CDF management and compliance. "
            "Multiple adverse audit findings suggest systemic issues in fund utilization. "
            "Immediate corrective action and enhanced community oversight are required."
        )

    story.append(Paragraph(f"Overall Risk Level: <font color='{risk_color}'><b>{risk_level}</b></font>", styles['ReportBody']))
    story.append(Paragraph(risk_text, styles['ReportBody']))
    story.append(Spacer(1, 0.2*inch))

    # Recommendations
    story.append(Paragraph("Key Recommendations", styles['SubsectionHeading']))
    recommendations = [
        "Implement community monitoring committees for all NG-CDF projects",
        "Improve procurement transparency and competitive bidding processes",
        "Ensure timely project completion and proper documentation",
        "Strengthen the NG-CDF committee's oversight capacity",
        "Publish quarterly fund utilization reports for public scrutiny",
    ]
    for i, rec in enumerate(recommendations, 1):
        story.append(Paragraph(f"{i}. {rec}", styles['ReportBullet']))

    return story


@reports_bp.route("/governor/<governor_name>/pdf", methods=["GET"])
def generate_governor_pdf_report(governor_name):
    """Generate a PDF accountability report for a governor."""
    try:
        db = get_db()

        # Verify governor exists - use 'name' field instead of 'governor'
        profile = db.county_leaders.find_one({"name": governor_name})
        if not profile:
            return jsonify({"error": f"Governor {governor_name} not found"}), 404

        styles = get_report_styles()
        story = build_governor_report_story(db, governor_name, styles)

        if not story:
            return jsonify({"error": "Failed to build report"}), 500

        # Build PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.8*inch,
            bottomMargin=0.8*inch,
        )

        def page_template(canvas, doc):
            add_header_footer(canvas, doc, "Governor Accountability Report", profile.get('county', 'Nyeri') + " County")

        doc.build(story, onFirstPage=page_template, onLaterPages=page_template)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{governor_name}_accountability_report_{datetime.now().strftime("%Y%m%d")}.pdf'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to generate governor PDF report", "details": str(e)}), 500


@reports_bp.route("/constituency/<constituency_slug>/pdf", methods=["GET"])
def generate_constituency_pdf_report(constituency_slug):
    """Generate a PDF accountability report for a constituency/MP."""
    try:
        db = get_db()

        # Verify constituency exists
        constituency = db.constituencies.find_one({"slug": constituency_slug})
        if not constituency:
            return jsonify({"error": f"Constituency {constituency_slug} not found"}), 404

        mp = db.mps.find_one({"constituency_slug": constituency_slug})

        styles = get_report_styles()
        story = build_constituency_report_story(db, constituency_slug, styles)

        if not story:
            return jsonify({"error": "Failed to build report"}), 500

        # Build PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.8*inch,
            bottomMargin=0.8*inch,
        )

        entity_name = f"{constituency.get('name', constituency_slug)} Constituency"
        mp_name = mp.get('name', '') if mp else ''
        title = f"MP/Constituency Accountability Report — {mp_name}"

        def page_template(canvas, doc):
            add_header_footer(canvas, doc, title, entity_name)

        doc.build(story, onFirstPage=page_template, onLaterPages=page_template)
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{constituency_slug}_accountability_report_{datetime.now().strftime("%Y%m%d")}.pdf'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to generate constituency PDF report", "details": str(e)}), 500

@reports_bp.route("/governor/<governor_name>", methods=["GET"])
def generate_governor_report(governor_name):
    """
    Generate a report for a specific governor.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()

        # Get governor profile - use 'name' field
        profile = db.county_leaders.find_one({"name": governor_name})
        if not profile:
            return jsonify({"error": f"Governor {governor_name} not found"}), 404

        profile = serializable_single(profile)

        # County finances and audit are county-level, not governor-specific
        finances = list(db.county_finances.find({}))
        finances = serializable_doc(finances)

        # Get audit findings
        audit = list(db.county_audit_findings.find({}))
        audit = serializable_doc(audit)

        # Get department data
        department = list(db.department_absorption.find({}))
        department = serializable_doc(department)

        # Create a report dictionary
        report_data = {
            "governor_profile": profile,
            "financial_data": finances,
            "audit_findings": audit,
            "department_performance": department,
            "generated_at": datetime.now().isoformat()
        }

        # Convert to DataFrame for Excel/CSV
        # We'll create multiple sheets for Excel
        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Governor profile
                pd.DataFrame([profile]).to_excel(writer, sheet_name='Profile', index=False)

                # Financial data
                if finances:
                    pd.DataFrame(finances).to_excel(writer, sheet_name='Financials', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Financials', index=False)

                # Audit findings
                if audit:
                    pd.DataFrame(audit).to_excel(writer, sheet_name='Audit', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Audit', index=False)

                # Department performance
                if department:
                    pd.DataFrame(department).to_excel(writer, sheet_name='Departments', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Departments', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{governor_name}_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV format - we'll combine key data into one CSV or return JSON for now
            # For simplicity, we'll return JSON for CSV format request
            # In a real app, we might create a CSV with multiple sections
            return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": "Failed to generate governor report", "details": str(e)}), 500

@reports_bp.route("/constituency/<constituency_slug>", methods=["GET"])
def generate_constituency_report(constituency_slug):
    """
    Generate a report for a specific constituency.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()

        # Get constituency info
        constituency = db.constituencies.find_one({"slug": constituency_slug})
        if not constituency:
            return jsonify({"error": f"Constituency {constituency_slug} not found"}), 404

        constituency = serializable_single(constituency)

        # Get MP info
        mp = db.mps.find_one({"constituency_slug": constituency_slug})
        if mp:
            mp = serializable_single(mp)

        # Get allocations
        allocations = list(db.allocations.find({"constituency_slug": constituency_slug}))
        allocations = serializable_doc(allocations)

        # Get audit findings
        audit = list(db.audit_findings.find({"constituency_slug": constituency_slug}))
        audit = serializable_doc(audit)

        # Create a report dictionary
        report_data = {
            "constituency_info": constituency,
            "mp_info": mp,
            "allocations": allocations,
            "audit_findings": audit,
            "generated_at": datetime.now().isoformat()
        }

        # Convert to Excel if requested
        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Constituency info
                pd.DataFrame([constituency]).to_excel(writer, sheet_name='Constituency', index=False)

                # MP info
                if mp:
                    pd.DataFrame([mp]).to_excel(writer, sheet_name='MP', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='MP', index=False)

                # Allocations
                if allocations:
                    pd.DataFrame(allocations).to_excel(writer, sheet_name='Allocations', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Allocations', index=False)

                # Audit findings
                if audit:
                    pd.DataFrame(audit).to_excel(writer, sheet_name='Audit', index=False)
                else:
                    pd.DataFrame().to_excel(writer, sheet_name='Audit', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'{constituency_slug}_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV format - return JSON for now
            return jsonify(report_data), 200

    except Exception as e:
        return jsonify({"error": "Failed to generate constituency report", "details": str(e)}), 500

@reports_bp.route("/audit/findings", methods=["GET"])
def generate_audit_findings_report():
    """
    Generate a report of audit findings.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    - leader_type: 'governor' or 'constituency' (optional)
    - constituency_slug: filter by constituency (for constituency findings)
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()
        leader_type = request.args.get('leader_type')
        constituency_slug = request.args.get('constituency_slug')

        # Build query
        query = {}
        if leader_type == "governor":
            query = {}  # We'll search in county_audit_findings
        elif leader_type == "constituency":
            query = {}
            if constituency_slug:
                query["constituency_slug"] = constituency_slug
            # We'll search in audit_findings
        else:
            # If no leader_type specified, we might want to search both? Let's default to both for now
            # But we need to handle different collections
            pass

        # For simplicity, let's get all audit findings from both collections if no filter
        # But we need to standardize the fields

        findings = []

        # Get governor audit findings
        if leader_type != "constituency":  # Include governor unless explicitly filtered out
            governor_findings = list(db.county_audit_findings.find({}))
            for f in governor_findings:
                f = serializable_single(f)
                findings.append({
                    "leader_type": "governor",
                    "leader_id": f.get("governor", ""),
                    "leader_name": f.get("governor", ""),
                    "county": f.get("county", ""),
                    "county_code": f.get("county_code", ""),
                    "financial_year": f.get("financial_year", ""),
                    "finding_type": f.get("finding_type", ""),
                    "amount_flagged_kshm": f.get("amount_flagged_kshm", 0),
                    "severity": f.get("severity", ""),
                    "misappropriation_notes": f.get("misappropriation_notes", ""),
                    "recommendation": f.get("recommendation", ""),
                    "note": ""
                })

        # Get constituency audit findings
        if leader_type != "governor":  # Include constituency unless explicitly filtered out
            constituency_query = {}
            if constituency_slug:
                constituency_query["constituency_slug"] = constituency_slug
            constituency_findings = list(db.audit_findings.find(constituency_query))
            for f in constituency_findings:
                f = serializable_single(f)
                findings.append({
                    "leader_type": "constituency",
                    "leader_id": f.get("constituency_slug", ""),
                    "leader_name": f.get("mp_name", ""),
                    "constituency": f.get("constituency", ""),
                    "county": f.get("county", ""),
                    "county_code": f.get("county_code", ""),
                    "financial_year": f.get("fy_reviewed", ""),
                    "finding_type": f.get("finding_type", ""),
                    "amount_flagged_kshm": 0,  # Constituency findings don't have this in seed data
                    "severity": "",
                    "misappropriation_notes": "",
                    "recommendation": "",
                    "note": f.get("note", ""),
                    "amount_at_risk": f.get("amount_at_risk", "")
                })

        if not findings:
            return jsonify({"message": "No audit findings found"}), 200

        # Convert to DataFrame
        df = pd.DataFrame(findings)

        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Audit Findings', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'audit_findings_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'audit_findings_report_{datetime.now().strftime("%Y%m%d")}.csv'
            )

    except Exception as e:
        return jsonify({"error": "Failed to generate audit findings report", "details": str(e)}), 500

@reports_bp.route("/financial/summary", methods=["GET"])
def generate_financial_summary_report():
    """
    Generate a financial summary report.
    Query parameters:
    - format: 'csv' or 'excel' (default: 'csv')
    - governor_name: filter by governor (optional)
    """
    try:
        db = get_db()
        format = request.args.get('format', 'csv').lower()
        governor_name = request.args.get('governor_name')

        # Build query for finances
        query = {}
        if governor_name:
            query["governor"] = governor_name

        # Get financial data
        finances = list(db.county_finances.find(query))
        finances = serializable_doc(finances)

        if not finances:
            return jsonify({"message": "No financial data found"}), 200

        # Convert to DataFrame
        df = pd.DataFrame(finances)

        if format == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Financial Summary', index=False)

            output.seek(0)
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'financial_summary_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            )
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'financial_summary_report_{datetime.now().strftime("%Y%m%d")}.csv'
            )

    except Exception as e:
        return jsonify({"error": "Failed to generate financial summary report", "details": str(e)}), 500


@reports_bp.route("/", methods=["GET"])
def get_reports():
    """
    Get a list of available reports for display in the reports library.
    Returns report metadata in the format expected by the frontend.
    """
    try:
        db = get_db()

        # Get some sample data to create realistic report entries
        # We'll create a few report entries based on actual data in the database

        reports_list = []

        # Get the governor to create a governor report entry
        governor = db.county_leaders.find_one()
        if governor:
            reports_list.append({
                "id": str(governor.get("_id", "gov-001")),
                "title": f"{governor.get('name', 'Governor')} Accountability Report",
                "category": "Accountability Reports",
                "entity": f"{governor.get('county', 'Nyeri County')} County",
                "financialYear": "2024/25",  # We could get this from finances data
                "datePublished": datetime.now().strftime("%Y-%m-%d"),
                "reportType": "governor",
                "reportParams": {
                    "governor_name": governor.get('name', '')
                }
            })

        # Get a few constituencies to create constituency report entries
        constituencies = list(db.constituencies.find().limit(3))
        for i, constituency in enumerate(constituencies):
            reports_list.append({
                "id": f"const-{i+1:03d}",
                "title": f"{constituency.get('name', 'Constituency')} NG-CD Report",
                "category": "NG-CDF Reports",
                "entity": constituency.get('name', 'Unknown Constituency'),
                "financialYear": "2024/25",
                "datePublished": datetime.now().strftime("%Y-%m-%d"),
                "reportType": "constituency",
                "reportParams": {
                    "constituency_slug": constituency.get('slug', '')
                }
            })

        # Add an audit findings report
        reports_list.append({
            "id": "audit-001",
            "title": "County Audit Findings Report",
            "category": "Audit Reports",
            "entity": "Nyeri County",
            "financialYear": "2024/25",
            "datePublished": datetime.now().strftime("%Y-%m-%d"),
            "reportType": "audit_findings",
            "reportParams": {}
        })

        # Add a financial summary report
        reports_list.append({
            "id": "finance-001",
            "title": "County Financial Summary Report",
            "category": "Financial Reports",
            "entity": "Nyeri County",
            "financialYear": "2024/25",
            "datePublished": datetime.now().strftime("%Y-%m-%d"),
            "reportType": "financial_summary",
            "reportParams": {}
        })

        # If we didn't get any data from the database, provide a fallback
        if not reports_list:
            reports_list = [
                {
                    "id": "R-01",
                    "title": "Nyeri County Accountability Report FY2024/25",
                    "category": "Accountability Reports",
                    "entity": "Nyeri County",
                    "financialYear": "2024/25",
                    "datePublished": "2025-08-12"
                },
                {
                    "id": "R-02",
                    "title": "Mathira NG-CDF Audit Summary FY2023/24",
                    "category": "Auditor-General Reports",
                    "entity": "Mathira",
                    "financialYear": "2023/24",
                    "datePublished": "2024-11-03"
                }
            ]

        return jsonify({"reports": reports_list}), 200

    except Exception as e:
        print(f"Error in get_reports: {e}")
        # Fallback to mock-like data to avoid breaking the frontend
        fallback_reports = [
            {
                "id": "R-01",
                "title": "Nyeri County Accountability Report FY2024/25",
                "category": "Accountability Reports",
                "entity": "Nyeri County",
                "financialYear": "2024/25",
                "datePublished": "2025-08-12"
            },
            {
                "id": "R-02",
                "title": "Mathira NG-CDF Audit Summary FY2023/24",
                "category": "Auditor-General Reports",
                "entity": "Mathira",
                "financialYear": "2023/24",
                "datePublished": "2024-11-03"
            }
        ]
        return jsonify({"reports": fallback_reports}), 200