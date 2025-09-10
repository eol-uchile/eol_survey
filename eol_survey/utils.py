# Python Standard Libraries
from collections import OrderedDict, defaultdict
import json
import logging

# Installed packages (via pip)
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext as _
from uchileedxlogin.services.interface import get_user_id_doc_id_pairs
import six

# Edx dependencies
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from lms.djangoapps.courseware.models import StudentModule
from opaque_keys.edx.keys import CourseKey, UsageKey
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError

log = logging.getLogger(__name__)

def get_all_states(block_id, course_key):
    """
        Get all student module
    """
    usage_key = UsageKey.from_string(block_id)
    smdat = StudentModule.objects.filter(course_id=course_key, module_state_key=usage_key).order_by('student__username').values('student__username', 'state')
    response = []
    for module in smdat:
        response.append({'username': module['student__username'], 'state': json.loads(module['state'])})
    return response

def _build_student_data(data, students, block, student_states, csvwriter):
    """
        Create list of list to make csv report
    """
    url_base = data['base_url']
    block_key = UsageKey.from_string(block)
    course_key = block_key.course_key
    header = ['Username', 'Email', 'Documento_id']
    store = modulestore()
    with store.bulk_operations(course_key):
        block_item = store.get_item(block_key)
        generated_report_data = get_report_xblock(block_key, student_states, block_item)
        if generated_report_data is not None:
            aux_headers = get_headers(student_states)
            if aux_headers is not None:
                for i in range(len(aux_headers)):
                    header.append('Pregunta {}'.format(i + 1))
                csvwriter.writerow(_get_utf8_encoded_rows(header))
                for response in student_states:
                    if response['username'] not in students:
                        continue
                    # A human-readable location for the current block
                    # A machine-friendly location for the current block
                    # A block that has a single state per user can contain multiple responses
                    # within the same state.
                    user_states = generated_report_data.get(response['username'])
                    if user_states:
                        responses = set_data(
                                response,
                                students,
                                user_states,
                                aux_headers
                                )
                        if responses:
                            csvwriter.writerow(_get_utf8_encoded_rows(responses))



        #Analytics Here!
        csvwriter.writerow([])
        csvwriter.writerow([])
        csvwriter.writerow(['¡Preguntas!'])

        questions = get_questions(generated_report_data)
        if aux_headers is not None:

            for x in range(len(aux_headers)):
                row = [
                'Pregunta {}'.format(x + 1), 
                questions[aux_headers[x]]['question']
                ]
                csvwriter.writerow(_get_utf8_encoded_rows(row))
    return csvwriter

def get_headers(student_states):
    for response in student_states:
        raw_state = response['state']
        if 'attempts' not in raw_state:
            continue
        return list(raw_state['input_state'].keys())
    return None
def get_questions(generated_report_data):
    questions = {}
    for username in generated_report_data:
        if questions:
            break
        for user_state in generated_report_data[username]:
            if _("Correct Answer") in user_state:
                questions[user_state[_("Answer ID")]] = {'question':user_state[_("Question")].replace(";",""), 'correct':user_state[_("Correct Answer")].replace(";","")}
            else:
                questions[user_state[_("Answer ID")]] = {'question':user_state[_("Question")].replace(";",""), 'correct':''}
    return questions

def set_data(response, students, user_states, questions_ids):
    """ 
        Create a row according 
        ['Username', 'Email', 'Documento_id', 'Intentos', 'preg1', 'preg2, ... 'pregN' , 'Nota']
    """

    # For each response in the block, copy over the basic data like the
    # title, location, block_key and state, and add in the responses
    responses = [
            response['username'], 
            students[response['username']]['email'], 
            students[response['username']]['doc_id'],
            ]
    aux_response = {}
    for user_state in user_states:
        aux_response[user_state[_("Answer ID")]] = user_state[_("Answer")].replace(";","")
    for x in questions_ids:
        responses.append(aux_response[x])
    return responses

def get_all_enrolled_users(course_key):
    """
        Get all enrolled student 
    """
    students = OrderedDict()
    enrolled_students = User.objects.filter(
        courseenrollment__course_id=course_key,
        courseenrollment__is_active=1,
    ).order_by('username').values('id', 'username', 'email')
    user_id_list = enrolled_students.values_list('id', flat=True)
    user_doc_id = get_user_id_doc_id_pairs(user_id_list)
    user_doc_id_dict = {id: doc_id for id, doc_id in user_doc_id}
    for user in enrolled_students:
        doc_id = user_doc_id_dict.get(user['id'], '')
        students[user['username']] = {'email': user['email'], 'doc_id': doc_id}
    return students

def get_report_xblock(block_key, user_states, block):
    """
    # Blocks can implement the generate_report_data method to provide their own
    # human-readable formatting for user state.
    """
    generated_report_data = defaultdict(list)
    for username, state in block.generate_report_data(user_states, block):
        generated_report_data[username].append(state)
    return generated_report_data

def _get_utf8_encoded_rows(row):
    """
    Given a list of `rows` containing unicode strings, return a
    new list of rows with those strings encoded as utf-8 for CSV
    compatibility.
    """

    if six.PY2:
        return [six.text_type(item).encode('utf-8') for item in row]
    else:
        return [six.text_type(item) for item in row]

def get_eol_survey_responses(request, course_id):
    if request.method != "GET":
        return HttpResponse(status=400)
    course_key = CourseKey.from_string(course_id)
    if (CourseInstructorRole(course_key).has_user(request.user) or
                  CourseStaffRole(course_key).has_user(request.user)):
        store = modulestore()
        with store.bulk_operations(course_key):
            smdat = StudentModule.objects.filter(course_id= course_key, module_type= 'eol_survey').values('module_state_key').distinct().order_by()
            response = []
            max_length = 20
            for data in smdat:
                try:
                    block_item = store.get_item(data['module_state_key'])
                    block_unit = store.get_item(block_item.parent)
                    block_subsection = store.get_item(block_unit.parent)
                    block_section = store.get_item(block_subsection.parent)
                    response.append({'name_survey': block_item.display_name, 'location': str(block_item.location), 'parent_display_name': '{} > {} > {}'.format(_formatter_text(block_section.display_name,max_length), _formatter_text(block_subsection.display_name,max_length), _formatter_text(block_unit.display_name,max_length))})
                except ItemNotFoundError:
                    log.error("Error no hay registro de esta encuesta")

        return JsonResponse({'response':response}, safe=False)    
    
    else:
        log.error("User dont have permission or is not staff, user: {}".format(request.user))
        return HttpResponse(status=400)

def _formatter_text(text, max_length):
    if len(text)> max_length: 
        return f"{text[:max_length-3]}..."
    else: 
        return text
