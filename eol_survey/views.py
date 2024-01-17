# -*- coding: utf-8 -*-
import json
import requests
from .models import Survey
from itertools import cycle
from django.http import Http404
from django.urls import reverse
from django.conf import settings
from .task import task_process_data
from django.shortcuts import render
from opaque_keys import InvalidKeyError
from django.utils.html import strip_tags
from django.views.generic.base import View
from django.db import IntegrityError, transaction
from lms.djangoapps.instructor import permissions
from xmodule.modulestore.django import modulestore
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from lms.djangoapps.courseware.access import has_access
from xmodule.modulestore.exceptions import ItemNotFoundError
from opaque_keys.edx.keys import CourseKey, UsageKey, LearningContextKey
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from lms.djangoapps.instructor_task.api_helper import submit_task, AlreadyRunningError
from lms.djangoapps.courseware.courses import get_course_by_id, get_course_with_access
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

import logging
logger = logging.getLogger(__name__)

def _default_data():
    return {
        'form-rut': '',
        'form-name': '',
        'form-email': '',
        'form-type': '',
        'form-course': '',
        'form-description': '',
    }


class EolSurveyView(View):
    http_method_names = ['post','get','delete']
    def get(self, request):
        if not request.user.is_anonymous and request.user.is_staff: 
        
            context = {
                'data':{"form-header": "","form-description":"", "form-content": ""},
                'status': ""
            }
            return render(request, 'eol_survey/survey_form.html', context)
        else:
            logger.error("User dont have permission or is not staff, user: {}".format(request.user))
            return HttpResponse(status=400)

    def post(self, request):
        # Check method params
        if  'form-header' not in request.POST or 'form-description' not in request.POST or 'form-content' not in request.POST:
            return HttpResponse(status=400)

        inputSurvey = request.POST.get('inputId', '')

        context = {
            'data':{"form-header": "","form-description":"", "form-content": ""},
            'status': ""
        }

        if not request.user.is_anonymous and request.user.is_staff: 
            # Validate user form data
            validation = self.validate_data(request.POST)
            # If data is invalid, send error flag and form data
            if validation['error']:
                context['success'] = False
                context['error'] = validation['error_attr']
                context['data'] = request.POST  # Update data with form values
                return render(request, 'eol_survey/survey_form.html', context)

            header_value = request.POST['form-header']
            description_value = request.POST['form-description']
            content_value = request.POST['form-content']
            # checks if the inputSurvey exists, if it does, it edits it, otherwise it creates it automatically.
            if inputSurvey:
                try:
                    message = Survey.objects.get(id=inputSurvey)
                    message.header= header_value
                    message.description = description_value
                    message.content = content_value
                    message.save()
                    context['success'] = True
                    context['status'] = "Update"  
                    return render(request, 'eol_survey/survey_form.html', context)
                except Survey.DoesNotExist: 
                    context['success'] = False
                    context['status'] = "Error"
                    context['error'] = validation.get('error_attr', 'Error desconocido')
                    context['data'] = request.POST  
                    return render(request, 'eol_survey/survey_form.html', context)
            else:
                message = Survey(
                    header= header_value,
                    description= description_value,
                    content= content_value
                    )
                message.save()
                context['success'] = True
                context['status'] = "Create"
                return render(request, 'eol_survey/survey_form.html', context)
        
        else: 
            logger.error("User dont have permission or is not staff, user: {}".format(request.user))
            return HttpResponse(status=400)

    def validate_data(self, data):
        """
            Validate all form data
        """
        if data['form-header'].strip() == '':
            return {
                'error': True,
                'error_attr': 'Encabezado'
            }
        if data['form-description'].strip() == '':
            return {
                'error': True,
                'error_attr': 'Descripcion'
            }
        if data['form-content'].strip()== '':
            return {
                'error': True,
                'error_attr': 'Contenido'
            }
        return {
            'error': False
        }

class EolSurveyReportAnalyticsView(View):
    """
        Return a csv with progress students
    """
    @transaction.non_atomic_requests
    def dispatch(self, args, **kwargs):
        return super(EolSurveyReportAnalyticsView, self).dispatch(args, **kwargs)

    def get(self, request, **kwargs):
        if not request.user.is_anonymous:
            data = self.validate_and_get_data(request)
            if data['block'] is None:
                logger.error("EolSurveyReportAnalytics - Falta parametro block o parametro incorrecto, user: {}, course: {}, block: {}".format(request.user, request.GET.get('course', ''), request.GET.get('block', '')))
                return JsonResponse({'error': 'Falta parametro block o parametro incorrecto'})
            elif not self.have_permission(request.user, data['block']):
                logger.error("EolSurveyReportAnalytics - Usuario no tiene rol para esta funcionalidad, user: {}, course: {}, block: {}".format(request.user, request.GET.get('course', ''), request.GET.get('block', '')))
                return JsonResponse({'error': 'Usuario no tiene rol para esta funcionalidad'})
            data['base_url'] = request.build_absolute_uri('')
            return self.get_context(request, data)
        else:
            logger.error("EolReportAnalytics - User is Anonymous")
        raise Http404()

    def get_context(self, request, data):
        try:
            task = task_process_data(request, data)
            success_status = 'La analitica de las encuestas esta siendo creada, en un momento estará disponible para descargar.'
            return JsonResponse({"status": success_status, "task_id": task.task_id})
        except AlreadyRunningError:
            logger.error("EolSurveyReportAnalytics - Task Already Running Error, user: {}, data: {}".format(request.user, data))
            return JsonResponse({'error_task': 'AlreadyRunningError'})

    def have_permission(self, user, block):
        """
            Verify if the user is instructor
        """
        """
        any([
            request.user.is_staff,
            CourseStaffRole(course_key).has_user(request.user),
            CourseInstructorRole(course_key).has_user(request.user)
        ])
        """
        try:
            block_key = UsageKey.from_string(block)
            course_key = block_key.course_key
            course = get_course_with_access(user, "load", course_key)
            data_researcher_access = user.has_perm(permissions.CAN_RESEARCH, course_key)
            return bool(has_access(user, 'instructor', course)) or bool(has_access(user, 'staff', course)) or data_researcher_access
        except Exception:
            return False

    def validate_and_get_data(self, request):
        """
            Verify format and course id
        """
        data = {'block': None}
        if request.GET.get("block", "") != "":
            # valida si existe el block_id
            if self.validate_block(request.GET.get("block", "")):
                data['block'] = request.GET.get("block", "")
        return data
        
    def validate_block(self, block_id):
        """
            Verify if block_id exists
        """
        try:
            block_key = UsageKey.from_string(block_id)
            if block_key.block_type != 'eol_survey':
                return False
            store = modulestore()
            block_item = store.get_item(block_key)
            return True
        except (InvalidKeyError, ItemNotFoundError) as e:
            return False