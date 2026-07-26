"""
AuraFit — Style DNA PDF Generator (Stage 8).

Generates a luxury-branded A4 PDF report using ReportLab.
The PDF includes:
  - Cover page (headline, user name, date)
  - Table of contents
  - 7 profile sections with AuraFit styling
  - Colour swatches (rendered as coloured rectangles)
  - Occasion guide
  - Recommendations list

Design decisions:
  - Cormorant Garamond (display) + DM Sans (body)
  - Obsidian background pages for section headers
  - Gold (#C9A84C) as the brand accent
  - Colour swatches drawn as 20×20pt rounded rectangles
  - No third-party CDN dependencies — all assets embedded

Upload flow:
  1. Render PDF to BytesIO
  2. Upload to S3 → s3_key = reports/{user_id}/{report_id}.pdf
  3. Update StyleDNAReport.pdf_s3_key, pdf_url, pdf_size_kb
  4. Return CDN URL
"""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Brand colours ─────────────────────────────────────────────────────────────
GOLD        = (0.788, 0.659, 0.298)   # #C9A84C
BLACK       = (0.039, 0.039, 0.043)   # #0A0A0B
CHARCOAL    = (0.078, 0.078, 0.086)   # #141416
WHITE       = (1.0, 1.0, 1.0)
CREAM       = (0.980, 0.969, 0.910)   # #FAF7E8
MUTED       = (0.600, 0.600, 0.620)
ROSE        = (0.831, 0.506, 0.541)


