from datetime import date, timedelta
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from accounts.models import Cow,BreedingEvent,Pregnancy
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

class BreedingEventCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, farm_id):
        cow = get_object_or_404(
            Cow,
            id=request.data["cow_id"],
            farm_id=farm_id
        )

        if cow.is_pregnant:
            return Response(
                {"detail": "Cow is already pregnant"},
                status=400
            )

        breeding = BreedingEvent.objects.create(
            cow=cow,
            method=request.data["method"],
            date_bred=request.data["date_bred"]
        )

        return Response({"id": breeding.id}, status=201)
    
class ConfirmPregnancyAPIView(APIView):
    def post(self, request, breeding_id):
        breeding = get_object_or_404(BreedingEvent, id=breeding_id)

        Pregnancy.objects.create(
            cow=breeding.cow,
            breeding_event=breeding,
            confirmed=True,
            expected_calving_date=(
                breeding.date_bred + timedelta(days=283)
            ),
            status="ongoing"
        )

        return Response({"detail": "Pregnancy confirmed"})


class BreedingDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        user = request.user
        farm = get_object_or_404(Farm, id=farm_id)

        if not (user.is_system_user() or user.account_id == farm.account_id):
            return Response({"detail": "Not allowed"}, status=403)

        cows = Cow.objects.filter(farm=farm, is_active=True)

        today = date.today()
        calving_window = today + timedelta(days=30)

        # 🧠 Metrics
        pregnant_qs = Pregnancy.objects.filter(
            cow__in=cows,
            status="ongoing"
        )

        overview = {
            "ready_for_breeding": cows.filter(
                status=Cow.LACTATING
            ).exclude(
                pregnancies__status="ongoing"
            ).count(),

            "pregnant": pregnant_qs.count(),

            "expected_calvings": pregnant_qs.filter(
                expected_calving_date__lte=calving_window
            ).count(),

            "overdue_checks": pregnant_qs.filter(
                confirmed=False,
                breeding_event__date_bred__lte=today - timedelta(days=45)
            ).count(),
        }

        # 🐄 Upcoming calvings
        upcoming = pregnant_qs.filter(
            expected_calving_date__gte=today
        ).order_by("expected_calving_date")[:5]

        upcoming_calvings = [
            {
                "tag": p.cow.tag_number,
                "days_left": (p.expected_calving_date - today).days
            }
            for p in upcoming
        ]

        # ❤️ Recent breeding events
        breedings = BreedingEvent.objects.filter(
            cow__in=cows
        ).order_by("-date_bred")[:5]

        recent_breedings = [
            {
                "id": b.id,
                "tag": b.cow.tag_number,
                "date": b.date_bred,
                "method": b.method,
                "status": "confirmed" if hasattr(b, "pregnancy") else "pending"
            }
            for b in breedings
        ]

        return Response({
            "overview": overview,
            "recent_breedings": recent_breedings,
            "upcoming_calvings": upcoming_calvings,
        })
