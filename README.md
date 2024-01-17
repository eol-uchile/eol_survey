# EOL CONTACT FORM

![https://github.com/eol-uchile/eol_contact_form/actions](https://github.com/eol-uchile/eol_contact_form/workflows/Python%20application/badge.svg)

New Page for Open Edx LMS (EOL) with a contact form

# Install

    docker-compose exec lms pip install -e /openedx/requirements/eol_survey
# Configuration

To enable [Google ReCAPTCHA v2](https://www.google.com/recaptcha/) Edit *production.py* in *lms settings* and add your own keys. Add help desk default email.

    EOL_CONTACT_FORM_RECAPTCHA_SITE_KEY = AUTH_TOKENS.get('EOL_CONTACT_FORM_RECAPTCHA_SITE_KEY', '')
    EOL_CONTACT_FORM_RECAPTCHA_SECRET_KEY = AUTH_TOKENS.get('EOL_CONTACT_FORM_RECAPTCHA_SECRET_KEY', '')
    EOL_CONTACT_FORM_HELP_DESK_EMAIL = AUTH_TOKENS.get('EOL_CONTACT_FORM_HELP_DESK_EMAIL', '')

Set help desk email in a Site:
- */admin/site_configuration/siteconfiguration/*
    - **"EOL_CONTACT_FORM_HELP_DESK_EMAIL":""**

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run lms /openedx/requirements/eol_contact_form/.github/test.sh

# Screenshots
*Last Update 15/04/2020*

<p align="center">
<img width="600" src="examples/lms_form.png">
</p>