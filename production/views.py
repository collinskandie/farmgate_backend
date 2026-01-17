from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsSystemUser
from rest_framework import status
from accounts.models import Account, User, Farm, Cow
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import requests
from decouple import config
from datetime import date
from decimal import Decimal, InvalidOperation
from production.utils.pdf import MilkProductionPDFReport
from production.models import ChatSession, MilkRecord
from accounts.models import User, Cow, Farm
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum


# from rest_framework.views import APIView
import json

from production.serializers import MilkRecordSerializer

# Create your views here.


# class MilkRecordAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     # -----------------------------------------
#     # GET → List all milk records
#     # -----------------------------------------
#     def get(self, request):
#         records = MilkRecord.objects.select_related("cow").all()
#         serializer = MilkRecordSerializer(records, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     # -----------------------------------------
#     # POST → Create a milk record
#     # -----------------------------------------
#     def post(self, request):
#         serializer = MilkRecordSerializer(data=request.data)

#         if serializer.is_valid():
#             serializer.save(recorded_by=request.user)
#             return Response(
#                 serializer.data,
#                 status=status.HTTP_201_CREATED
#             )

#         return Response(
#             serializer.errors,
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # -----------------------------------------
#     # PUT → Update a milk record
#     # -----------------------------------------
#     def put(self, request, pk):
#         record = get_object_or_404(MilkRecord, pk=pk)

#         serializer = MilkRecordSerializer(
#             record,
#             data=request.data,
#             partial=True  # allows partial updates
#         )

#         if serializer.is_valid():
#             serializer.save()
#             return Response(
#                 serializer.data,
#                 status=status.HTTP_200_OK
#             )

#         return Response(
#             serializer.errors,
#             status=status.HTTP_400_BAD_REQUEST
#         )

class MilkRecordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        records = MilkRecord.objects.select_related(
            "cow",
            "cow__farm",
            "cow__farm__account"
        )

        # 🔓 System users see everything
        if user.is_system_user():
            pass  # no filtering, full access

        # 🔒 Tenant users are scoped to their account
        else:
            if not user.account:
                return Response(
                    {"detail": "User has no account assigned"},
                    status=status.HTTP_403_FORBIDDEN
                )

            records = records.filter(
                cow__farm__account=user.account
            )

        serializer = MilkRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

# class ProductionCallBack(APIView):
#     authentication_classes = []
#     permission_classes = []

#     PHONE_NUMBER_ID = "933662143166769"
#     ACCESS_TOKEN = ""

#     def get(self, request):
#         VERIFY_TOKEN = "framgatego_verify_token"

#         mode = request.GET.get("hub.mode")
#         token = request.GET.get("hub.verify_token")
#         challenge = request.GET.get("hub.challenge")

#         if mode == "subscribe" and token == VERIFY_TOKEN:
#             return HttpResponse(challenge)

#         return HttpResponse("Forbidden", status=403)

#     def post(self, request):
#         payload = request.data
#         print("🔥🔥🔥 POST WEBHOOK HIT 🔥🔥🔥")
#         print(request.data)

#         try:
#             entry = payload["entry"][0]
#             change = entry["changes"][0]
#             value = change["value"]

#             if "messages" not in value:
#                 return HttpResponse("No message", status=200)

#             message = value["messages"][0]

#             # 🔒 Safety check (important)
#             if message.get("type") != "text":
#                 return HttpResponse("Ignored", status=200)

#             from_number = message["from"]
#             text = message["text"]["body"]

#             print("Incoming:", from_number, text)

#             self.send_whatsapp_message(
#                 to=from_number,
#                 text="Hello 👋 Welcome to Farmgate!"
#             )

#         except Exception as e:
#             print("Webhook error:", e)

#         return HttpResponse("OK", status=200)

#     def send_whatsapp_message(self, to, text):
#         url = f"https://graph.facebook.com/v18.0/{self.PHONE_NUMBER_ID}/messages"

#         headers = {
#             "Authorization": f"Bearer {self.ACCESS_TOKEN}",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "messaging_product": "whatsapp",
#             "to": to,
#             "text": {"body": text}
#         }

#         response = requests.post(url, headers=headers, json=payload)
#         print("SEND STATUS:", response.status_code)
#         print("SEND BODY:", response.text)


# class ProductionCallBack(APIView):
#     authentication_classes = []
#     permission_classes = []
#     VERIFY_TOKEN = config('VERIFY_TOKEN')
#     PHONE_NUMBER_ID = config("PHONE_NUMBER_ID")
#     ACCESS_TOKEN = config('WHATS_APP_API_KEY')

