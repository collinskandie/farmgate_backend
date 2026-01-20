# production/utils/pdf.py
import os
from datetime import date
from decimal import Decimal
from reportlab.lib.pagesizes import A4, landscape
from reportlab.graphics.charts.piecharts import Pie

from django.conf import settings
from django.db.models import Sum
from datetime import timedelta
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.styles import ParagraphStyle
from production.models import MilkRecord
from accounts.models import Cow


class MilkProductionPDFReport:
    """
    Generates a branded, analytical milk production PDF report
    suitable for WhatsApp delivery.
    """

    def __init__(self, farm):
        self.farm = farm
        self.today = date.today()
        self.styles = getSampleStyleSheet()
        self.styles.add(
            ParagraphStyle(
                name="Cell",
                fontSize=9,
                alignment=1,  # center
            )
        )

        reports_dir = os.path.join(settings.MEDIA_ROOT, "reports")

        os.makedirs(reports_dir, exist_ok=True)

        self.file_path = os.path.join(
            reports_dir,
            f"milk_report_farm_{farm.id}_{self.today}.pdf"
        )

    # ==================================================
    # 📊 Data aggregation
    # ==================================================

    def _get_totals(self):
        totals = (
            MilkRecord.objects
            .filter(cow__farm=self.farm, date=self.today)
            .values("session")
            .annotate(total=Sum("quantity_in_liters"))
        )

        morning = sum(
            r["total"] for r in totals if r["session"] == MilkRecord.MORNING
        ) or Decimal("0")

        evening = sum(
            r["total"] for r in totals if r["session"] == MilkRecord.EVENING
        ) or Decimal("0")

        return morning, evening, morning + evening

    # ==================================================
    # 📈 Chart
    # ==================================================
    def _build_chart(self, morning, evening):
        drawing = Drawing(400, 200)

        chart = VerticalBarChart()
        chart.data = [[float(morning), float(evening)]]
        chart.categoryAxis.categoryNames = ["Morning", "Evening"]
        chart.valueAxis.valueMin = 0
        chart.barWidth = 40
        chart.x = 50
        chart.y = 50
        chart.height = 100
        chart.width = 300

        drawing.add(chart)
        return drawing
    
    def _build_pie_chart(self, morning, noon, evening):
        drawing = Drawing(300, 200)

        pie = Pie()
        pie.x = 65
        pie.y = 15
        pie.width = 170
        pie.height = 170

        pie.data = [
            float(morning),
            float(noon),
            float(evening),
        ]

        pie.labels = ["Morning", "Noon", "Evening"]
        pie.slices.strokeWidth = 0.5

        pie.slices[0].fillColor = colors.HexColor("#1f77b4")
        pie.slices[1].fillColor = colors.HexColor("#ff7f0e")
        pie.slices[2].fillColor = colors.HexColor("#2ca02c")

        drawing.add(pie)
        return drawing


    # ==================================================
    # 🐄 Table
    # ==================================================
    def _build_analytical_table(self):
        cows = Cow.objects.filter(farm=self.farm).order_by("id")
        yesterday = self.today - timedelta(days=1)

        table_data = [[
            "Cow",
            "Morning (L)",
            "Noon (L)",
            "Evening (L)",
            "Total (L)"
        ]]

        totals = {
            "morning": Decimal("0"),
            "noon": Decimal("0"),
            "evening": Decimal("0"),
            "total": Decimal("0"),
        }

        best_improvement = None
        worst_decline = None

        for cow in cows:
            row = [cow.name if hasattr(cow, "name") else cow.tag_number]
            cow_total = Decimal("0")

            for session_key, label in [
                (MilkRecord.MORNING, "morning"),
                (MilkRecord.AFTERNOON, "noon"),
                (MilkRecord.EVENING, "evening"),
            ]:
                today_val = self._get_daily_value(cow, session_key, self.today)
                yesterday_val = self._get_daily_value(
                    cow, session_key, yesterday)

                diff = today_val - yesterday_val
                # arrow = "↑" if diff > 0 else "↓" if diff < 0 else "→"

                # cell = f"{today_val:.2f} [{diff:+.2f}] {arrow}"
                if diff > 0:
                    arrow = '<font color="green">↑</font>'
                elif diff < 0:
                    arrow = '<font color="red">↓</font>'
                else:
                    arrow = '<font color="grey">→</font>'

                cell = Paragraph(
                    f"{today_val:.2f} [{diff:+.2f}] {arrow}",
                    self.styles["Cell"]
                )

                row.append(cell)

                totals[label] += today_val
                cow_total += today_val

            # Total column
            yesterday_total = (
                self._get_daily_value(cow, MilkRecord.MORNING, yesterday) +
                self._get_daily_value(cow, MilkRecord.AFTERNOON, yesterday) +
                self._get_daily_value(cow, MilkRecord.EVENING, yesterday)
            )

            total_diff = cow_total - yesterday_total
            arrow = "↑" if total_diff > 0 else "↓" if total_diff < 0 else "→"

            row.append(f"{cow_total:.2f} [{total_diff:+.2f}] {arrow}")
            totals["total"] += cow_total

            # Track narration candidates
            if not best_improvement or total_diff > best_improvement[1]:
                best_improvement = (cow, total_diff)

            if not worst_decline or total_diff < worst_decline[1]:
                worst_decline = (cow, total_diff)

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
            colWidths=[
                3.2*cm,  # Cow name
                3.2*cm,  # Morning
                3.2*cm,  # Noon
                3.2*cm,  # Evening
                3.2*cm,  # Total
            ],
            repeatRows=1
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A2E5C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),

            # TOTAL row
            ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
            ("FONT", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))

        return table, best_improvement, worst_decline

    def _build_narration(self, best, worst):
        lines = ["<b>Performance Summary:</b>"]

        if best and best[1] > 0:
            lines.append(
                f"{best[0].name} showed the most improvement in total yield compared to yesterday."
            )

        if worst and worst[1] < 0:
            lines.append(
                f"{worst[0].name} recorded the largest decrease in milk yield."
            )

        if best and worst and best[1] + worst[1] < 0:
            lines.append("Overall herd performance has declined.")

        return Paragraph(
            "<para align='center'><b>Performance Summary:</b><br/>" +
            "<br/>".join(lines[1:]) +
            "</para>",
            self.styles["Normal"]
        )

    def _get_daily_value(self, cow, session, target_date):
        return (
            MilkRecord.objects
            .filter(
                cow=cow,
                date=target_date,
                session=session
            )
            .aggregate(total=Sum("quantity_in_liters"))["total"]
            or Decimal("0")
        )

    # ==================================================
    # 🖨️ Footer
    # ==================================================

    def _footer(self, canvas, doc):
        canvas.setFont("Helvetica", 9)
        canvas.drawString(
            2*cm, 1.2*cm,
            "Generated by Farmgate • Confidential"
        )
    
    def _get_total_for_date(self, target_date):
        total = (
            MilkRecord.objects
            .filter(cow__farm=self.farm, date=target_date)
            .aggregate(total=Sum("quantity_in_liters"))["total"]
            or Decimal("0")
        )
        return total
    
    def _build_comparison_chart(self, yesterday_total, today_total):
        drawing = Drawing(400, 220)

        chart = VerticalBarChart()
        chart.data = [[float(yesterday_total), float(today_total)]]
        chart.categoryAxis.categoryNames = ["Yesterday", "Today"]

        chart.valueAxis.valueMin = 0
        chart.barWidth = 40
        chart.groupSpacing = 20

        chart.x = 50
        chart.y = 40
        chart.height = 120
        chart.width = 300

        chart.bars[0].fillColor = colors.HexColor("#0A2E5C")

        drawing.add(chart)
        return drawing



    # ==================================================
    # 📄 Build PDF
    # ==================================================
    # def generate(self):
    #     doc = SimpleDocTemplate(
    #         self.file_path,
    #         pagesize=landscape(A4),
    #         rightMargin=2*cm,
    #         leftMargin=2*cm,
    #         topMargin=2*cm,
    #         bottomMargin=2*cm,
    #     )

    #     elements = []
    #     elements.append(Spacer(1, 12))

    #     # Header
    #     elements.append(
    #         Paragraph(
    #             f"<b>Milk Production Report</b><br/>"
    #             f"{self.farm.name}<br/>"
    #             f"{self.today}",
    #             self.styles["Title"]
    #         )
    #     )

    #     elements.append(Spacer(1, 16))

    #     # Summary
    #     morning, evening, total = self._get_totals()

    #     elements.append(Spacer(1, 20))

    #     table, best, worst = self._build_analytical_table()

    #     elements.append(table)
    #     elements.append(Spacer(1, 24))
    #     elements.append(self._build_narration(best, worst))

    #     # Build
    #     doc.build(
    #         elements,
    #         onFirstPage=self._footer,
    #         onLaterPages=self._footer
    #     )

    #     return self.file_path
    def generate(self):
        doc = SimpleDocTemplate(
            self.file_path,
            pagesize=landscape(A4),
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
        )

        elements = []

        # =========================
        # Header
        # =========================
        header_style = ParagraphStyle(
            "Header",
            fontSize=18,
            alignment=1,
            spaceAfter=6,
        )

        subheader_style = ParagraphStyle(
            "SubHeader",
            fontSize=11,
            textColor=colors.grey,
            alignment=1,
        )

        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Milk Production Report", header_style))
        elements.append(
            Paragraph(
                f"{self.farm.name} &nbsp;&nbsp;•&nbsp;&nbsp; {self.today}",
                subheader_style,
            )
        )
        elements.append(Spacer(1, 20))


        # =========================
        # Data prep
        # =========================
        yesterday = self.today - timedelta(days=1)

        morning, evening, total_today = self._get_totals()
        noon = total_today - (morning + evening)

        yesterday_total = self._get_total_for_date(yesterday)

        # =========================
        # Analytical table
        # =========================
        table, best, worst = self._build_analytical_table()
        elements.append(table)
        elements.append(Spacer(1, 24))

        # =========================
        # Pie chart (AFTER table)
        # =========================
        elements.append(
            Paragraph("Milk Distribution (Today)", self.styles["Heading3"])
        )
        elements.append(
            self._build_pie_chart(morning, noon, evening)
        )
        elements.append(Spacer(1, 30))

        # =========================
        # Yesterday vs Today chart
        # =========================
        elements.append(
            Paragraph("Total Production Comparison", self.styles["Heading3"])
        )
        elements.append(
            self._build_comparison_chart(yesterday_total, total_today)
        )
        elements.append(Spacer(1, 36))

        # =========================
        # Narration (LAST)
        # =========================
        elements.append(self._build_narration(best, worst))

        # =========================
        # Build PDF
        # =========================
        doc.build(
            elements,
            onFirstPage=self._footer,
            onLaterPages=self._footer,
        )

        return self.file_path

