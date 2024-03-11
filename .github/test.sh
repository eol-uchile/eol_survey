#!/bin/dash
set -e
pip install -e /openedx/requirements/eol_survey

cd /openedx/requirements/eol_survey/eol_survey
cp /openedx/edx-platform/setup.cfg .
mkdir test_root
cd test_root/
ln -s /openedx/staticfiles .

cd /openedx/requirements/eol_survey/eol_survey

DJANGO_SETTINGS_MODULE=lms.envs.test EDXAPP_TEST_MONGO_HOST=mongodb pytest tests.py


rm -rf test_root