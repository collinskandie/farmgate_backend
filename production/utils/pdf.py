import os
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4
from pathlib import Path
from django.conf import settings
from django.db.models import Sum

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie

from production.models import MilkRecord
from accounts.models import Cow


class MilkProductionPDFReport:
    """
    Executive-style milk production report (WhatsApp friendly).
    """

    def __init__(self, farm):
        self.farm = farm
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)

        # -------------------------
        # Styles
        # -------------------------
        self.styles = getSampleStyleSheet()

        self.styles.add(ParagraphStyle(
            name="TitleMain",
            fontSize=18,
            alignment=1,
            spaceAfter=6,
        ))

        self.styles.add(ParagraphStyle(
            name="SubTitle",
            fontSize=11,
            alignment=1,
            textColor=colors.grey,
            spaceAfter=18,
        ))

        self.styles.add(ParagraphStyle(
            name="Cell",
            fontSize=9,
            alignment=1,
        ))

        self.styles.add(ParagraphStyle(
            name="Narration",
            fontSize=10,
            alignment=1,
            leading=14,
        ))

        # -------------------------
        # Output path (git ignored)
        # -------------------------
        reports_dir = Path(settings.MEDIA_ROOT) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = reports_dir / (
            f"milk_report_farm_{farm.id}_{self.today}_{uuid4().hex}.pdf"
        )

    # ==================================================
    # Data helpers
    # ==================================================
    def _get_value(self, cow, session, target_date):
        return (
            MilkRecord.objects
            .filter(cow=cow, date=target_date, session=session)
            .aggregate(total=Sum("quantity_in_liters"))["total"]
            or Decimal("0")
        )

    def _get_total_for_date(self, target_date):
        return (
            MilkRecord.objects
            .filter(cow__farm=self.farm, date=target_date)
            .aggregate(total=Sum("quantity_in_liters"))["total"]
            or Decimal("0")
        )

    # ==================================================
    # Analytical table
    # ==================================================
    def _build_table(self):
        cows = Cow.objects.filter(farm=self.farm).order_by("id")

        table_data = [[
            "Cow",
            "Morning (L)",
            "Noon (L)",
            "Evening (L)",
            "Total (L)",
        ]]

        totals = {
            "morning": Decimal("0"),
            "noon": Decimal("0"),
            "evening": Decimal("0"),
            "total": Decimal("0"),
        }

        best = None
        worst = None

        for cow in cows:
            row = [cow.name or cow.tag_number]
            cow_total = Decimal("0")

            for session, key in [
                (MilkRecord.MORNING, "morning"),
                (MilkRecord.AFTERNOON, "noon"),
                (MilkRecord.EVENING, "evening"),
            ]:
                today_val = self._get_value(cow, session, self.today)
                yesterday_val = self._get_value(cow, session, self.yesterday)
                diff = today_val - yesterday_val

                if diff > 0:
                    arrow = '<font color="green">↑</font>'
                elif diff < 0:
                    arrow = '<font color="red">↓</font>'
                else:
                    arrow = '<font color="grey">→</font>'

                cell = Paragraph(
                    f"{today_val:.2f} "
                    f"<font size='7'>({diff:+.2f})</font> {arrow}",
                    self.styles["Cell"],
                )

                row.append(cell)
                totals[key] += today_val
                cow_total += today_val

            yesterday_total = (
                self._get_value(cow, MilkRecord.MORNING, self.yesterday)
                + self._get_value(cow, MilkRecord.AFTERNOON, self.yesterday)
                + self._get_value(cow, MilkRecord.EVENING, self.yesterday)
            )

            total_diff = cow_total - yesterday_total

            row.append(
                Paragraph(
                    f"{cow_total:.2f} "
                    f"<font size='7'>({total_diff:+.2f})</font>",
                    self.styles["Cell"],
                )
            )

            totals["total"] += cow_total

            if not best or total_diff > best[1]:
                best = (cow, total_diff)
            if not worst or total_diff < worst[1]:
                worst = (cow, total_diff)

            table_data.append(row)

        # TOTAL ROW
        table_data.append([
            "TOTAL",
            f"{totals['morning']:.2f}",
            f"{totals['noon']:.2f}",
            f"{totals['evening']:.2f}",
            f"{totals['total']:.2f}",
        ])

        table = Table(
            table_data,
            colWidths=[4*cm, 4*cm, 4*cm, 4*cm, 4*cm],
            repeatRows=1,
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0A2E5C")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold"),

            ("ROWBACKGROUNDS", (0,1), (-1,-2),
             [colors.whitesmoke, colors.transparent]),

            ("FONT", (0,1), (0,-2), "Helvetica-Bold"),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),

            ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
            ("FONT", (0,-1), (-1,-1), "Helvetica-Bold"),
        ]))

        return table, best, worst, totals

    # ==================================================
    # Charts
    # ==================================================
    def _pie_chart(self, morning, noon, evening):
        d = Drawing(260, 180)
        pie = Pie()
        pie.x = 50
        pie.y = 10
        pie.width = 160
        pie.height = 160

        pie.data = [float(morning), float(noon), float(evening)]
        pie.labels = ["Morning", "Noon", "Evening"]
        pie.slices[0].fillColor = colors.HexColor("#1f77b4")
        pie.slices[1].fillColor = colors.HexColor("#ff7f0e")
        pie.slices[2].fillColor = colors.HexColor("#2ca02c")

        d.add(pie)
        return d

    def _comparison_chart(self, yesterday, today):
        d = Drawing(300, 200)
        chart = VerticalBarChart()
        chart.data = [[float(yesterday), float(today)]]
        chart.categoryAxis.categoryNames = ["Yesterday", "Today"]
        chart.valueAxis.valueMin = 0
        chart.barWidth = 40
        chart.groupSpacing = 30
        chart.x = 60
        chart.y = 40
        chart.height = 120
        chart.width = 180
        chart.bars[0].fillColor = colors.HexColor("#0A2E5C")

        d.add(chart)
        return d

    # ==================================================
    # Narration
    # ==================================================
    def _narration(self, best, worst):
        lines = ["<b>Performance Summary</b>"]

        if best and best[1] > 0:
            lines.append(
                f"{best[0].name} recorded the strongest improvement in milk yield."
            )

        if worst and worst[1] < 0:
            lines.append(
                f"{worst[0].name} recorded the largest decline in production."
            )

        return Paragraph("<br/>".join(lines), self.styles["Narration"])

    # ==================================================
    # Footer
    # ==================================================
    def _footer(self, canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.drawString(
            2*cm, 1.2*cm,
            "Generated by Farmgate • Confidential"
        )

    # ==================================================
    # Build PDF
    # ==================================================
    def generate(self):
        doc = SimpleDocTemplate(
            self.file_path,
            pagesize=landscape(A4),
            leftMargin=2*cm,
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        elements = []

        # Header
        elements.append(Paragraph("Milk Production Report", self.styles["TitleMain"]))
        elements.append(
            Paragraph(
                f"{self.farm.name} • {self.today}",
                self.styles["SubTitle"],
            )
        )

        # Table
        table, best, worst, totals = self._build_table()
        elements.append(table)
        elements.append(Spacer(1, 20))
        # Narration
        elements.append(
            Table(
                [[self._narration(best, worst)]],
                colWidths=[20*cm],
                style=[
                    ("BOX", (0,0), (-1,-1), 0.75, colors.HexColor("#0A2E5C")),
                    ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F4F7FB")),
                    ("PAD", (0,0), (-1,-1), 14),
                ],
            )
        )
        elements.append(Spacer(1, 10))

        # Charts
        # elements.append(Paragraph("Milk Distribution (Today)", self.styles["Heading3"]))
        # elements.append(self._pie_chart(
        #     totals["morning"],
        #     totals["noon"],
        #     totals["evening"],
        # ))
        # elements.append(Spacer(1, 24))

        # elements.append(Paragraph("Total Production Comparison", self.styles["Heading3"]))
        # elements.append(
        #     self._comparison_chart(
        #         self._get_total_for_date(self.yesterday),
        #         totals["total"],
        #     )
        # )
        # elements.append(Spacer(1, 30))
                # =========================
        # Charts (side by side)
        # =========================
        pie_chart = self._pie_chart(
            totals["morning"],
            totals["noon"],
            totals["evening"],
        )
        comparison_chart = self._comparison_chart(
            self._get_total_for_date(self.yesterday),
            totals["total"],
        )

        charts_table = Table(
            [
                [
                    Paragraph("Milk Distribution (Today)", self.styles["Heading3"]),
                    Paragraph("Total Production Comparison", self.styles["Heading3"]),
                ],
                [
                    pie_chart,
                    comparison_chart,
                ],
            ],
            colWidths=[10*cm, 10*cm],
        )

        charts_table.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

            # Optional framing (recommended)
            ("BOX", (0,1), (0,1), 0.5, colors.lightgrey),
            ("BOX", (1,1), (1,1), 0.5, colors.lightgrey),

            ("BACKGROUND", (0,1), (0,1), colors.whitesmoke),
            ("BACKGROUND", (1,1), (1,1), colors.whitesmoke),

            ("LEFTPADDING", (0,0), (-1,-1), 12),
            ("RIGHTPADDING", (0,0), (-1,-1), 12),
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))

        elements.append(charts_table)
        elements.append(Spacer(1, 5))
        doc.build(
            elements,
            onFirstPage=self._footer,
            onLaterPages=self._footer,
        )

        return self.file_path
