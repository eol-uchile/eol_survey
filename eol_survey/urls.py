

from django.conf.urls import url
from django.conf import settings
from . import api,utils 
from .views import EolSurveyView, EolSurveyReportAnalyticsView

urlpatterns = (
    url(
        r'Survey_form$',
        EolSurveyView.as_view(),
        name='Survey_form_view',
    ),
    url(
        r'api/message_detail$',
        api.message_detail,
        name='message_detail_api',
    ),
    url(
        r'api/delete_survey/$',
        api.delete_survey,
        name='delete_survey'
    ), 
    url(
        r'api/get_survey_json/$', 
        api.get_survey_json, 
        name='get_survey_json'
    ),
    url(
        r'Report_Survey$',
        EolSurveyReportAnalyticsView.as_view(),
        name='eolSurveyReport'
    ),
    url(
        r'survey_responses/{}$'.format(
            settings.COURSE_ID_PATTERN,   
        ),
        utils.get_eol_survey_responses,
        name='survey_responses'
    )
)
