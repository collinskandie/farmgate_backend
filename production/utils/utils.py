

from datetime import date
from django.db.models import Sum
from production.models import MilkRecord
from production.utils.pdf import MilkProductionPDFReport


def generate_milk_report(farm):
    report = MilkProductionPDFReport(farm)
    pdf_path = report.generate()

    today = date.today()
    total = (
        MilkRecord.objects
        .filter(cow__farm=farm, date=today)
        .aggregate(total=Sum("quantity_in_liters"))["total"]
        or 0
    )

    return pdf_path, total
