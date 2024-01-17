import json 
from .models import Survey    
from django.http import HttpResponse
from django.http import JsonResponse
from .utils import get_eol_survey_responses
from django.views.decorators.csrf import csrf_exempt

import logging
log = logging.getLogger(__name__)

def message_detail(request):
    # allows to query the database if the survey id exists, if so, brings the fields in a Json
    if request.method != "GET":
        return HttpResponse(status=400)

    survey_id = request.GET.get('survey_id')
    if not request.user.is_anonymous and request.user.is_staff: 
        if survey_id: 
            try: 
                message = Survey.objects.get(id=survey_id)
                content = {
                    'header': message.header,
                    'description': message.description,
                    'content': message.content  
                }           
                return JsonResponse({'content':content })
            except: 
                return JsonResponse({'error': True})
            
        else: 
            return JsonResponse({'error': True})
    
    else:
        log.error("User dont have permission or is not staff, user: {}".format(request.user))
        return HttpResponse(status=400)
        

@csrf_exempt
def delete_survey(request):
    # transforms the data into a json, and if the survey_id exists, deletes it
    if request.method != "POST":
        return HttpResponse(status=400)
    try:
        data = json.loads(request.body)
        
    except json.decoder.JSONDecodeError:
        return HttpResponse(status=400)
        
    if 'survey_id' not in data: 
        return HttpResponse(status=400)
    survey_id = data.get('survey_id')
    if not request.user.is_anonymous and request.user.is_staff: 
        if survey_id: 
            try: 
                survey = Survey.objects.get(id=survey_id)
                survey.delete()
                return JsonResponse({'success': True})
            except Survey.DoesNotExist: 
                return JsonResponse({'success': False, 'error': 'dicha encuesta no existe.'})
        else: 
            return JsonResponse({'success': False, 'error': 'No se proporcionó una survey_id'})
    else: 
        log.error("User dont have permission or is not staff, user: {}".format(request.user))
        return HttpResponse(status=400)
    

  
def get_survey_json(request):
    # makes a list of all the polls in the database and transforms them into a json, this function is used to load the combobox. 
    if request.method != "GET":
        return HttpResponse(status=400)
    if not request.user.is_anonymous and request.user.is_staff: 
        surveys = list(Survey.objects.all().values('id','header'))
        surveys_json= [{'id': survey['id'], 'header': survey['header']} for survey in surveys] 
        return JsonResponse({'surveys': surveys_json})
    
    else: 
        log.error("User dont have permission or is not staff, user: {}".format(request.user))
        return HttpResponse(status=400)

