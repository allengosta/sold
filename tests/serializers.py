from rest_framework import serializers

from tests.models import Project


class AdvertisementSerializer(serializers.ModelSerializer):
    primary_income_calls = serializers.IntegerField()
    call_center_working_specs = serializers.IntegerField()
    call_center_primary_visits = serializers.IntegerField()
    managers_outcome_calls = serializers.IntegerField()
    check_date = serializers.SerializerMethodField()

    def get_check_date(self, obj):
        return self.context['request'].query_params.get('check_date', None)

    class Meta:
        model = Project
        fields = (
            'id',
            'name',
            'primary_income_calls',
            'call_center_working_specs',
            'call_center_primary_visits',
            'managers_outcome_calls',
            'check_date'
        )