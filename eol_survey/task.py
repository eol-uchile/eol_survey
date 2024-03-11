import six
import csv
import codecs
from pytz import UTC
from time import time
from datetime import datetime
from functools import partial
from celery import current_task, task
from django.core.files.base import ContentFile
from django.utils.translation import ugettext_noop
from lms.djangoapps.instructor_task.models import ReportStore
from lms.djangoapps.instructor_task.tasks_base import BaseInstructorTask    
from opaque_keys.edx.keys import CourseKey, UsageKey, LearningContextKey
from common.djangoapps.util.file import course_filename_prefix_generator
from .utils import get_all_states,_build_student_data, get_all_enrolled_users
from lms.djangoapps.instructor_task.api_helper import submit_task, AlreadyRunningError
from lms.djangoapps.instructor_task.tasks_helper.runner import run_main_task, TaskProgress
import logging
log = logging.getLogger(__name__)

def task_process_data(request, data):
    block_key = UsageKey.from_string(request.GET.get("block"))
    course_key = block_key.course_key
    task_type = 'Eol_Survey_Report_Analytics'
    task_class = process_data
    task_input = {'data': data }
    task_key = "{}_{}".format(task_type, str(course_key))

    return submit_task(
        request,
        task_type,
        task_class,
        course_key,
        task_input,
        task_key)

@task(base=BaseInstructorTask, queue='edx.lms.core.low')
def process_data(entry_id, xmodule_instance_args):
    action_name = ugettext_noop('generated')
    task_fn = partial(generate, xmodule_instance_args)

    return run_main_task(entry_id, task_fn, action_name)

def generate(_xmodule_instance_args, _entry_id, course_id, task_input, action_name):
    """
    For a given `course_id`, generate a CSV file containing
    all student answers to a given problem, and store using a `ReportStore`.
    """
    start_time = time()
    start_date = datetime.now(UTC)
    num_reports = 1
    task_progress = TaskProgress(action_name, num_reports, start_time)
    current_step = {'step': 'EolSurveyReportAnalytics - Calculating students answers to problem'}
    task_progress.update_task_state(extra_meta=current_step)
    
    data = task_input.get('data')
    students = get_all_enrolled_users(course_id)

    report_store = ReportStore.from_config('GRADES_DOWNLOAD')
    csv_name = 'Analitica_de_Encuestas'

    report_name = u"{course_prefix}_{csv_name}_{timestamp_str}.csv".format(
        course_prefix=course_filename_prefix_generator(course_id),
        csv_name=csv_name,
        timestamp_str=start_date.strftime("%Y-%m-%d-%H%M")
    )
    output_buffer = ContentFile('')
    if six.PY2:
        output_buffer.write(codecs.BOM_UTF8)
    csvwriter = csv.writer(
            output_buffer,
            delimiter=';',
            dialect='excel')
    student_states = get_all_states(data['block'],course_id)
    csvwriter = _build_student_data(data, students, data['block'], student_states, csvwriter)

    current_step = {'step': 'EolSurveyReportAnalytics - Uploading CSV'}
    task_progress.update_task_state(extra_meta=current_step)

    output_buffer.seek(0)
    report_store.store(course_id, report_name, output_buffer)
    current_step = {
        'step': 'EolSurveyReportAnalytics - CSV uploaded',
        'report_name': report_name,
    }

    return task_progress.update_task_state(extra_meta=current_step)

