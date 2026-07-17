from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.utils import ImageReader
import io
try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None

from config import REPORTS_DIR, UPLOADS_DIR


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
    # Header: logo left, title centered, date right
    logo_width = 48
    logo_height = 48
    if logo_path.exists():
        try:
            canvas.drawImage(str(logo_path), 36, height - logo_height - 18, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFont("Helvetica", 8)

    # Footer: page number
    page_num_text = f"Page {doc.page}"
    canvas.drawCentredString(width / 2.0, 20, page_num_text)
    canvas.restoreState()


def _add_image(file_path, max_w=380, max_h=240):
    file_path = Path(file_path)
    if not file_path.exists():
        alt = UPLOADS_DIR / file_path.name if UPLOADS_DIR else file_path
        if alt.exists():
            file_path = alt
    if not file_path.exists():
        return Paragraph(f"Missing photo file: {file_path}", getSampleStyleSheet()["Normal"])

    try:
        return RLImage(str(file_path), width=max_w, height=max_h)
    except Exception:
        if PILImage:
            try:
                with PILImage.open(file_path) as im:
                    im_conv = im.convert("RGB")
                    w, h = im_conv.size
                    ratio = min(max_w / w, max_h / h)
                    new_w = int(w * ratio)
                    new_h = int(h * ratio)
                    im_resized = im_conv.resize((new_w, new_h))
                    buf = io.BytesIO()
                    im_resized.save(buf, format="JPEG")
                    buf.seek(0)
                    img_reader = ImageReader(buf)
                    return RLImage(img_reader, width=new_w, height=new_h)
            except Exception:
                return Paragraph("Photo could not be rendered.", getSampleStyleSheet()["Normal"])
        return Paragraph("Photo could not be rendered.", getSampleStyleSheet()["Normal"])


def create_report_pdf(inspection_id, vehicle, inspection, items, photos):
    def _sanitize_filename(s: str) -> str:
        return "".join(c if (c.isalnum() or c in ('-', '_')) else '_' for c in (s or ""))

    vin = vehicle.get('vin', '') or ''
    vin_safe = _sanitize_filename(vin)
    if vin_safe:
        filename = f"inspection_report_{vin_safe}.pdf"
    else:
        filename = "inspection_report.pdf"
    report_path = REPORTS_DIR / filename
    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=72,
        bottomMargin=48,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    h1 = ParagraphStyle("ReportTitle", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=20, spaceAfter=12)
    h2 = ParagraphStyle("SectionTitle", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#2E7D7D"), spaceAfter=8)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9)

    story = []

    # Cover Page
    logo_path = Path(__file__).resolve().parent.parent / "assets" / "logo.png"
    if logo_path.exists():
        try:
            story.append(RLImage(str(logo_path), width=100, height=60))
        except Exception:
            pass
    story.append(Spacer(1, 12))
    story.append(Paragraph("Inspection Report", h1))
    story.append(Spacer(1, 6))
    info_table = [
        ["Field", "Value"],
        ["Make", vehicle.get('make', '')],
        ["Model", vehicle.get('model', '')],
        ["Year", vehicle.get('year', '')],
        ["VIN", vehicle.get('vin', '')],
        ["Engine", vehicle.get('engine', '')],
        ["Odometer reading", vehicle.get('odometer', '')],
        ["Transmission type", vehicle.get('transmission', '')],
        ["Fuel type", vehicle.get('fuel_type', '')],
        ["Color", vehicle.get('color', '')],
        ["Interior type", vehicle.get('interior_type', '')],
        ["Accident history", vehicle.get('accident_history', '')],
    ]
    table = Table(info_table, hAlign='LEFT', colWidths=[140, 340], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D7D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 18))
    # Cover ends here. Inspector Notes stay on the same page, then move to the next section.
    story.append(Paragraph("Inspector Notes", h2))
    story.append(Paragraph(inspection.get("remarks", "No summary notes were provided."), normal))

    story.append(PageBreak())

    # Findings Section (grouped by category; part names hidden)
    story.append(Paragraph("Inspection Findings", h2))
    story.append(Spacer(1, 6))

    if items:
        # Group items by category and aggregate remarks
        grouped = {}
        for item in items:
            cat = item.get("category", "Uncategorized")
            grouped.setdefault(cat, []).append(item)

        # track images already inserted to avoid duplicates
        used_paths = set()

        for cat_idx, (category, cat_items) in enumerate(grouped.items(), start=1):
            story.append(Paragraph(f"{cat_idx}. {category}", styles["Heading3"]))
            # Aggregate non-empty remarks for the category
            remarks_list = [it.get('remarks', '').strip() for it in cat_items if it.get('remarks') and it.get('remarks').strip()]
            if remarks_list:
                combined = "; ".join(dict.fromkeys(remarks_list))
                story.append(Paragraph(f"Remarks: {combined}", small))
            else:
                story.append(Paragraph("No remarks recorded for this category.", small))

            # Attach photos that belong to this category (do not reference individual part names)
            matched = [p for p in photos if p.get('category') == category]
            if matched:
                for mp in matched:
                    fp = mp.get('file_path') or ''
                    if fp in used_paths:
                        continue
                    story.append(_add_image(fp))
                    used_paths.add(fp)
                    if mp.get('remarks'):
                        story.append(Paragraph(mp.get('remarks'), small))
                    story.append(Spacer(1, 6))
            else:
                story.append(Paragraph("No photos for this category.", small))

            story.append(Spacer(1, 12))
        story.append(PageBreak())
    else:
        story.append(Paragraph("No inspection findings available.", normal))
        story.append(PageBreak())

    # All Photos Appendix
    story.append(Paragraph("Appendix: All Inspection Photos", h2))
    story.append(Spacer(1, 6))
    if photos:
        for idx, photo in enumerate(photos, start=1):
            fp = photo.get('file_path') or ''
            if fp in used_paths:
                continue
            story.append(Paragraph(f"Photo {idx}: {photo.get('caption', Path(fp).name)}", styles["Heading4"]))
            story.append(_add_image(fp))
            if photo.get('remarks'):
                story.append(Paragraph(photo.get('remarks'), small))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No photos uploaded for this inspection.", normal))

    

    story.append(Spacer(1, 12))
    story.append(Paragraph("End of Report", styles["Heading4"]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return report_path
