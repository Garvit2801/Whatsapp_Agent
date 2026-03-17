from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def _para(text: str, style):
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(safe.replace("\n", "<br/>"), style)

def generate_validation_report_pdf(
    output_path: str,
    repo_name: str,
    branch_name: str,
    goal: str,
    written_files: list[str],
    deleted_files: list[str],
    changed_files: list[str],
    command_results: list[dict],
) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["BodyText"],
        fontSize=10,
        leading=13,
        spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "SmallCustom",
        parent=styles["BodyText"],
        fontSize=9,
        leading=11,
    )

    story = []
    story.append(Paragraph("Validation Report", title_style))
    story.append(Spacer(1, 6))

    meta_rows = [
        [_para("Repo", body_style), _para(repo_name, body_style)],
        [_para("Branch", body_style), _para(branch_name, body_style)],
        [_para("Goal", body_style), _para(goal, body_style)],
    ]
    meta_table = Table(meta_rows, colWidths=[32 * mm, 145 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    def add_list_section(title: str, values: list[str]):
        story.append(Paragraph(title, heading_style))
        if values:
            for item in values:
                story.append(_para(f"- {item}", body_style))
        else:
            story.append(_para("None", body_style))
        story.append(Spacer(1, 6))

    add_list_section("Files written", written_files)
    add_list_section("Files deleted", deleted_files)
    add_list_section("Git status after run", changed_files)

    story.append(Paragraph("Validation commands", heading_style))
    if command_results:
        rows = [[
            _para("Command", small_style),
            _para("Result", small_style),
            _para("Output", small_style),
        ]]
        for item in command_results:
            status = "PASS" if item.get("success") else "FAIL"
            output = (item.get("stdout") or item.get("stderr") or item.get("message") or "").strip()
            output = output[:500] if output else "-"
            rows.append([
                _para(item.get("command", "-"), small_style),
                _para(status, small_style),
                _para(output, small_style),
            ])

        table = Table(rows, colWidths=[70 * mm, 22 * mm, 88 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#D1D5DB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        story.append(_para("No validation commands were run.", body_style))

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    doc.build(story)
    return str(path)