import datetime

from osf_tests.factories import PreprintFactory, PreprintProviderFactory
from osf.models import PreprintService
import mock
import pytest
import pytz
import requests
from django.utils import timezone

from scripts.analytics.preprint_summary import PreprintSummary


@pytest.fixture()
def preprint_provider():
    return PreprintProviderFactory(name='Test 1')

@pytest.fixture()
def preprint(preprint_provider):
    return PreprintFactory._build(PreprintService, provider=preprint_provider)


@pytest.fixture()
def right_before_my_birthday():
    return {'preprint_dates': datetime.datetime(1991, 9, 25, 0, tzinfo=pytz.utc).replace(hour=23,minute=59,second=59),
            'run_date': timezone.now()
            }

@pytest.fixture()
def my_birthday_at_midnight():
    return {'preprint_dates': datetime.datetime(1991, 9, 25, 0, tzinfo=pytz.utc),
            'run_date': timezone.now()
            }

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('date', [right_before_my_birthday(), my_birthday_at_midnight()])
class TestPreprintCount:

    def test_get_preprint_count(self, preprint, date):

        requests.post = mock.MagicMock()
        resp = requests.Response()
        resp._content = '{"hits" : {"total" : 1}}'
        requests.post.return_value = resp

        field = PreprintService._meta.get_field('date_created')
        field.auto_now_add = False  # We have to fudge the time because Keen doesn't allow same day queries.

        preprint.date_created = date['preprint_dates'] - datetime.timedelta(hours=1)
        preprint.save()

        field.auto_now_add = True
        results = PreprintSummary().get_events(date['preprint_dates'].date())

        assert len(results) == 1

        data = results[0]
        assert data['provider']['name'] == 'Test 1'
        assert data['provider']['total'] == 1