#     # ==================================================
#     # 🔐 Webhook verification
#     # ==================================================
#     def get(self, request):
#         mode = request.GET.get("hub.mode")
#         token = request.GET.get("hub.verify_token")
#         challenge = request.GET.get("hub.challenge")

#         if mode == "subscribe" and token == self.VERIFY_TOKEN:
#             return HttpResponse(challenge)

#         return HttpResponse("Forbidden", status=403)

#     # ==================================================
#     # 📩 Incoming messages
#     # ==================================================
#     def post(self, request):
#         payload = request.data
#         print("🔥 POST WEBHOOK HIT")

#         try:
#             value = payload["entry"][0]["changes"][0]["value"]

#             if "messages" not in value:
#                 return HttpResponse("OK")

#             message = value["messages"][0]
#             if message.get("type") != "text":
#                 return HttpResponse("Ignored")

#             phone = message["from"]
#             text = message["text"]["body"].strip()

#             print("Incoming:", phone, text)
#             self.handle_message(phone, text)

#         except Exception as e:
#             print("Webhook error:", e)

#         return HttpResponse("OK")

#     # ==================================================
#     # 🧠 Conversation brain
#     # ==================================================
#     def handle_message(self, phone, text):
#         session, _ = ChatSession.objects.get_or_create(
#             phone=phone,
#             defaults={"step": "start"}
#         )

#         user = self.get_user_by_phone(phone)
#         if not user:
#             self.send_message(
#                 phone,
#                 "❌ Your phone number is not linked to any account. Please contact admin."
#             )
#             return
#         # -----------------------------------------------
#         # STEP 0: Resolve farm
#         # -----------------------------------------------
#         if session.step == "start":
#             farms = user.farms.all()

#             if not farms.exists():
#                 self.send_message(
#                     phone,
#                     "❌ You are not assigned to any farm."
#                 )
#                 return

#             # For now: auto-pick first farm
#             session.farm = farms.first()
#             session.step = "menu"
#             session.save()

#             self.send_message(
#                 phone,
#                 f"👋 Hello {user.full_name}\n\n"
#                 "What would you like to do?\n\n"
#                 "1️⃣ Enter milk production\n"
#                 "2️⃣ Report incident"
#             )
#             return

#         # -----------------------------------------------
#         # MENU
#         # -----------------------------------------------
#         if session.step == "menu":
#             if text == "1":
#                 session.step = "select_session"
#                 session.save()
#                 self.send_message(
#                     phone,
#                     "Select milk session:\n\n"
#                     "1️⃣ Morning\n"
#                     "2️⃣ Afternoon\n"
#                     "3️⃣ Evening"
#                 )
#                 return

#             if text == "2":
#                 session.step = "report_incident"
#                 session.save()
#                 self.send_message(phone, "Please describe the incident.")
#                 return

#             self.send_message(phone, "Please reply with 1 or 2.")
#             return

#         # -----------------------------------------------
#         # SESSION (Morning / Evening)
#         # -----------------------------------------------
#         if session.step == "select_session":
#             if text not in ["1", "2", "3"]:
#                 self.send_message(
#                     phone,
#                     f"👋 Hello {user.full_name}\n\n"
#                     "Please reply with 1 for Morning or 2 for Afternoon or 3 for Evening."
#                 )
#                 return

#             session.data["session"] = (
#                 MilkRecord.MORNING if text == "1" else MilkRecord.AFTERNOON if text == "2" else MilkRecord.EVENING
#             )
#             session.step = "enter_milk"
#             session.save()

#             cows = Cow.objects.filter(farm=session.farm).order_by("id")
#             if not cows.exists():
#                 self.send_message(phone, "❌ No cows found for this farm.")
#                 return

#             cow_list = "\n".join(
#                 [f"{i+1}. {cow.tag_number}" for i, cow in enumerate(cows)]
#             )

#             self.send_message(
#                 phone,
#                 "Enter milk amounts (litres) separated by commas "
#                 "in the SAME order as below:\n\n"
#                 f"{cow_list}\n\n"
#                 "Example: 10,8.5,9"
#             )
#             return

#         if session.step == "enter_milk":
#             cows = list(Cow.objects.filter(farm=session.farm).order_by("id"))

