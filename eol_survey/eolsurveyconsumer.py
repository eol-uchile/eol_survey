"""TO-DO: Write a description of what this XBlock is."""

import json
import datetime
from pytz import utc
import pkg_resources
from six import text_type
from xblock.core import XBlock
from django.http import HttpResponse
from web_fragments.fragment import Fragment
from xmodule.exceptions import NotFoundError
from xmodule.capa_module import ProblemBlock
from xmodule.x_module import(shim_xmodule_js)
from django.template import Context, Template
from capa.util import convert_files_to_filenames
from xblock.scorable import ScorableXBlockMixin, Score
from common.lib.xmodule.xmodule.capa_base import RANDOMIZATION
from xmodule.util.xmodule_django import add_webpack_to_fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblock.fields import Integer, Scope, String, Dict, Float, Boolean, List, DateTime, JSONField

import logging
log = logging.getLogger(__name__)


class EolSurveyConsumerXBlock(ProblemBlock):

    display_name = String(
        display_name = "Display_name",
        help = "Display name for this module",
        default = "Encuestas",
        scope = Scope.settings,
    )
    survey_id = Integer(
        display_name = "ID de encuesta",
        help = "ID de la encuesta seleccionada",
        default=0,
        scope= Scope.settings,
    )

    # has_author_view = True
    # has_score = False
    # editable_fields = ('display_name', 'survey_id')

    has_score = False

    """
    TO-DO: document what your XBlock does.
    """   
    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")
    
    def get_survey_data(self):
        """
            this function makes it possible to load the select in the configurations
        """
        from .models import Survey
        surveys = list(Survey.objects.all().values('id','header'))
        survey_list = [{'id': survey['id'], 'header': survey['header']} for survey in surveys]
        return survey_list

    def generate_report_data(self, user_state_iterator, limit_responses=None):
        """
        Return a list of student responses to this block in a readable way.

        Arguments:
            user_state_iterator: iterator over UserStateClient objects.
                E.g. the result of user_state_client.iter_all_for_block(block_key)

            limit_responses (int|None): maximum number of responses to include.
                Set to None (default) to include all.

        Returns:
            each call returns a tuple like:
            ("username", {
                           "Question": "2 + 2 equals how many?",
                           "Answer": "Four",
                           "Answer ID": "98e6a8e915904d5389821a94e48babcf_10_1"
            })
        """

        from capa.capa_problem import LoncapaProblem, LoncapaSystem

        if self.category != 'eol_survey':
            raise NotImplementedError()

        if limit_responses == 0:
            # Don't even start collecting answers
            return
        capa_system = LoncapaSystem(
            ajax_url=None,
            # TODO set anonymous_student_id to the anonymous ID of the user which answered each problem
            # Anonymous ID is required for Matlab, CodeResponse, and some custom problems that include
            # '$anonymous_student_id' in their XML.
            # For the purposes of this report, we don't need to support those use cases.
            anonymous_student_id=None,
            cache=None,
            can_execute_unsafe_code=lambda: None,
            get_python_lib_zip=(lambda: get_python_lib_zip(contentstore, self.runtime.course_id)),
            DEBUG=None,
            filestore=self.runtime.resources_fs,
            i18n=self.runtime.service(self, "i18n"),
            node_path=None,
            render_template=None,
            seed=1,
            STATIC_URL=None,
            xqueue=None,
            matlab_api_key=None,
        )
        _ = capa_system.i18n.ugettext
        print(user_state_iterator)
        for user_state in user_state_iterator:
            if 'student_answers' not in user_state['state']:
                continue
            lcp = LoncapaProblem(
                problem_text=self.data,
                id=self.location.html_id(),
                capa_system=capa_system,
                # We choose to run without a fully initialized CapaModule
                capa_module=None,
                state={
                    'done': user_state['state'].get('done'),
                    'correct_map': user_state['state'].get('correct_map'),
                    'student_answers': user_state['state'].get('student_answers'),
                    'has_saved_answers': user_state['state'].get('has_saved_answers'),
                    'input_state': user_state['state'].get('input_state'),
                    'seed': user_state['state'].get('seed'),
                },
                seed=user_state['state'].get('seed'),
                # extract_tree=False allows us to work without a fully initialized CapaModule
                # We'll still be able to find particular data in the XML when we need it
                extract_tree=False,
            )

            for answer_id, orig_answers in lcp.student_answers.items():
                # Some types of problems have data in lcp.student_answers that isn't in lcp.problem_data.
                # E.g. formulae do this to store the MathML version of the answer.
                # We exclude these rows from the report because we only need the text-only answer.
                if answer_id.endswith('_dynamath'):
                    continue


                question_text = lcp.find_question_label(answer_id)
                answer_text = lcp.find_answer_text(answer_id, current_answer=orig_answers)
                correct_answer_text = lcp.find_correct_answer_text(answer_id)

                report = {
                    _("Answer ID"): answer_id,
                    _("Question"): question_text,
                    _("Answer"): answer_text,
                }
                if correct_answer_text is not None:
                    report[_("Correct Answer")] = correct_answer_text
                yield (user_state['username'], report)



    def author_view(self, context=None): 
        return self.student_view(context, show_detailed_errors = True)

    def studio_view(self, context):
        fragment = Fragment()
        context = {
            'xblock': self,
            'location': str(self.location).split('@')[-1],
            'survey_list': self.get_survey_data(),
            'survey_id': self.survey_id
        }
 
        fragment.content = self.render_template(
            'static/eol_survey/html/studio_view.html', context)
        fragment.add_css(self.resource_string("static/eol_survey/css/eolsurveyconsumer.css"))
        fragment.add_javascript(self.resource_string("static/eol_survey/js/eolsurveyconsumer_studio.js"))
        fragment.initialize_js('EolSurveyConsumerXBlock')
        return fragment

    # # TO-DO: change this view to display your data your own way.
    def student_view(self, context, show_detailed_errors=False):
        """
        The primary view of the EolSurveyConsumerXBlock, shown to students
        when viewing courses.
        """
        try: 
            self.lcp
        except Exception as err:
            html = self.handle_fatal_lcp_error(err if show_detailed_errors else None)
        
        else: 
            html = self.get_html()
        fragment = Fragment(html)
        add_webpack_to_fragment(fragment, 'ProblemBlockPreview')
        shim_xmodule_js(fragment, 'Problem')
        fragment.add_css(self.resource_string("static/eol_survey/css/eolsurveyconsumer.css"))
        return fragment
    def validate_data(self, id):
        from .models import Survey

        if Survey.objects.filter(id=id).exists():
            return Survey.objects.get(id=id).content
        else:
            return None

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Called when submitting the form in Studio.
        """
        try: 
            self.display_name = data.get('display_name')
            survey_id = int(data.get('id'))
            content = self.validate_data(survey_id)
            if content:

                self.data = content
                self.show_correctness = "never"
                self.showanswer = "never"
                self.weight = 0.0 
                self.force_save_button = False 
                self.show_reset_button = False
                self.survey_id = survey_id
                return {'result': 'success'}

            else:
                return{'result': 'error'}
                
        except (ValueError):
            return {'result': 'error'}

    def submit_problem(self, data, override_time=False):
        from capa.responsetypes import LoncapaProblemError, ResponseError, StudentInputError
        """
        Checks whether answers to a problem are correct

        Returns a map of correct/incorrect answers:
          {'success' : 'correct' | 'incorrect' | AJAX alert msg string,
           'contents' : html}
        """
        event_info = dict()
        event_info['state'] = self.lcp.get_state()
        event_info['problem_id'] = text_type(self.location)

        self.lcp.has_saved_answers = False
        answers = self.make_dict_of_responses(data)
        answers_without_files = convert_files_to_filenames(answers)
        event_info['answers'] = answers_without_files

        metric_name = u'capa.check_problem.{}'.format
        # Can override current time
        current_time = datetime.datetime.now(utc)
        if override_time is not False:
            current_time = override_time

        _ = self.runtime.service(self, "i18n").ugettext

        # Too late. Cannot submit
        if self.closed():
            log.error(
                'ProblemClosedError: Problem %s, close date: %s, due:%s, is_past_due: %s, attempts: %s/%s,',
                text_type(self.location),
                self.close_date,
                self.due,
                self.is_past_due(),
                self.attempts,
                self.max_attempts,
            )
            event_info['failure'] = 'closed'
            self.track_function_unmask('problem_check_fail', event_info)
            raise NotFoundError(_("Problem is closed."))

        # Problem submitted. Student should reset before checking again
        if self.done and self.rerandomize == RANDOMIZATION.ALWAYS:
            event_info['failure'] = 'unreset'
            self.track_function_unmask('problem_check_fail', event_info)
            raise NotFoundError(_("Problem must be reset before it can be submitted again."))

        # Problem queued. Students must wait a specified waittime before they are allowed to submit
        # IDEA: consider stealing code from below: pretty-print of seconds, cueing of time remaining
        if self.lcp.is_queued():
            prev_submit_time = self.lcp.get_recentmost_queuetime()

            waittime_between_requests = self.runtime.xqueue['waittime']
            if (current_time - prev_submit_time).total_seconds() < waittime_between_requests:
                msg = _(u"You must wait at least {wait} seconds between submissions.").format(
                    wait=waittime_between_requests)
                return {'success': msg, 'html': ''}

        # Wait time between resets: check if is too soon for submission.
        if self.last_submission_time is not None and self.submission_wait_seconds != 0:
            seconds_since_submission = (current_time - self.last_submission_time).total_seconds()
            if seconds_since_submission < self.submission_wait_seconds:
                remaining_secs = int(self.submission_wait_seconds - seconds_since_submission)
                msg = _(u'You must wait at least {wait_secs} between submissions. {remaining_secs} remaining.').format(
                    wait_secs=self.pretty_print_seconds(self.submission_wait_seconds),
                    remaining_secs=self.pretty_print_seconds(remaining_secs))
                return {
                    'success': msg,
                    'html': ''
                }

        try:
            # expose the attempt number to a potential python custom grader
            # self.lcp.context['attempt'] refers to the attempt number (1-based)
            self.lcp.context['attempt'] = self.attempts + 1
            correct_map = self.lcp.grade_answers(answers)
            # self.attempts refers to the number of attempts that did not
            # raise an error (0-based)
            self.attempts = self.attempts + 1
            self.lcp.done = True
            self.set_state_from_lcp()
            self.set_score(Score(raw_earned=0, raw_possible=0))
            self.set_last_submission_time()

        except (StudentInputError, ResponseError, LoncapaProblemError) as inst:
            if self.runtime.DEBUG:
                log.warning(
                    "StudentInputError in capa_module:problem_check",
                    exc_info=True
                )

            # Save the user's state before failing
            self.set_state_from_lcp()
            self.set_score(Score(raw_earned=0, raw_possible=0))

            # If the user is a staff member, include
            # the full exception, including traceback,
            # in the response
            if self.runtime.user_is_staff:
                msg = u"Staff debug info: {tb}".format(tb=traceback.format_exc())

            # Otherwise, display just an error message,
            # without a stack trace
            else:
                full_error = inst.args[0]
                try:
                    # only return the error value of the exception
                    msg = full_error.split("\\n")[-2].split(": ", 1)[1]
                except IndexError:
                    msg = full_error

            return {'success': msg}

        except Exception as err:
            # Save the user's state before failing
            self.set_state_from_lcp()
            self.set_score(Score(raw_earned=0, raw_possible=0))

            if self.runtime.DEBUG:
                msg = u"Error checking problem: {}".format(text_type(err))
                msg += u'\nTraceback:\n{}'.format(traceback.format_exc())
                return {'success': msg}
            raise
        published_grade = self.publish_grade()

        # success = correct if ALL questions in this problem are correct
        success = 'correct'
        for answer_id in correct_map:
            if not correct_map.is_correct(answer_id):
                success = 'incorrect'

        # NOTE: We are logging both full grading and queued-grading submissions. In the latter,
        #       'success' will always be incorrect
        event_info['grade'] = published_grade['grade']
        event_info['max_grade'] = published_grade['max_grade']
        event_info['correct_map'] = correct_map.get_dict()
        event_info['success'] = success
        event_info['attempts'] = self.attempts
        event_info['submission'] = self.get_submission_metadata_safe(answers_without_files, correct_map)
        self.track_function_unmask('problem_check', event_info)

        # render problem into HTML
        html = self.get_problem_html(encapsulate=False, submit_notification=True)

        # Withhold success indicator if hiding correctness
        if not self.correctness_available():
            success = 'submitted'

        return {
            'success': success,
            'contents': html
        }
    # pylint: enable=too-many-statements

    def render_template(self, template_path, context):
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        return template.render(Context(context))

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("EolSurveyConsumerXBlock",
             """<eolsurveyconsumer/>
             """),
            ("Multiple EolSurveyConsumerXBlock",
             """<vertical_demo>
                <eolsurveyconsumer/>
                <eolsurveyconsumer/>
                <eolsurveyconsumer/>
                </vertical_demo>
             """),
        ]
