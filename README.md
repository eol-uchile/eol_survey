# EOL SURVEY

![Coverage Status](/coverage-badge.svg)

![https://github.com/eol-uchile/eol_survey/actions](https://github.com/eol-uchile/eol_survey/workflows/Python%20application/badge.svg)

On this Manager of your surveys can create, delete or edit a different surveys, also use this survey in a course like an xblock and finally, generate a report in the instructor view with all the answers of your students.

# Install

    docker-compose exec lms pip install -e /openedx/requirements/eol_survey
    docker-compose exec cms pip install -e /openedx/requirements/eol_survey
    docker-compose exec lms python manage.py lms --settings=prod.production makemigrations eol_survey
    docker-compose exec lms python manage.py lms --settings=prod.production migrate eol_survey



# Install Theme

To enable the export eol survey report interface, add the following code to your theme. This includes a conditional check to ensure the template only renders if the app is installed.

- _../themes/your_theme/lms/templates/instructor/instructor_dashboard_2/data_download.html_

    **add eol_survey template to the data_download template**

        <%
        survey_url = None
        survey_traceback = None
        try:
          survey_url = reverse('eolSurveyReport')
        except Exception:
          if settings.DEBUG:
            survey_traceback = traceback.format_exc()
        %>  
        %if survey_traceback:
          <div class="survey_traceback" hidden>
            <pre>${survey_traceback}</pre>
          </div>
        %elif survey_url:
          <%include file="eol_survey.html"/>
        %endif


### Adding new translations:

To extract and update any new translatable text, run the update command below. After manually filling in the new translations, run the compile command to update the .mo translation files.

### Commands

**Update**

    docker run -it --rm -w /code -v $(pwd):/code python:3.8 bash
    pip install -r requirements-i18n.in
    make update_translations

**Compile**

    docker run -it --rm -w /code -v $(pwd):/code python:3.8 bash
    pip install -r requirements-i18n.in
    make compile_translations

# URL
mydomain.com/Survey_form

## TESTS
**Prepare tests:**

- Install **act** following the instructions in [https://nektosact.com/installation/index.html](https://nektosact.com/installation/index.html)

**Run tests:**
- In a terminal at the root of the project
    ```
    act -W .github/workflows/pythonapp.yml
    ```
