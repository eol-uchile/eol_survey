# -*- coding: utf-8 -*-
import json
import pytest
import unittest
import textwrap
from . import views
from pytz import UTC
from .task import  generate
from mock import patch, Mock
from django.test import Client
from django.urls import reverse
from django.test import TestCase
from xblock.scorable import Score
from xblock.fields import ScopeIds
from eol_survey.models import Survey
from xblock.field_data import DictFieldData
from collections import defaultdict
from django.utils.translation import gettext as _
from .eolsurveyconsumer import EolSurveyConsumerXBlock
from edx_user_state_client.interface import XBlockUserState
from common.lib.xmodule.xmodule.tests import get_test_system
from lms.djangoapps.instructor_task.models import ReportStore
from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from opaque_keys.edx.keys import UsageKey
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from common.djangoapps.student.tests.factories import CourseAccessRoleFactory
from common.djangoapps.student.roles import CourseInstructorRole, CourseStaffRole
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from common.djangoapps.student.tests.factories import UserFactory, CourseEnrollmentFactory



import logging
logger = logging.getLogger(__name__)
test_config = {
    'PLATFORM_NAME': 'PLATFORM_NAME',
    'EOL_CONTACT_FORM_HELP_DESK_EMAIL': 'test@test.test'
}


class TestEolSurveyForm(TestCase):
    def setUp(self):

        super(TestEolSurveyForm, self).setUp()
        self.clientStaff = Client()
        self.clientNoStaff = Client()
        self.clientAnony = Client()
        with patch('common.djangoapps.student.models.cc.User.save'):
            self.user = UserFactory(
                username = 'testuser',
                password = '1234',
                is_staff = True
            )
            self.user2 = UserFactory(
                username = 'testuser2',
                password = '1234',
                is_staff = False
            )
        self.clientStaff.login(username= 'testuser', password= '1234')
        self.clientNoStaff.login(username= 'testuser2',password= '1234')

    def test_render_page(self):
        """
            Test GET function
        """
        url = reverse('Survey_form_view')
        response = self.clientStaff.get(url)
        self.assertEqual(response.status_code, 200)

    def test_validate_data(self):
        """
            Test data validation at backend
            1. Test without error
            2. Test with error in header
        """
        data = {
            'form-header': 'Encabezado n7',
            'form-description': 'Este es la encuesta de prueba',
            'form-content': '¿Que le parecio el curso?',
        }
        result = views.EolSurveyView().validate_data(data)
        self.assertEqual(result['error'], False)

        data['form-header'] = ''
        result = views.EolSurveyView().validate_data(data)
        self.assertEqual(result['error'], True)
        self.assertEqual(result['error_attr'], 'Encabezado')
    
    def test_successfully_create_survey(self): 
        """
            Create a new survey with all correct
        """
        data = { 
            'form-header': 'Encuesta n7',
            'form-description': 'Descripcion de una encuesta',
            'form-content': '¿Que le parecio el curso?',
        }
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertTrue(Survey.objects.filter(header= data['form-header']).exists())

        prueba = Survey.objects.filter(header= data['form-header']).first()
        self.assertEqual(prueba.header, data['form-header'])
        self.assertEqual(prueba.description, data['form-description'] )
        self.assertTrue("Encuesta Creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code, 200)
    
    def test_create_survey_blank_header(self):
        """
            In this test, a survey is created with a blank header 
        """
        data = {
            'form-header': '',
            'form-description': 'Descripcion de una encuesta',
            'form-content': '¿Que le parecio el curso',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code, 200)
    
    def test_create_survey_blank_desc(self):
        """
            In this test, a survey is created with a blank description 
        """

        data = {
            'form-header': 'Encuesta n7',
            'form-description': '',
            'form-content': '¿Que le parecio el curso',
        }        
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code, 200)

    def test_create_survey_blank_content(self):
        """
            In this test, a survey is created with a blank content 
        """

        data = {
            'form-header': 'Encuesta n7',
            'form-description': 'Descripcion de una encuesta',
            'form-content': '',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code, 200)

    def test_create_survey_no_staff(self):
        """
            In this test, a survey is created with a user no staff 
        """
                
        data = { 
            'form-header': 'Encuesta n7',
            'form-description': 'Descripcion de una encuesta',
            'form-content': '¿Que le parecio el curso?',
        }
        response = self.clientNoStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code,400)

    def test_create_survey_get(self):
        """
            In this test, a survey is created with a diferent method. 
            Always is post but in this case is get 
        """
        
        data = { 
            'form-header': 'Encuesta n7',
            'form-description': 'Descripcion de una encuesta',
            'form-content': '¿Que le parecio el curso?',
        }
        response = self.clientStaff.get(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code, 200)

    def test_create_survey_without_header(self):
        """
            In this test, a survey is created without header.
        """

        data = { 
            'form-description': 'Descripcion de una encuesta',
            'form-content': '¿Que le parecio el curso?',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(description= data['form-description']).exists())
        self.assertFalse("Encuesta creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code,400)
    
    def test_create_survey_without_desc(self):
        """
            In this test, a survey is created without description.
        """
        data = {
            'form-header': 'Encuesta n7',
            'form-content': '¿Que le parecio el curso?'
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code,400)
    
    def test_create_survey_without_content(self):
        """
            In this test, a survey is created without content.
        """
        data = {
            'form-header': 'Encuesta n7',
            'form-description': 'Esta es una descripcion de una encuesta',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta creada correctamente" in response._container[0].decode())
        self.assertEqual(response.status_code,400)
    
    def test_create_survey_anon(self):
        """
            when you try to create a survey, but the user is anonymous. 
            Result you cant create a survey 
        """

        data = { 
            'form-header': 'Encuesta n7',
            'form-description': 'Descripcion de una encuesta',
            'form-content': '¿Que le parecio el curso?',
        }
        response = self.clientAnony.post(reverse('Survey_form_view'), data)
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertEqual(response.status_code,400)
    
    def test_successfully_edit_survey(self):
        """
            In this test, a survey successfully edited.
            first a survey is created.
            after updating the database, the delivered data is compared with the database.
        """
        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encuesta editada',
            'form-description': 'Descripcion editada',
            'form-content': 'Contenido editado',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertTrue(Survey.objects.filter(header= data['form-header']).exists())
        self.assertEqual(survey.header, data['form-header'])
        self.assertEqual(survey.description, data['form-description'])
        self.assertEqual(survey.content, data['form-content'])
        self.assertTrue("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 200)

    def test_edit_survey_header_blank(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            In this case, the original survey had a header, but when edited it appears blank
        """
        
        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': '',
            'form-description': 'Descripcion editada',
            'form-content': 'Contenido editado',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(description= data['form-description']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 200)   

    def test_edit_survey_desc_blank(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            In this case, the original survey had a description, but when edited it appears blank
        """

        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encabezado n7',
            'form-description': '',
            'form-content': 'Contenido editado',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 200)    

    def test_edit_survey_content_blank(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            In this case, the original survey had a content, but when edited it appears blank
        """

        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encabezado n7',
            'form-description': 'Descripcion editada',
            'form-content': '',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 200)    

    def test_edit_survey_method_get(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            Always is post but in this case is get 
        """

        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encabezado n7',
            'form-description': 'Descripcion editada',
            'form-content': 'Cotenido nuevo',
        }
        response = self.clientStaff.get(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 200)    

    def test_edit_survey_without_header(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            In this case, the original survey had a header, but editing the survey removed header
        """

        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-description': 'Descripcion editada',
            'form-content': 'Cotenido nuevo',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(description= data['form-description']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 400)    

    def test_edit_survey_without_desc(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            In this case, the original survey had a description, but editing the survey removed description
        """

        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encuesta n7',
            'form-content': 'Contenido nuevo',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 400)    

    def test_edit_survey_without_content(self):
        """
            In this test, an attempt is made to edit a survey.
            first a survey is created.
            In this case, the original survey had a content, but editing the survey removed content
        """

        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encuesta n7',
            'form-description': 'Esta es una nueva descripcion',
        }
        response = self.clientStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 400)  

    def test_edit_survey_no_staff(self):
        """
            In this test, a survey is edited with a user no staff 
        """        
        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'inputId': survey.id,
            'form-header': 'Encuesta n7',
            'form-description': 'Esta es una nueva descripcion',
        }
        response = self.clientNoStaff.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertFalse("Encuesta Actualizada correctamente." in response._container[0].decode())
        self.assertEqual(response.status_code, 400)  

    def test_edit_survey_anon(self):
        """
            when you try to edit a survey, but the user is anonymous. 
            Result you cant edit a survey 
        """
        survey = Survey.objects.create(
            header= 'Encuesta existente',
            description= 'Descripcion existente',
            content= 'Cotenido existente'
        )

        data = {
            'survey_id': survey.id,
            'form-header': 'Encuesta editada',
            'form-description': 'Descripcion editada',
            'form-content': 'Contenido editado',
        }
        response = self.clientAnony.post(reverse('Survey_form_view'), data)
        survey.refresh_from_db()
        self.assertFalse(Survey.objects.filter(header= data['form-header']).exists())
        self.assertEqual(response.status_code, 400)

    def test_successfully_delete_survey(self):
        """
            In this test, a survey successfully delete.
            first a survey is created.
            check that the id no longer exists in the database,
            and only a staff can delete a survey
        """
        
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )       

        data = {
            'survey_id' : survey.id
        }
        response = self.clientStaff.post(reverse('delete_survey'), json.dumps(data), content_type= 'application/json')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Survey.objects.filter(id= survey.id).exists())

    def test_delete_survey_blank(self):
        """
            first a survey is created.
            when you try to delete a survey, but id is blank
        """
        
        data = {}
        response = self.clientStaff.post(reverse('delete_survey'), json.dumps(data), content_type= 'application/json')
        self.assertEqual(response.status_code, 400)

    def test_delete_survey_no_staff(self):
        """
            first a survey is created.
            when trying to delete a survey, but the user is not personal
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )       

        data = {
            'survey_id' : survey.id
        }
        response = self.clientNoStaff.post(reverse('delete_survey'), json.dumps(data), content_type= 'application/json')
        self.assertEqual(response.status_code, 400)
        
    def test_delete_survey_method_get(self):
        """
            first a survey is created.
            Always is post but in this case is get 
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )       

        data = {
            'survey_id' : survey.id
        }
        response = self.clientStaff.get(reverse('delete_survey'), data)
        self.assertEqual(response.status_code, 400)

    def test_delete_survey_no_json(self):
        """
            first a survey is created.
            to delete a survey it must be in Json,
            otherwise it will never be deleted correctly, for this purpose json.dumps() is used. 
        """
        
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )       

        data = 'this is not a Json'
        response = self.clientStaff.post(reverse('delete_survey'), data, content_type= 'application/json')

        self.assertEqual(response.status_code, 400)
        
    def test_delete_survey_anon(self):
        """
            when you try to delete a survey, but the user is anonymous. 
            Result you cant delete a survey 
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )       

        data = {
            'survey_id' : survey.id
        }
        response = self.clientAnony.post(reverse('delete_survey'), json.dumps(data), content_type= 'application/json')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Survey.objects.filter(id= survey.id).exists())

    def test_message_detail_successfully(self):
        """
            first a survey is created.
            Then the data is fetched based on the same Id, 
            and the expected data is compared with the response
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )     
        data = {
            'survey_id': survey.id
        }
        
        response = self.clientStaff.get(reverse('message_detail_api'), data)

        expected_content = {
            'content': {
                'header': survey.header,
                'description': survey.description,
                'content': survey.content
            }
        }
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf-8'), expected_content)
    
    def test_message_detail_without_survey_id(self):
        """
            In this case you want to bring the survey fields without any id, so it will fail. 
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )     
        data = {}
        
        response = self.clientStaff.get(reverse('message_detail_api'), data)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf-8'), {'error': True})
    
    def test_message_detail_string_id(self):
        """
            the id is always a number that can be transformed into an int, 
            if you give it a word it will fail
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )     
        data = {
            'survey_id': 'prueba'
        }
        
        response = self.clientStaff.get(reverse('message_detail_api'), data)

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf-8'), {'error': True})
    
    def test_message_detail_none_surveyId(self):
        """
            a value from a survey that does not exist in the database is given, 
            the response is compared with an error : True
        """
        data = {
            'survey_id': '999999'
        }
        response = self.clientStaff.get(reverse('message_detail_api'), data)
        
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(str(response.content, encoding='utf-8'), {'error': True})
    
    def test_message_detail_no_staff(self):
        """
            This function can only be used with staff rolls.
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )     
        data = {
            'survey_id': survey.id
        }
        
        response = self.clientNoStaff.get(reverse('message_detail_api'), data)

        self.assertEqual(response.status_code, 400)
        
    def test_message_detail_method_post(self):
        """
            Always is get but in this case is post 
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )     
        data = {
            'survey_id': survey.id
        }
        
        response = self.clientStaff.post(reverse('message_detail_api'), data)

        self.assertEqual(response.status_code, 400)
    
    def test_message_detail_anon(self):
        """
            When you try to bring the fields of a survey, but the user is anonymous.
            Therefore, it will not be possible to bring in the survey fields.
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Esta es el nuevo contenido'
        )     
        data = {
            'survey_id': survey.id
        }
        
        response = self.clientAnony.get(reverse('message_detail_api'), data)

        self.assertEqual(response.status_code, 400)    

    def test_successfully_get_survey_json(self):
        """
            first a survey is created.
            the response is compared with the list that should be generated from the surveys.
        """
        survey = Survey.objects.create(
            header= 'Encuesta nueva',
            description= 'Esta es la descripcion nueva',
            content= 'Este es el nuevo contenido'
        )
        response = self.clientStaff.get(reverse('get_survey_json'))

        self.assertEqual(response.status_code,200)
        self.assertJSONEqual(
            str(response.content, encoding='utf-8'), 
            {"surveys": [{"id": survey.id, "header": survey.header}]}
        )

    def test_get_survey_json_no_staff(self):
        """
            This function can only be used with staff rolls.
        """
        response = self.clientNoStaff.get(reverse('get_survey_json'))

        self.assertEqual(response.status_code, 400)

    def test_get_survey_json_method_post(self):
        """
            Always is get but in this case is post 
        """
        response = self.clientStaff.post(reverse('get_survey_json'))

        self.assertEqual(response.status_code, 400) 

    def test_get_survey_json_anon(self):
        """
            If your user is anonymous you will not be able to bring the list of surveys.   
        """
        response = self.clientAnony.post(reverse('get_survey_json'))

        self.assertEqual(response.status_code, 400)
    

class TestRequest(object):
    # pylint: disable=too-few-public-methods
    # cuando solo consumimos una api externa. 
    """
    Module helper for @json_handler
    """
    method = None
    body = None
    success = None

class CapaFactory(object):
    """
    A helper class to create problem modules with various parameters for testing.
    """

    sample_problem_xml = textwrap.dedent("""\
        <?xml version="1.0"?>
        <problem>
            <text>
                <p>What is pi, to two decimal places?</p>
            </text>
        <numericalresponse answer="3.14">
        <textline math="1" size="30"/>
        </numericalresponse>
        </problem>
    """)

    num = 0

    @classmethod
    def next_num(cls):
        cls.num += 1
        return cls.num

    @classmethod
    def input_key(cls, response_num=2, input_num=1):
        """
        Return the input key to use when passing GET parameters
        """
        return "input_" + cls.answer_key(response_num, input_num)

    @classmethod
    def answer_key(cls, response_num=2, input_num=1):
        """
        Return the key stored in the capa problem answer dict
        """
        return ("%s_%d_%d" % ("-".join(['i4x', 'edX', 'capa_test', 'problem', 'SampleProblem%d' % cls.num]),
                              response_num, input_num))

    @classmethod
    def create(cls, attempts=None, problem_state=None, correct=False, xml=None, override_get_score=True, **kwargs):
        """
        All parameters are optional, and are added to the created problem if specified.

        Arguments:
            graceperiod:
            due:
            max_attempts:
            showanswer:
            force_save_button:
            rerandomize: all strings, as specified in the policy for the problem

            problem_state: a dict to to be serialized into the instance_state of the
                module.

            attempts: also added to instance state.  Will be converted to an int.
        """
        location = BlockUsageLocator(
            CourseLocator("edX", "capa_test", "2012_Fall", deprecated=True),
            "problem",
            "SampleProblem{0}".format(cls.next_num()),
            deprecated=True,
        )
        if xml is None:
            xml = cls.sample_problem_xml
        field_data = {'data': xml}
        field_data.update(kwargs)
        if problem_state is not None:
            field_data.update(problem_state)
        if attempts is not None:
            # converting to int here because I keep putting "0" and "1" in the tests
            # since everything else is a string.
            field_data['attempts'] = int(attempts)

        system = get_test_system(course_id=location.course_key)
        system.user_is_staff = kwargs.get('user_is_staff', False)
        system.render_template = Mock(return_value="<div>Test Template HTML</div>")
        module = EolSurveyConsumerXBlock(
            system,
            DictFieldData(field_data),
            ScopeIds(None, 'problem', location, location),
        )
        assert module.lcp

        if override_get_score:
            if correct:
                # TODO: probably better to actually set the internal state properly, but...
                module.score = Score(raw_earned=1, raw_possible=1)
            else:
                module.score = Score(raw_earned=0, raw_possible=1)

        module.graded = 'False'
        module.weight = 1
        return module

class TestEolSurveyXBlock(CapaFactory, unittest.TestCase):


    def setUp(self):
        super(TestEolSurveyXBlock, self).setUp()
        self.module = CapaFactory.create()
        
        self.find_question_label_patcher = patch(
            'capa.capa_problem.LoncapaProblem.find_question_label',
            lambda self, answer_id: answer_id
        )
        self.find_answer_text_patcher = patch(
            'capa.capa_problem.LoncapaProblem.find_answer_text',
            lambda self, answer_id, current_answer: current_answer
        )
        self.find_question_label_patcher.start()
        self.find_answer_text_patcher.start()
        self.addCleanup(self.find_question_label_patcher.stop)
        self.addCleanup(self.find_answer_text_patcher.stop)


    def test_validate_field_data(self):
        """
            validates the xblock default values
        """
        self.assertEqual(self.module.display_name, 'Encuestas')
        self.assertEqual(self.module.survey_id, 0)
    
    def test_edit_block_studio(self):
        """
            the display_name and survey_id values are modified, studio_submit should ave it correctlys
        """
        request = TestRequest()
        request.method = 'POST'
        with patch('eol_survey.eolsurveyconsumer.EolSurveyConsumerXBlock.validate_data') as mock_val_data: 
            mock_val_data.return_value = '<problem/>'
            data = json.dumps({'display_name': 'testname', 'id': "140"})
            request.body = data.encode()
            response = self.module.studio_submit(request)
            self.assertEqual(self.module.display_name, 'testname')
            self.assertEqual(self.module.survey_id, 140)
    
    def test_edit_block_studio_string_id(self):
        """
            the fields are edited but survey_id is now a text, 
            so it should not be possible to save the fields.
        """
        request = TestRequest()
        request.method = 'POST'
        with patch('eol_survey.eolsurveyconsumer.EolSurveyConsumerXBlock.validate_data') as mock_val_data:
            mock_val_data.return_value = '<problem/>'
            data = json.dumps({'display_name': 'testname', 'id': 'cien'})
            request.body = data.encode()
            response = self.module.studio_submit(request)
            response_data = json.loads(response.text)
            result_field = response_data.get('result')
            self.assertEqual(response.status_code,200)
            self.assertEqual(result_field, 'error')

    def test_edit_block_studio_None_id(self):
        """
            the fields are edited, but this time with a survey_id that does not exist, 
            the value of validate_data is used as None
        """
        request = TestRequest()
        request.method = 'POST'
        with patch('eol_survey.eolsurveyconsumer.EolSurveyConsumerXBlock.validate_data') as mock_val_data: 
            mock_val_data.return_value = None
            data = json.dumps({'display_name': 'testname', 'id': "9999"}) 
            request.body = data.encode()
            response = self.module.studio_submit(request)
            self.assertEqual(self.module.display_name, 'testname')
            self.assertEqual(self.module.survey_id, 0)

    def test_submit_problem_score(self):
        module = CapaFactory.create(attempts=1)

        # Simulate that all answers are marked correct, no matter
        # what the input is, by patching CorrectMap.is_correct()
        # Also simulate rendering the HTML
        with patch('common.lib.capa.capa.correctmap.CorrectMap.is_correct') as mock_is_correct:
            with patch('xmodule.capa_module.ProblemBlock.get_problem_html') as mock_html:
                mock_is_correct.return_value = True
                mock_html.return_value = "Test HTML"

                # Check the problem
                get_request_dict = {CapaFactory.input_key(): '3.14'}
                result = module.submit_problem(get_request_dict)

        # Expect that the problem is marked correct
        assert result['success'] == 'correct'

        # Expect that we get the (mocked) HTML
        assert result['contents'] == 'Test HTML'

        # Expect that the number of attempts is incremented by 1
        assert module.attempts == 2
        # and that this was considered attempt number 2 for grading purposes
        assert module.lcp.context['attempt'] == 2

        assert module.get_score().raw_earned == 0 
    
    def test_generate_report_data_correct(self):
        """
            report can be generated correctly
        """
        descriptor = self._get_descriptor()
        user_count = 5
        response_count = 10
        report_data = list(descriptor.generate_report_data(
            self._mock_user_state_generator(
                user_count=user_count,
                response_count=response_count,
            )
        ))
        self.assertEqual(user_count * response_count, len(report_data))

    def _get_descriptor(self):
        """
            descriptor works correctly when block_type = eol_survey
        """
        scope_ids = Mock(block_type='eol_survey')
        descriptor = EolSurveyConsumerXBlock(get_test_system(), scope_ids=scope_ids)
        descriptor.runtime = Mock()
        descriptor.data = '<problem/>'
        return descriptor

    def _mock_user_state_generator(self, user_count=1, response_count=10):
        response = []
        
        for uid in range(user_count):
            data =  self._user_state(username='user{}'.format(uid), response_count=response_count)
            response.append({"username": data.username, "state": data.state})
        return response


    def _user_state(self, username='testuser', response_count=10, suffix=''):
        return XBlockUserState(
            username=username,
            state={
                'student_answers': {
                    '{}_answerid_{}{}'.format(username, aid, suffix): '{}_answer_{}'.format(username, aid)
                    for aid in range(response_count)
                },
                'seed': 1,
                'correct_map': {},
            },
            block_key=None,
            updated=None,
            scope=None,
        )
    
    def test_generate_report_data_error(self):
        """
            here it is not possible to create the report because
            the descriptor is not properly configured.
        """
        descriptor = self._get_descriptor_error()
        user_count = 5
        response_count = 10
        try:
            report_data = list(descriptor.generate_report_data(
                self._mock_user_state_generator(
                    user_count=user_count,
                    response_count=response_count,
                )
            ))
            self.assertTrue(False)

        except NotImplementedError:
            self.assertTrue(True)
            

    def _get_descriptor_error(self):
        """
            when setting the block_type anything other than eol_survey will fail to set the descriptor.
        """
        scope_ids = Mock(block_type='samdjlnasjdka')
        descriptor = EolSurveyConsumerXBlock(get_test_system(), scope_ids=scope_ids)
        descriptor.runtime = Mock()
        descriptor.data = '<problem/>'
        return descriptor


class TestEolSurveyReportView(ModuleStoreTestCase):
    def setUp(self):
        # USER_COUNT = 11
        super(TestEolSurveyReportView, self).setUp()
        self.course = CourseFactory.create(
            org='mss',
            course='999',
            display_name='2021',
            emit_signals=True, 
            run= 'test')
        aux = CourseOverview.get_from_id(self.course.id)
        with self.store.bulk_operations(self.course.id, emit_signals=False):
            self.chapter = ItemFactory.create(
                parent_location=self.course.location,
                category="chapter",
            )
            self.section = ItemFactory.create(
                parent_location=self.chapter.location,
                category="sequential",
            )
            self.subsection = ItemFactory.create(
                parent_location=self.section.location,
                category="vertical",
            )
            self.items = [
                ItemFactory.create(
                    parent_location=self.subsection.location,
                    category="eol_survey"
                )
            ]
        self.block_id = str(self.items[0].location)
        #self.block_id = 'block-v1:mss+999+2021+type@eol_survey+block@9d584d6a1bb345b1a1930e4358ba8f6a'
        with patch('common.djangoapps.student.models.cc.User.save'):
            # staff user
            self.client_instructor = Client()
            self.client_student = Client()
            self.client_noStaff = Client()
            self.client_staff = Client()
            self.user_instructor = UserFactory(
                username='instructor',
                password='12345',
                email='instructor@edx.org',
                is_staff=False)
            self.user_noStaff = UserFactory(
                username='noStaff',
                password='12345',
                email='noStaff@edx.org',
                is_staff=False)
            self.user_staff = UserFactory(
                username='Staff',
                password='12345',
                email='Staff@edx.org',
                is_staff=True)
            role = CourseInstructorRole(self.course.id)
            role.add_users(self.user_instructor)
            role2 = CourseStaffRole(self.course.id)
            role2.add_users(self.user_staff)
            self.client_instructor.login(
                username='instructor', password='12345')
            self.client_noStaff.login(
                username='noStaff', password='12345')
            self.client_staff.login(
                username='Staff', password= '12345')
            self.student = UserFactory(
                username='student',
                password='test',
                email='student@edx.org')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id, mode='honor')
            self.student2 = UserFactory(
                username='student2',
                password='test',
                email='student2@edx.org')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student2, course_id=self.course.id, mode='honor')
            self.client_student.login(
                username='student', password='test')
            # Create and Enroll data researcher user
            self.data_researcher_user = UserFactory(
                username='data_researcher_user',
                password='test',
                email='data.researcher@edx.org')
            CourseEnrollmentFactory(
                user=self.data_researcher_user,
                course_id=self.course.id, mode='audit')
            CourseAccessRoleFactory(
                course_id=self.course.id,
                user=self.data_researcher_user,
                role='data_researcher',
                org=self.course.id.org
            )
            self.client_data_researcher = Client()
            self.assertTrue(self.client_data_researcher.login(username='data_researcher_user', password='test'))
    
    def _verify_csv_file_report(self, report_store, expected_data):
        """
        Verify course survey data.
        """
        report_csv_filename = report_store.links_for(self.course.id)[0][0]
        report_path = report_store.path_to(self.course.id, report_csv_filename)
        with report_store.storage.open(report_path) as csv_file:
            csv_file_data = csv_file.read()
            # Removing unicode signature (BOM) from the beginning
            csv_file_data = csv_file_data.decode("utf-8-sig")
            for data in expected_data:
                self.assertIn(data, csv_file_data)

    def test_survey_report_analytics_get_url(self):
        """
            Test eol_survey_report_analytics view
        """
        response = self.client_instructor.get(reverse('eolSurveyReport'))
        request = response.request
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request['PATH_INFO'], '/Report_Survey')

    @patch("eol_survey.utils.modulestore")    
    @patch("eol_survey.utils.get_report_xblock")
    def test_eol_survey_report_analytics_get_all_data(self, report, store_mock):
        """
            Test eol_survey_report_analytics view data
        """
        u1_state_1 = {_("Answer ID"): 'answer_id_1',
            _("Question"): 'question_text_1',
            _("Answer"): 'correct_answer_text_1',
            _("Correct Answer") : 'correct_answer_text_1'
            }
        u1_state_2 = {_("Answer ID"): 'answer_id_2',
            _("Question"): 'question_text_2',
            _("Answer"): 'asdadsadsa',
            _("Correct Answer") : 'correct_answer_text_2'
            }
        u2_state_1 = {_("Answer ID"): 'answer_id_1',
            _("Question"): 'question_text_1',
            _("Answer"): 'correct_answer_text_1',
            _("Correct Answer") : 'correct_answer_text_1'
            }
        u2_state_2 = {_("Answer ID"): 'answer_id_2',
            _("Question"): 'question_text_2',
            _("Answer"): 'correct_answer_text_4',
            _("Correct Answer") : 'correct_answer_text_2'
            }
        generated_report_data = {
            self.student.username : [u1_state_1,u1_state_2],
            self.student2.username : [u2_state_1,u2_state_2],
            }               
        report.return_value = generated_report_data
        store_mock = Mock()
        from lms.djangoapps.courseware.models import StudentModule
        data = {'block': self.block_id, 'course': str(self.course.id), 'base_url':'this_is_a_url'}
        task_input = {'data': data }
        usage_key = UsageKey.from_string(self.block_id)
        module = StudentModule(
            module_state_key=usage_key,
            student=self.student,
            course_id=self.course.id,
            module_type='eol_survey',
            state='{"attempts": 1, "input_state": {"answer_id_1": 1, "answer_id_2": 2}}')
        module.save()
        module2 = StudentModule(
            module_state_key=usage_key,
            student=self.student2,
            course_id=self.course.id,
            module_type='eol_survey',
            state='{"attempts": 2, "input_state": {"answer_id_1": 1, "answer_id_2": 2}}')
        module2.save()
        with patch('lms.djangoapps.instructor_task.tasks_helper.runner._get_current_task'):
            result = generate(
                None, None, self.course.id,
                task_input, 'Eol_Survey_Report_Analytics'
            )
        report_store = ReportStore.from_config(config_name='GRADES_DOWNLOAD')
        header_row = ";".join(['Username', 'Email', 'Run', 'Pregunta 1', 'Pregunta 2'])
        student_row1 = ";".join([
            self.student.username,
            self.student.email,
            '',
            u1_state_1[_("Answer")],
            u1_state_2[_("Answer")],
        ])
        student_row2 = ";".join([
            self.student2.username,
            self.student2.email,
            '',
            u2_state_1[_("Answer")],
            u2_state_2[_("Answer")],
        ])
        expected_data = [
            header_row, 
            student_row1, 
            student_row2,
            'Pregunta 1;question_text_1',
            'Pregunta 2;question_text_2',
            ]
        self._verify_csv_file_report(report_store, expected_data)

    @patch("eol_survey.utils.modulestore")
    @patch("eol_survey.utils.get_report_xblock")
    def test_eol_report_analytics_get_no_responses(self, report, store_mock):
        """
            Test eol_report_analytics view data no student responses
        """
        generated_report_data = defaultdict(list)            
        report.return_value = generated_report_data
        store_mock = Mock()
        from lms.djangoapps.courseware.models import StudentModule
        data = {'block': self.block_id, 'course': str(self.course.id), 'base_url':'this_is_a_url'}
        task_input = {'data': data}
        usage_key = UsageKey.from_string(self.block_id)
        module = StudentModule(
            module_state_key=usage_key,
            student=self.student,
            course_id=self.course.id,
            module_type='eol_survey',
            state='{}')
        module.save()
        with patch('lms.djangoapps.instructor_task.tasks_helper.runner._get_current_task'):
            result = generate(
                None, None, self.course.id,
                task_input, 'Eol_Survey_Report_Analytics'
            )
        report_store = ReportStore.from_config(config_name='GRADES_DOWNLOAD')
        expected_data = [
            ]
        self._verify_csv_file_report(report_store, expected_data)



    def test_eol_survey_report_analytics_no_data_block(self):
        """
            Test eol_survey_report_analytics view no exitst block params
        """
        data = {
            'course':str(self.course.id)
        }
        response = self.client_instructor.get(reverse('eolSurveyReport'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response._container[0].decode()), {'error': 'Falta parametro block o parametro incorrecto'})
    
    @patch('eol_survey.views.UsageKey')
    def test_eol_survey_report_analytics_block_no_exists(self, mock_usageKey):
        """
            Test eol_survey_report_analytics view when block no exists
        """
        mock_usageKey.configure_mock(course_key=self.course.id)
        data = {
            'block':self.block_id,
            'course': str(self.course.id)
        }
        response = self.client_instructor.get(reverse('eolSurveyReport'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response._container[0].decode()), {'error': 'Falta parametro block o parametro incorrecto'})

    def test_eol_survey_report_analytics_block_no_eol_survey(self):
        """
            Test eol_survey_report_analytics view when block type is not problem type
        """
        data = {
            'block':'block-v1:mss+999+2021+type@scorm+block@aecf834d50a34f93a03f43bd20723ed7',
            'course': str(self.course.id)
        }
        response = self.client_instructor.get(reverse('eolSurveyReport'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response._container[0].decode()), {'error': 'Falta parametro block o parametro incorrecto'})

    def test_eol_survey_report_analytics_get_user_is_anonymous(self):
        """
            Test eol_survey_report_analytics view when user is anonymous
        """
        client = Client()
        response = self.client.get(reverse('eolSurveyReport'))
        request = response.request
        self.assertEqual(response.status_code, 404)

    @patch("eol_survey.views.EolSurveyReportAnalyticsView.validate_and_get_data")
    def test_eol_survey_report_analytics_get_user_no_permission(self, data_mock):
        """
            Test eol_survey_rsurvey_eport_analytics view when user is a student
        """
        usage_key = UsageKey.from_string(self.block_id)
        data = {
            'block':self.block_id,
            'course': str(self.course.id)
        }
        data_mock.return_value = data
        response = self.client_student.get(reverse('eolSurveyReport'), data)
        request = response.request
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response._container[0].decode()), {'error': 'Usuario no tiene rol para esta funcionalidad'})
    
    @patch("eol_survey.views.EolSurveyReportAnalyticsView.have_permission")
    @patch("eol_survey.views.EolSurveyReportAnalyticsView.validate_and_get_data")
    def test_eol_survey_report_analytics_get_data_researcher(self, data_mock, permission_mock):
        """
            Test eol_survey_report_analytics view when user is data researcher
        """
        block_id = 'block-v1:mss+999+2021+type@eol_survey+block@9d584d6a1bb345b1a1930e4358ba8f6a'
        usage_key= UsageKey.from_string(block_id)
        permission_mock.return_value = True
        data = {
            'block': block_id,
            'course': str(usage_key.course_key)
        }
        data_mock.return_value = data
        response = self.client_data_researcher.get(reverse('eolSurveyReport'), data)
        request = response.request
        r = json.loads(response._container[0].decode())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(r['status'], 'La analitica de las encuestas esta siendo creada, en un momento estará disponible para descargar.')
    
    def test_successfully_get_eol_survey_responses(self):
        """
            Test to load cb_survey in the instructor page. With a survey load in the cb
        """
        from lms.djangoapps.courseware.models import StudentModule
        usage_key = UsageKey.from_string(self.block_id)
        module = StudentModule(
            module_state_key=usage_key,
            student=self.student,
            course_id=self.course.id,
            module_type='eol_survey',
            state='{"attempts": 1, "input_state": {"answer_id_1": 1}}')
        module.save()
        response = self.client_staff.get(reverse('survey_responses', kwargs= {'course_id':self.course.id}))
        self.assertEqual(response.status_code,200)
        self.assertJSONEqual(
            str(response.content, encoding='utf-8'), 
            {"response": [{'location': self.block_id, 'name_survey': self.items[0].display_name, 'parent_display_name': '{} > {} > {}'.format(self.chapter.display_name,self.section.display_name, self.subsection.display_name) }]}
        ) 

    def test_successfully_get_eol_survey_no_responses(self):
        """
            Test to load cb_survey in instructor page. But in this case dosent exist a survey to load
        """
        response = self.client_staff.get(reverse('survey_responses', kwargs= {'course_id':self.course.id}))
        self.assertEqual(response.status_code,200)
        self.assertJSONEqual(
            str(response.content, encoding='utf-8'), 
            {"response": []}
        ) 
        
    def test_get_eol_survey_responses_staff(self):
        """
            This function can only be used with staff rolls.
        """

        response = self.client_staff.get(reverse('survey_responses', kwargs= {'course_id':self.course.id}))
        self.assertEqual(response.status_code, 200)

    def test_get_eol_survey_responses_instructor(self):
        """
            This function can only be used with instructor rolls.
        """

        response = self.client_instructor.get(reverse('survey_responses', kwargs= {'course_id':self.course.id}))    
        self.assertEqual(response.status_code, 200)

    def test_get_eol_survey_responses_no_staff(self):
        """
            This function can only be used with staff rolls.
        """
        response = self.client_noStaff.get(reverse('survey_responses', kwargs = {'course_id':self.course.id}))

        self.assertEqual(response.status_code, 400)
