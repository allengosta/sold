import json
from collections import namedtuple
from datetime import datetime, time

from django.db import connection
from django.db.models import Q, OuterRef, F, Value, Exists, When, Sum, Count, Case, Func
from django.forms import IntegerField
from django.http import HttpResponse
from rest_framework import mixins
from rest_framework import permissions
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import detail_route
from rest_framework.decorators import list_route
from rest_framework.exceptions import ValidationError

from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.response import Response

from tests.serializers import AdvertisementSerializer
from .filters import AdvertisementFilter
from .models import Project, Contact
import datetime as date


class Interval(Func):
    function = 'CAST'
    template = '%(function)s(%(expressions)s AS INTERVAL)'


def namedtuplefetchall(cursor):
    """Return all rows from a cursor as a namedtuple"""
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


class AdvertisementViewSet(mixins.ListModelMixin, viewsets.GenericViewSet, viewsets.ViewSet):
    queryset = Project.objects.all()
    renderer_classes = [JSONRenderer, BrowsableAPIRenderer]
    pagination_class = None
    serializer_class = AdvertisementSerializer
    filter_class = AdvertisementFilter
    search_fields = ('name',)

    def get_queryset(self):
        if self.kwargs['id'] != '0':
            project_id = self.kwargs['id']
            qs = self.queryset.filter(id=project_id)
            return qs
        else:
            return self.queryset.filter(id__in=(35, 37, 40, 41, 27, 28, 30, 42, 43, 44))

    def list(self, request, *args, **kwargs):
        call_center_primary_visits_whens = []
        managers_outcome_calls_whens = []
        call_center_working_specs_whens = []

        if self.kwargs['id'] != '0':
            project_id = self.kwargs['id']
            project = Project.objects.get(id=project_id)
            check_date_str = request.query_params.get('check_date', None)

            check_date = datetime.strptime(check_date_str, "%Y-%m-%dT%H:%M:%S.%f")

            primary_income_calls_query = Q(contacts__time__date=check_date.date()) & Q(contacts__source__in=[2, 3],
                                                                                       contacts__extra_type=0) & Q(
                contacts__typex=1)

            managers_outcome_calls = Contact.objects.filter(Q(project=project_id) if project_id else Q(),
                                                            extra_type__in=(0, 1),
                                                            source=2,
                                                            typex=0,
                                                            time__date=check_date.date()). \
                exclude(user__user_permissions__name='operator').exclude(result__in=(9,))

            call = Contact.objects.filter(client=OuterRef('client'),
                                          extra_type__in=(0, 1), user__user_permissions__name='operator')

            call_center_primary_visits_query = Contact.objects.filter(
                Q(project=project_id) if project_id else Q(),
                source=1,
                time__date=check_date.date(),
                client__contacts__extra_type__in=(0, 1),
                # user__user_permissions__name='operator',
                client__contacts__time__lte=F('time'),
                client__contacts__time__gte=F('time') - Interval(Value('1 month'))
            ).annotate(calls_q=Exists(call)).filter(calls_q=True).distinct('client').filter(
                extra_type__in=[0, 2, 3])

            call_center_primary_visits_count = call_center_primary_visits_query.count()
            call_center_primary_visits_whens.append(When(id=project.id, then=call_center_primary_visits_count))

            managers_outcome_calls_count = managers_outcome_calls.count()
            managers_outcome_calls_whens.append(When(id=project.id, then=managers_outcome_calls_count))

            self.queryset = self.queryset.annotate(

                primary_income_calls=Count(Case(When(primary_income_calls_query, then=F('contacts__client'))),
                                           distinct=True),

                call_center_working_specs=Case(*call_center_working_specs_whens, default=0,
                                               output_field=IntegerField()),

                call_center_primary_visits=Case(*call_center_primary_visits_whens, default=0,
                                                output_field=IntegerField()),

                managers_outcome_calls=Case(*managers_outcome_calls_whens, default=0, output_field=IntegerField()),
            )
            return super().list(request, *args, **kwargs)

    @list_route()
    def chart_1(self, request, *args, **kwargs):

        start_date = datetime(2017, 6, 1)

        time_0 = request.query_params.get('time_0')
        time_1 = request.query_params.get('time_1')
        breakdown = request.query_params.get('breakdown')
        project_filter = request.query_params.get('project__in', None)

        user_id = request.query_params.get('user__id', None)

        if user_id == 'all' or user_id == None:
            user_id = 'NULL'

        time_0 = datetime.combine(datetime.strptime(time_0, '%Y-%m-%d'), time.min)
        time_1 = datetime.combine(datetime.strptime(time_1, '%Y-%m-%d'), time.max)

        raw_sql = """
            select charts.date, Sum(charts.calls_count) from (
                SELECT
                to_char(dates.d1::DATE, 'YYYY-MM-DD') AS date,
                "dj_projects"."id",
                "dj_projects"."name",
                COUNT(DISTINCT
                CASE WHEN (
                         "dj_contacts"."time" BETWEEN dates.d1 AND dates.d1 + INTERVAL '1 day')
                THEN "dj_contacts"."id"
                ELSE NULL END) AS calls_count
                from (SELECT * FROM generate_series('{}'::DATE, '{}'::DATE, INTERVAL '1 day') d1) as dates, dj_projects
                LEFT OUTER JOIN "dj_contacts" ON ("dj_projects"."id" = "dj_contacts"."project_id" 
                and "dj_contacts"."extra_type" = 0 
                AND "dj_contacts"."source" IN (2, 3) AND "dj_contacts"."typex" = 1)
                WHERE "dj_projects"."id" IN ({}) and "dj_contacts".user_id = COALESCE(({}), "dj_contacts".user_id)
                group by dj_projects.id, dates.d1
                order by dj_projects.id, dates.d1) as charts 
                group by charts.date order by charts.date
            """

        project_q = Q()
        if project_filter is not None and project_filter != '':
            project_filter = project_filter.split(',')
            project_q = Q(id__in=project_filter)

        projects = request.user.profile.projects.filter(project_q).values_list('id', flat=True)
        user_projects = ",".join([str(id) for id in projects])

        raw_sql = raw_sql.format(time_0, time_1, user_projects, user_id)

        with connection.cursor() as cursor:
            cursor.execute(raw_sql)
            results = namedtuplefetchall(cursor)
            calls = []
            trend_values = []

            total = 0
            index = 0

            for row in results:
                cur_date = datetime.strptime(row[0], '%Y-%m-%d').date()
                if cur_date <= date.date.today():
                    total += int(row[1])
                    calls.append(int(row[1]))
                index += 1

            try:
                average_day_call_count = total / len(calls)
                trend_value_of_the_day = round(average_day_call_count, 2)
            except Exception:
                trend_value_of_the_day = 0

            for day_numb in range(1, time_1.day + 1):
                trend_values.append(trend_value_of_the_day)

            resp = {'Calls': calls, 'Trend': trend_values}
            return HttpResponse(json.dumps(resp), content_type="application/json")