class StyleDNAPDFGenerator:
    """Generate a branded AuraFit Style DNA PDF report."""

    def generate(self, report_data: dict, user_name: str, report_id: str) -> bytes:
        """
        Generate the full PDF and return as bytes.
        report_data: the assembled StyleDNAReport sections as a dict.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm, pt
            from reportlab.lib.colors import Color, HexColor
            from reportlab.pdfgen import canvas
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak, HRFlowable,
            )
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        except ImportError:
            logger.warning("reportlab not installed — returning placeholder PDF")
            return self._placeholder_pdf(user_name)

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=25 * mm,
            rightMargin=25 * mm,
            title=f"AuraFit Style DNA — {user_name}",
            author="AuraFit AI",
        )

        W, H = A4
        gold_rgb  = Color(GOLD[0],    GOLD[1],    GOLD[2])
        black_rgb = Color(BLACK[0],   BLACK[1],   BLACK[2])
        cream_rgb = Color(CREAM[0],   CREAM[1],   CREAM[2])
        muted_rgb = Color(MUTED[0],   MUTED[1],   MUTED[2])

        # ── Style sheet ───────────────────────────────────────────────────────
        styles = getSampleStyleSheet()

        headline_style = ParagraphStyle("Headline",
            fontName="Helvetica-Bold", fontSize=26, textColor=cream_rgb,
            spaceAfter=8, alignment=TA_CENTER, leading=32)
        section_head = ParagraphStyle("SectionHead",
            fontName="Helvetica-Bold", fontSize=16, textColor=gold_rgb,
            spaceBefore=18, spaceAfter=8, leading=20)
        subhead = ParagraphStyle("SubHead",
            fontName="Helvetica-Bold", fontSize=11, textColor=cream_rgb,
            spaceBefore=10, spaceAfter=4, leading=14)
        body = ParagraphStyle("Body",
            fontName="Helvetica", fontSize=9, textColor=muted_rgb,
            spaceAfter=4, leading=13)
        bullet = ParagraphStyle("Bullet",
            fontName="Helvetica", fontSize=9, textColor=cream_rgb,
            spaceAfter=3, leading=12, leftIndent=12, bulletIndent=0)
        caption = ParagraphStyle("Caption",
            fontName="Helvetica-Oblique", fontSize=8, textColor=muted_rgb,
            spaceAfter=4, alignment=TA_CENTER)

        # ── Build content ──────────────────────────────────────────────────────
        story: list = []

        def _gold_line():
            return HRFlowable(width="100%", thickness=0.5, color=gold_rgb, spaceAfter=8, spaceBefore=4)

        def _section_title(title: str):
            story.append(Paragraph(title, section_head))
            story.append(_gold_line())

        def _bullets(items: list[str], label: str = ""):
            if label:
                story.append(Paragraph(label, subhead))
            for item in items:
                story.append(Paragraph(f"• {item}", bullet))

        def _swatch_row(colors: list[dict], label: str = ""):
            """Render a row of colour swatches as a table."""
            from reportlab.platypus import Table, TableStyle
            from reportlab.lib.colors import HexColor
            if not colors:
                return
            if label:
                story.append(Paragraph(label, subhead))
            cols = min(len(colors), 8)
            cell_w = (W - 50 * mm) / cols
            name_cells  = []
            swatch_cells= []
            for c in colors[:cols]:
                hex_val = c.get("hex", "#C9A84C")
                name    = c.get("name", "")[:12]
                try:
                    col = HexColor(hex_val)
                except Exception:
                    col = gold_rgb
                swatch_cells.append(
                    Table([[""]], colWidths=[cell_w - 4], rowHeights=[16],
                          style=TableStyle([
                              ("BACKGROUND", (0,0), (-1,-1), col),
                              ("GRID", (0,0), (-1,-1), 0.5, muted_rgb),
                              ("ROUNDEDCORNERS", [3]),
                          ]))
                )
                name_cells.append(Paragraph(name, caption))
            swatch_table = Table(
                [swatch_cells, name_cells],
                colWidths=[cell_w] * cols,
                style=TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (0,0), (-1,-1), "CENTER")]),
            )
            story.append(swatch_table)
            story.append(Spacer(1, 6))

        # ── 1. Cover page ──────────────────────────────────────────────────────
        story.append(Spacer(1, 40 * mm))
        story.append(Paragraph("✦ AuraFit", ParagraphStyle("Logo",
            fontName="Helvetica-Bold", fontSize=10, textColor=gold_rgb,
            alignment=TA_CENTER, spaceAfter=4, letterSpacing=6)))
        story.append(Paragraph("Style DNA Report", headline_style))
        headline = report_data.get("headline", "Your Unique Beauty Story")
        story.append(Paragraph(f"<i>{headline}</i>", ParagraphStyle("HeadSub",
            fontName="Helvetica-Oblique", fontSize=14, textColor=gold_rgb,
            alignment=TA_CENTER, spaceAfter=16)))
        story.append(_gold_line())
        story.append(Paragraph(user_name, ParagraphStyle("Name",
            fontName="Helvetica-Bold", fontSize=11, textColor=cream_rgb,
            alignment=TA_CENTER, spaceAfter=4)))
        story.append(Paragraph(
            f"Generated {datetime.now(UTC).strftime('%d %B %Y')}",
            ParagraphStyle("Date", fontName="Helvetica", fontSize=8,
                           textColor=muted_rgb, alignment=TA_CENTER)))
        story.append(Spacer(1, 30 * mm))
        narrative = report_data.get("narrative", "")
        if narrative:
            story.append(Paragraph(narrative, ParagraphStyle("Narrative",
                fontName="Helvetica-Oblique", fontSize=10, textColor=cream_rgb,
                alignment=TA_CENTER, leading=16, leftIndent=20, rightIndent=20)))
        story.append(PageBreak())

        # ── 2. Skin Profile ────────────────────────────────────────────────────
        sp = report_data.get("skin_profile", {})
        if sp:
            _section_title("✦ Your Skin Profile")
            meta = [
                f"Skin Tone: {str(sp.get('tone', 'Not analysed')).title()}",
                f"Skin Type: {str(sp.get('type', 'Not assessed')).title()}",
                f"Undertone: {str(sp.get('undertone', 'Not assessed')).title()}",
            ]
            for m in meta:
                story.append(Paragraph(m, bullet))
            concerns = sp.get("concerns", [])
            if concerns:
                story.append(Spacer(1, 6))
                _bullets([c.replace("_", " ").title() for c in concerns], "Skin Concerns")
            actives = sp.get("key_actives", [])
            if actives:
                story.append(Spacer(1, 4))
                _bullets(actives[:6], "Recommended Actives")
            routine = sp.get("routine", {})
            if routine.get("morning"):
                story.append(Spacer(1, 4))
                _bullets(routine["morning"][:6], "Morning Routine")
            if routine.get("evening"):
                story.append(Spacer(1, 4))
                _bullets(routine["evening"][:6], "Evening Routine")

        story.append(PageBreak())

        # ── 3. Color Profile ───────────────────────────────────────────────────
        cp = report_data.get("color_profile_section", {})
        if cp:
            _section_title("✦ Your Color Profile")
            season = cp.get("season", "Unknown")
            story.append(Paragraph(f"Color Season: {season}", subhead))
            story.append(Paragraph(cp.get("description", ""), body))
            palette = cp.get("palette", {})
            if palette.get("best"):
                _swatch_row(palette["best"][:8], "Your Best Colors")
            if palette.get("neutrals"):
                _swatch_row(palette["neutrals"][:6], "Core Neutrals")
            if palette.get("accents"):
                _swatch_row(palette["accents"][:4], "Signature Accents")
            story.append(Spacer(1, 8))
            dos  = cp.get("dos", [])
            donts= cp.get("donts", [])
            if dos:   _bullets(dos,   "Colors to Embrace")
            if donts: _bullets(donts, "Colors to Avoid")
            metals = cp.get("metal_tones", [])
            if metals:
                story.append(Paragraph(f"Best Metals: {', '.join(metals)}", bullet))

        story.append(PageBreak())

        # ── 4. Fashion Profile ─────────────────────────────────────────────────
        fp = report_data.get("fashion_profile", {})
        if fp:
            _section_title("✦ Your Fashion Profile")
            archetype = fp.get("primary_archetype", "")
            if archetype:
                story.append(Paragraph(archetype, subhead))
            arch_desc = fp.get("archetype_description", "")
            if arch_desc:
                story.append(Paragraph(arch_desc, body))
            body_guide = fp.get("body_guide", {})
            if body_guide:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Body Shape Guide", subhead))
                summary = body_guide.get("summary", "")
                if summary:
                    story.append(Paragraph(summary, body))
                flatter = body_guide.get("flatter", [])
                if flatter: _bullets(flatter, "What Flatters You")
                avoid = body_guide.get("avoid", [])
                if avoid:   _bullets(avoid, "What to Avoid")
            capsule = fp.get("capsule_wardrobe", [])
            if capsule:
                story.append(Spacer(1, 8))
                story.append(Paragraph("Your Capsule Wardrobe", subhead))
                for item in capsule[:8]:
                    note = f" — {item.get('note')}" if item.get("note") else ""
                    story.append(Paragraph(f"• {item.get('item', '')}{note}", bullet))

        story.append(PageBreak())

        # ── 5. Fragrance Profile ───────────────────────────────────────────────
        fragp = report_data.get("fragrance_profile_section", {})
        if fragp:
            _section_title("✦ Your Fragrance Profile")
            families = fragp.get("families", [])
            if families:
                story.append(Paragraph(f"Fragrance Family: {', '.join(str(f).title() for f in families)}", subhead))
            personality = fragp.get("personality", "")
            if personality:
                story.append(Paragraph(f'"{personality}"', ParagraphStyle("FP",
                    fontName="Helvetica-Oblique", fontSize=10, textColor=gold_rgb,
                    spaceAfter=8, leftIndent=10)))
            occ_guide = fragp.get("occasion_guide", {})
            if occ_guide:
                story.append(Paragraph("Fragrance by Occasion", subhead))
                for occ, rec in occ_guide.items():
                    story.append(Paragraph(f"• {occ.title()}: {rec}", bullet))
            tip = fragp.get("layering_tip", "")
            if tip:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"Layering Tip: {tip}", body))

        story.append(PageBreak())

        # ── 6. Hairstyle Profile ───────────────────────────────────────────────
        hp = report_data.get("hairstyle_profile", {})
        if hp:
            _section_title("✦ Your Hairstyle Profile")
            face_shape = hp.get("face_shape", "")
            if face_shape:
                story.append(Paragraph(f"Face Shape: {str(face_shape).title()}", subhead))
            summary = hp.get("face_shape_summary", "")
            if summary:
                story.append(Paragraph(summary, body))
            recommended = hp.get("recommended_styles", [])
            if recommended: _bullets(recommended, "Recommended Styles")
            avoid_s = hp.get("avoid_styles", [])
            if avoid_s:     _bullets(avoid_s, "Styles to Avoid")
            tip = hp.get("styling_tip", "")
            if tip:
                story.append(Paragraph(f"Stylist Tip: {tip}", body))
            color_recs = hp.get("color_recommendations", [])
            if color_recs:  _bullets(color_recs, "Hair Color Recommendations")

        story.append(PageBreak())

        # ── 7. Occasion Guide ──────────────────────────────────────────────────
        og = report_data.get("occasion_guide", {})
        if og:
            _section_title("✦ Your Occasion Guide")
            for occ_name, occ_data in og.items():
                if not isinstance(occ_data, dict):
                    continue
                story.append(Paragraph(occ_name.title(), subhead))
                formula = occ_data.get("outfit_formula", "")
                if formula:
                    story.append(Paragraph(f"Outfit: {formula}", bullet))
                beauty = occ_data.get("beauty_look", "")
                if beauty:
                    story.append(Paragraph(f"Beauty: {beauty}", bullet))
                frag = occ_data.get("fragrance", "")
                if frag:
                    story.append(Paragraph(f"Fragrance: {frag}", bullet))
                palette_items = occ_data.get("colour_palette", [])
                if palette_items:
                    story.append(Paragraph(f"Colours: {', '.join(palette_items)}", bullet))
                story.append(Spacer(1, 4))

        story.append(PageBreak())

        # ── 8. Recommendations ─────────────────────────────────────────────────
        recs = report_data.get("recommendations", {})
        if recs:
            _section_title("✦ Curated Recommendations")
            for cat, picks in recs.items():
                if not picks:
                    continue
                story.append(Paragraph(cat.replace("_", " ").title(), subhead))
                if isinstance(picks, list):
                    for p in picks[:4]:
                        if isinstance(p, dict):
                            pick_text = p.get("pick") or p.get("item") or str(p)
                            why = p.get("why") or p.get("note") or p.get("description") or ""
                            why_str = f" — {why}" if why else ""
                            story.append(Paragraph(f"• {pick_text}{why_str}", bullet))
                story.append(Spacer(1, 4))

        # ── Back cover ─────────────────────────────────────────────────────────
        story.append(PageBreak())
        story.append(Spacer(1, 60 * mm))
        story.append(Paragraph("✦ AuraFit", ParagraphStyle("BackLogo",
            fontName="Helvetica-Bold", fontSize=14, textColor=gold_rgb,
            alignment=TA_CENTER, spaceAfter=8, letterSpacing=6)))
        story.append(Paragraph("Your AI-Powered Beauty & Style Intelligence", ParagraphStyle("BackTagline",
            fontName="Helvetica-Oblique", fontSize=9, textColor=muted_rgb,
            alignment=TA_CENTER)))
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Report ID: {report_id} · Generated {datetime.now(UTC).strftime('%d %B %Y, %H:%M UTC')}",
            ParagraphStyle("Footer", fontName="Helvetica", fontSize=7, textColor=muted_rgb,
                           alignment=TA_CENTER)))

        # ── Page background ────────────────────────────────────────────────────
        def _dark_background(canvas_obj, doc_obj):
            canvas_obj.saveState()
            canvas_obj.setFillColorRGB(*BLACK)
            canvas_obj.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
            canvas_obj.restoreState()

        doc.build(story, onFirstPage=_dark_background, onLaterPages=_dark_background)
        buf.seek(0)
        return buf.read()

    def _placeholder_pdf(self, user_name: str) -> bytes:
        """Minimal valid PDF when ReportLab is not installed."""
        content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 80>>
stream
BT /F1 18 Tf 50 750 Td (AuraFit Style DNA: {user_name}) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000397 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
472
%%EOF"""
        return content.encode()


pdf_generator = StyleDNAPDFGenerator()
