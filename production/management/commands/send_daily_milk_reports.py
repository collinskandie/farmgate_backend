from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
import os
import requests
from decouple import config

from accounts.models import Account
from production.utils.pdf import MilkProductionPDFReport


class Command(BaseCommand):
    help = "Send daily milk production reports to account phone numbers"

    def handle(self, *args, **options):
        today = date.today()
        self.stdout.write(f"📊 Sending daily farm reports for {today}")

        accounts = Account.objects.filter(is_active=True)

        for account in accounts:
            if not account.phone:
                continue

            farms = account.farms.all()
            if not farms.exists():
                continue

            for farm in farms:
                try:
                    self.send_farm_report(account, farm)
                    self.stdout.write(
                        f"✅ Sent report for farm '{farm.name}' to {account.phone}"
                    )
                except Exception as e:
                    self.stderr.write(
                        f"❌ Failed for farm '{farm.name}' ({account.phone}): {e}"
                    )

    # --------------------------------------------------
    # WhatsApp helpers
    # --------------------------------------------------
    def send_farm_report(self, account, farm):
        from django.conf import settings

        # 1️⃣ Generate PDF
        report = MilkProductionPDFReport(farm)
        pdf_path = report.generate()

        # 2️⃣ Upload PDF
        media_id = self.upload_pdf(pdf_path)

        # 3️⃣ Send intro message
        self.send_text(
            account.phone,
            (
                f"📊 *Daily Milk Production Report*\n\n"
                f"Farm: {farm.name}\n"
                f"Date: {timezone.now().date()}\n\n"
                f"📄 Detailed report attached below."
            ),
        )

        # 4️⃣ Send PDF
        self.send_pdf(account.phone, media_id)

    def upload_pdf(self, file_path):
        from django.conf import settings

        url = f"https://graph.facebook.com/v18.0/{config('PHONE_NUMBER_ID')}/media"

        headers = {
            "Authorization": f"Bearer {config('WHATS_APP_API_KEY')}",
        }

        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                headers=headers,
                files={
                    "file": (
                        os.path.basename(file_path),
                        f,
                        "application/pdf",
                    )
                },
                data={"messaging_product": "whatsapp"},
            )

        response.raise_for_status()
        return response.json()["id"]

    def send_text(self, phone, text):
        from django.conf import settings

        requests.post(
            f"https://graph.facebook.com/v18.0/{config('PHONE_NUMBER_ID')}/messages",
            headers={
                "Authorization": f"Bearer {config('WHATS_APP_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "text": {"body": text},
            },
        )

    def send_pdf(self, phone, media_id):
        from django.conf import settings

        requests.post(
            f"https://graph.facebook.com/v18.0/{config('PHONE_NUMBER_ID')}/messages",
            headers={
                "Authorization": f"Bearer {config('WHATS_APP_API_KEY')}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "document",
                "document": {
                    "id": media_id,
                    "caption": "📊 Daily Milk Production Report",
                },
            },
        )