#             try:
#                 values = [Decimal(v.strip()) for v in text.split(",")]
#             except (InvalidOperation, ValueError):
#                 self.send_message(
#                     phone,
#                     "❌ Invalid format.\nExample: 10,8.5,9"
#                 )
#                 return

#             if len(values) != len(cows):
#                 self.send_message(
#                     phone,
#                     f"❌ You sent {len(values)} values but you have {len(cows)} cows."
#                 )
#                 return

#             # 👇 STORE, DO NOT SAVE YET
#             session.data["milk_values"] = [str(v) for v in values]
#             session.step = "confirm_milk"
#             session.save()

#             # Build confirmation message
#             summary_lines = []
#             for cow, qty in zip(cows, values):
#                 summary_lines.append(f"{cow.tag_number}: {qty} L")

#             summary = "\n".join(summary_lines)

#             self.send_message(
#                 phone,
#                 "🧾 Please confirm milk production:\n\n"
#                 f"{summary}\n\n"
#                 "Reply:\n"
#                 "1️⃣ Confirm & Save\n"
#                 "2️⃣ Re-enter quantities"
#             )
#             return

#             # -----------------------------------------------
#         # CONFIRM MILK
#         # -----------------------------------------------
#         if session.step == "confirm_milk":
#             if text == "2":
#                 # User wants to re-enter
#                 session.step = "enter_milk"
#                 session.data.pop("milk_values", None)
#                 session.save()

#                 cows = Cow.objects.filter(farm=session.farm).order_by("id")
#                 cow_list = "\n".join(
#                     [f"{i+1}. {cow.tag_number}" for i, cow in enumerate(cows)]
#                 )

#                 self.send_message(
#                     phone,
#                     "🔁 Okay, please re-enter milk amounts "
#                     "in the SAME order as below:\n\n"
#                     f"{cow_list}\n\n"
#                     "Example: 10,8.5,9"
#                 )
#                 return

#             if text != "1":
#                 self.send_message(
#                     phone,
#                     "Please reply:\n"
#                     "1️⃣ Confirm & Save\n"
#                     "2️⃣ Re-enter quantities"
#                 )
#                 return

#             # ✅ CONFIRM & SAVE
#             cows = list(Cow.objects.filter(farm=session.farm).order_by("id"))
#             values = [Decimal(v) for v in session.data.get("milk_values", [])]

#             today = date.today()
#             session_type = session.data["session"]

#             for cow, qty in zip(cows, values):
#                 MilkRecord.objects.update_or_create(
#                     cow=cow,
#                     date=today,
#                     session=session_type,
#                     defaults={
#                         "quantity_in_liters": qty,
#                         "recorded_by": user,
#                     }
#                 )

#             self.reset_session(session)

#             self.send_message(
#                 phone,
#                 "✅ Milk production saved successfully. Thank you!"
#             )
#             return

#         # -----------------------------------------------
#         # INCIDENT
#         # -----------------------------------------------
#         if session.step == "report_incident":
#             # You can wire this to an Incident model later
#             self.reset_session(session)
#             self.send_message(
#                 phone,
#                 "⚠️ Incident reported successfully."
#             )

#     # ==================================================
#     # 🔎 Helpers
#     # ==================================================
#     def get_user_by_phone(self, phone):
#         try:
#             return User.objects.get(phone=phone)
#         except User.DoesNotExist:
#             return None

#     def reset_session(self, session):
#         session.step = "menu"
#         session.data = {}
#         session.save()

#     def send_message(self, to, text):
#         url = f"https://graph.facebook.com/v18.0/{self.PHONE_NUMBER_ID}/messages"

#         headers = {
#             "Authorization": f"Bearer {self.ACCESS_TOKEN}",
#             "Content-Type": "application/json"
#         }

#         payload = {
#             "messaging_product": "whatsapp",
#             "to": to,
#             "text": {"body": text}
#         }

