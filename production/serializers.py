from rest_framework import serializers
from .models import MilkRecord

class MilkRecordSerializer(serializers.ModelSerializer):
    cow_display = serializers.SerializerMethodField()

    class Meta:
        model = MilkRecord
        fields = [
            "id",
            "cow",
            "cow_display",
            "date",
            "session",
            "quantity_in_liters",
            "notes",
            "created_at",
        ]

    def get_cow_display(self, obj):
        # Prefer name, fallback to tag number
        if obj.cow.name:
            return obj.cow.name
        return obj.cow.tag_number

    def validate_quantity_in_liters(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Milk quantity must be greater than zero."
            )
        return value
