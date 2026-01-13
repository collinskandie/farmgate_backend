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

# from rest_framework.views import APIView
import json

from production.models import MilkRecord
from production.serializers import MilkRecordSerializer

# Create your views here.


class MilkRecordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # -----------------------------------------
    # GET → List all milk records
    # -----------------------------------------
    def get(self, request):
        records = MilkRecord.objects.select_related("cow").all()
        serializer = MilkRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # -----------------------------------------
    # POST → Create a milk record
    # -----------------------------------------
    def post(self, request):
        serializer = MilkRecordSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(recorded_by=request.user)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    # -----------------------------------------
    # PUT → Update a milk record
    # -----------------------------------------
    def put(self, request, pk):
        record = get_object_or_404(MilkRecord, pk=pk)

        serializer = MilkRecordSerializer(
            record,
            data=request.data,
            partial=True  # allows partial updates
        )

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class ProductionCallBack(APIView):
    authentication_classes = []
    permission_classes = []

    PHONE_NUMBER_ID = "933662143166769"
    ACCESS_TOKEN = "EAATZCpNkJN88BQduOXhLGFt0h1LmO6jB4sHEBlbE3EJ2B4KTXwf1kKqsUR3ZAc2ZBuZAeDAxWPlcNKJwPz1PGa4imklOQbazjGDZBvvRYXhn3Bl4UBAFy1kRj45aqw3SMJfXArqsHuHX6EzrbGSuUz3mClQi0kEfgIjvcbLFNWaRcmO6017kAxzkCTHXLd9eDfi4OiEjE0fM71phZAJS4qnk7jbIz9Egfx9jCHnMZCN"

    def get(self, request):
        VERIFY_TOKEN = "framgatego_verify_token"

        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge)

        return HttpResponse("Forbidden", status=403)

    def post(self, request):
        payload = request.data
        print("🔥🔥🔥 POST WEBHOOK HIT 🔥🔥🔥")
        print(request.data)

        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]
            value = change["value"]

            if "messages" not in value:
                return HttpResponse("No message", status=200)

            message = value["messages"][0]

            # 🔒 Safety check (important)
            if message.get("type") != "text":
                return HttpResponse("Ignored", status=200)

            from_number = message["from"]
            text = message["text"]["body"]

            print("Incoming:", from_number, text)

            self.send_whatsapp_message(
                to=from_number,
                text="Hello 👋 Welcome to Farmgate!"
            )

        except Exception as e:
            print("Webhook error:", e)

        return HttpResponse("OK", status=200)

    def send_whatsapp_message(self, to, text):
        url = f"https://graph.facebook.com/v18.0/{self.PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {self.ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "text": {"body": text}
        }

        response = requests.post(url, headers=headers, json=payload)
        print("SEND STATUS:", response.status_code)
        print("SEND BODY:", response.text)
