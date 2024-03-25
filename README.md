# EOL SURVEY

![https://github.com/eol-uchile/eol_survey/actions](https://github.com/eol-uchile/eol_survey/workflows/Python%20application/badge.svg)

On this Manager of your surveys can create, delete or edit a different surveys, also use this survey in a course like an xblock and finally, generate a report in the instructor view with all the answers of your students.

# Install

    docker-compose exec lms pip install -e /openedx/requirements/eol_survey
    docker-compose exec cms pip install -e /openedx/requirements/eol_survey
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations eol_survey
    docker-compose exec lms python manage.py lms --settings=prod.production migrate eol_survey



# Install Theme

To enable export Eol Survey combobox in your theme add next file and/or lines of code:

- _../themes/your_theme/lms/templates/instructor/instructor_dashboard_2/data_download.html_
    
    **add the script and css**
        
        <script type="text/javascript" src="${static.url('eol_survey/js/eol_survey_report_analytics.js')}"></script>
        <link rel="stylesheet" type="text/css" href="${static.url('eol_survey/css/eol_survey_report_analytics.css')}"/>
        <script type="text/javascript" src="${static.url('eol_survey/js/loadcbanalytics.js')}"></script>

    
    **and add html button**
    
        <% 
        try: 
          import urllib
          import eol_survey
          from django.urls import reverse
          enable_survey = True
          survey_url = '{}?{}'.format(reverse('eolSurveyReport'), urllib.parse.urlencode({'course': str(course.id)}))
        except mportError:
          enable_survey = False 
        %>
        %if enable_survey :
        
        <div class='eol_survey_report_analytics-report'>    
            <hr>
            <h4 class="hd hd-4">${_("Analítica de encuestas")}</h4>
            <p>
                <select name="cb_eol_survey" id="cb_eol_survey" >
                </select>     
                <input onclick="generate_analytics_report_survey(this)" type="button" name="eol_survey_report_analytics-report" value="${_("Generar")}" data-endpoint="${ survey_url }"/>
            </p>
            <div class="eol_survey_report_analytics-success-msg" id="eol_survey_report_analytics-success-msg"></div>
            <div class="eol_survey_report_analytics-warning-msg" id="eol_survey_report_analytics-warning-msg"></div>
            <div class="eol_survey_report_analytics-error-msg" id="eol_survey_report_analytics-error-msg"></div>
            <input type="hidden" name="courseId" id="courseId" value="${course.id}"> 
        </div>
        %endif

# URL
mydomain.com/Survey_form

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/eol_survey/.github/test.sh
