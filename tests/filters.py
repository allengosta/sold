from django_filters.rest_framework import FilterSet

from tests.models import Project


class AdvertisementFilter(FilterSet):

    class Meta:
        model = Project
        fields = {
                  'name': ['in', 'exact'],
                  }