#         response = requests.post(url, headers=headers, json=payload)
#         print("SEND:", response.status_code, response.text)
class ProductionCallBack(APIView):
    authentication_classes = []
    permission_classes = []

    VERIFY_TOKEN = config("VERIFY_TOKEN")
    PHONE_NUMBER_ID = config("PHONE_NUMBER_ID")
    ACCESS_TOKEN = config("WHATS_APP_API_KEY")
    INACTIVITY_TIMEOUT = timedelta(minutes=10)

    # =========================
    # Webhook verification
    # =========================
    def get(self, request):
        if (
            request.GET.get("hub.mode") == "subscribe"
            and request.GET.get("hub.verify_token") == self.VERIFY_TOKEN
        ):
            return HttpResponse(request.GET.get("hub.challenge"))
        return HttpResponse("Forbidden", status=403)

    # =========================
    # Incoming messages
    # =========================
    def post(self, request):
        try:
            value = request.data["entry"][0]["changes"][0]["value"]
            message = value.get("messages", [{}])[0]

            if message.get("type") != "text":
                return HttpResponse("OK")

            phone = message["from"]
            text = message["text"]["body"].strip()

            self.route_message(phone, text)

        except Exception as e:
            print("Webhook error:", e)

        return HttpResponse("OK")

    # =========================
    # Message router
    # =========================
    # def route_message(self, phone, text):
    #     session, _ = ChatSession.objects.get_or_create(phone=phone)

    #     user = self.get_user_by_phone(phone)
    #     if not user:
    #         return self.send(phone, "❌ Your number is not linked to any account.")

    #     handlers = {
    #         "start": self.handle_start,
    #         "menu": self.handle_menu,
    #         "select_session": self.handle_select_session,
    #         "enter_milk": self.handle_enter_milk,
    #         "confirm_milk": self.handle_confirm_milk,
    #         "report_incident": self.handle_incident,
    #         "todays_report": self.handle_report,
    #     }

    #     handler = handlers.get(session.step, self.handle_start)
    #     handler(session, user, text)
    def route_message(self, phone, text):
        session, _ = ChatSession.objects.get_or_create(phone=phone)

        # ⏱️ RESET IF INACTIVE
        if timezone.now() - session.updated_at > self.INACTIVITY_TIMEOUT:
            session.step = "start"
            session.data = {}
            session.save()

        user = self.get_user_by_phone(phone)
        if not user:
            return self.send(phone, "❌ Your number is not linked to any account.")

        handlers = {
            "start": self.handle_start,
            "menu": self.handle_menu,
            "select_session": self.handle_select_session,
            "enter_milk": self.handle_enter_milk,
            "confirm_milk": self.handle_confirm_milk,
            "report_incident": self.handle_incident,
            "todays_report": self.handle_report,
        }

        handler = handlers.get(session.step, self.handle_start)
        handler(session, user, text)


    # =========================
    # Handlers
    # =========================
    def handle_start(self, session, user, text):
        farm = user.farms.first()
        if not farm:
            return self.send(user.phone, "❌ You are not assigned to any farm.")

        session.farm = farm
        session.step = "menu"
        session.save()

        menu = ["1️⃣ Enter milk production"]

        if user.role in {User.MANAGER, User.ACCOUNT_OWNER}:
            menu.append("2️⃣ Get today’s report")

        self.send(
            user.phone,
            f"👋 Hello {user.full_name}\n\nWhat would you like to do?\n\n" +
            "\n".join(menu)
        )

    def handle_menu(self, session, user, text):
        if text == "1":
            session.step = "select_session"
            session.save()
            return self.send(
                user.phone,
                "Select milk session:\n\n1️⃣ Morning\n2️⃣ Afternoon\n3️⃣ Evening"
            )

        if text == "2" and user.role in {User.MANAGER, User.ACCOUNT_OWNER}:
            self.send(user.phone, "📊 Generating today’s report, this may take a moment.")
            return self.handle_report(session, user, text)

        self.send(user.phone, "❌ Invalid option.")

    def handle_select_session(self, session, user, text):
        session_map = {
            "1": MilkRecord.MORNING,
            "2": MilkRecord.AFTERNOON,
            "3": MilkRecord.EVENING,
        }

        if text not in session_map:
            return self.send(user.phone, "Reply 1, 2 or 3.")

        session.data["session"] = session_map[text]
        session.step = "enter_milk"
        session.save()

        cows = Cow.objects.filter(farm=session.farm)
        cow_list = "\n".join(f"{i+1}. {c.tag_number}" for i, c in enumerate(cows))

        self.send(
            user.phone,
            f"Enter milk amounts separated by commas:\n\n{cow_list}\n\nExample: 10,8.5,9"
        )

    def handle_enter_milk(self, session, user, text):
        cows = list(Cow.objects.filter(farm=session.farm))

        try:
            values = [Decimal(v.strip()) for v in text.split(",")]
        except Exception:
            return self.send(user.phone, "❌ Invalid format.")

        if len(values) != len(cows):
            return self.send(
                user.phone,
                f"❌ Expected {len(cows)} values."
            )

        session.data["milk_values"] = [str(v) for v in values]
        session.step = "confirm_milk"
        session.save()

        summary = "\n".join(
            f"{cow.tag_number}: {qty} L"
            for cow, qty in zip(cows, values)
        )

        self.send(
            user.phone,
            f"🧾 Confirm milk production:\n\n{summary}\n\n1️⃣ Confirm\n2️⃣ Re-enter"
        )

    def handle_confirm_milk(self, session, user, text):
        if text == "2":
            session.step = "enter_milk"
            session.save()
            return self.send(user.phone, "🔁 Re-enter milk quantities.")

        if text != "1":
            return self.send(user.phone, "Reply 1 to confirm or 2 to re-enter.")

        cows = Cow.objects.filter(farm=session.farm)
        values = [Decimal(v) for v in session.data["milk_values"]]

        for cow, qty in zip(cows, values):
            MilkRecord.objects.update_or_create(
                cow=cow,
                date=date.today(),
                session=session.data["session"],
                defaults={"quantity_in_liters": qty, "recorded_by": user},
            )

        self.reset(session)
        self.send(user.phone, "✅ Milk production saved.")

    # def handle_report(self, session, user, text):
    #     today = date.today()
    #     total = (
    #         MilkRecord.objects
    #         .filter(cow__farm=session.farm, date=today)
    #         .aggregate(total=Sum("quantity_in_liters"))["total"]
    #         or 0
    #     )

    #     self.reset(session)
    #     self.send(user.phone, f"📊 Today’s total milk: {total} L")
    def handle_report(self, session, user, text):
    # 1️⃣ Generate PDF
        report = MilkProductionPDFReport(session.farm)
        pdf_path = report.generate()

        # 2️⃣ Upload to WhatsApp
        media_id = self.upload_pdf(pdf_path)

        # 3️⃣ Send short summary text first (good UX)
        today = date.today()
        total = (
            MilkRecord.objects
            .filter(cow__farm=session.farm, date=today)
            .aggregate(total=Sum("quantity_in_liters"))["total"]
            or 0
        )

        self.send(
            user.phone,
            f"📊 *Today’s Milk Summary*\n\nTotal milk: {total} L\n\n📄 Detailed report attached below."
        )

        # 4️⃣ Send PDF document
        self.send_pdf(user.phone, media_id)

        # 5️⃣ Reset conversation
        self.reset(session)


    def handle_incident(self, session, user, text):
        self.reset(session)
        self.send(user.phone, "⚠️ Incident reported.")

    # =========================
    # Helpers
    # =========================
    def reset(self, session):
        session.step = "start"
        session.data = {}
        session.save()


    def send(self, phone, text):
        requests.post(
            f"https://graph.facebook.com/v18.0/{self.PHONE_NUMBER_ID}/messages",
            headers={
                "Authorization": f"Bearer {self.ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "text": {"body": text},
            },
        )

    def get_user_by_phone(self, phone):
        return User.objects.filter(phone=phone).first()
    
    def upload_pdf(self, file_path):
        url = f"https://graph.facebook.com/v18.0/{self.PHONE_NUMBER_ID}/media"

        headers = {
            "Authorization": f"Bearer {self.ACCESS_TOKEN}",
        }

        files = {
            "file": (
                file_path.split("/")[-1],
                open(file_path, "rb"),
                "application/pdf"
            )
        }

        data = {"messaging_product": "whatsapp"}

        response = requests.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()

        return response.json()["id"]  # media_id   
    
    def send_pdf(self, phone, media_id):
        url = f"https://graph.facebook.com/v18.0/{self.PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {self.ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "id": media_id,
                "caption": "📊 Today’s Milk Production Report",
            },
        }

        response = requests.post(url, headers=headers, json=payload)
        print("SEND PDF:", response.status_code, response.text)
 



class MilkBulkRecordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Expect a LIST, not a dict
        if not isinstance(request.data, list):
            return Response(
                {"detail": "Expected a list of records"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_records = []
        errors = []

        for index, record_data in enumerate(request.data):
            serializer = MilkRecordSerializer(data=record_data)

            if serializer.is_valid():
                serializer.save(recorded_by=request.user)
                created_records.append(serializer.data)
            else:
                errors.append({
                    "index": index,
                    "errors": serializer.errors
                })

        return Response(
            {
                "created_records": created_records,
                "errors": errors
            },
            status=(
                status.HTTP_201_CREATED
                if not errors
                else status.HTTP_207_MULTI_STATUS
            )
        )
