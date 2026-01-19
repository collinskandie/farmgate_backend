# production/utils/pdf.py
import os
from datetime import date
from decimal import Decimal

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
                yesterday_val = self._get_daily_value(cow, session_key, yesterday)

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
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0A2E5C")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONT", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),

            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 8),

            # TOTAL row
            ("BACKGROUND", (0,-1), (-1,-1), colors.lightgrey),
            ("FONT", (0,-1), (-1,-1), "Helvetica-Bold"),
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

    # ==================================================
    # 📄 Build PDF
    # ==================================================
    def generate(self):
        doc = SimpleDocTemplate(
            self.file_path,
            pagesize=A4
        )

        elements = []

        # # Logo (optional)
        # logo_path = os.path.join(settings.BASE_DIR, "static/logo.png")
        # if os.path.exists(logo_path):
        #     elements.append(
        #         Image(logo_path, width=4*cm, height=4*cm)
        #     )

        elements.append(Spacer(1, 12))

        # Header
        elements.append(
            Paragraph(
                f"<b>Milk Production Report</b><br/>"
                f"{self.farm.name}<br/>"
                f"{self.today}",
                self.styles["Title"]
            )
        )

        elements.append(Spacer(1, 16))

        # Summary
        morning, evening, total = self._get_totals()

        elements.append(Spacer(1, 20))

    
        table, best, worst = self._build_analytical_table()

        elements.append(table)
        elements.append(Spacer(1, 24))
        elements.append(self._build_narration(best, worst))


        # Build
        doc.build(
            elements,
            onFirstPage=self._footer,
            onLaterPages=self._footer
        )

        return self.file_path
