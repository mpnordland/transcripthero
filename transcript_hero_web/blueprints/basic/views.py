import os
import re
from flask import (render_template, request, redirect,
                   url_for, abort, flash, send_file)
from flask_security import current_user, login_required, roles_required, logout_user
from .forms import (TranscriptSearchForm, AccountSettingsForm,
                    TranscriptWizard, DeleteAccountForm,
                    GradingScaleForm, DeleteGradingScaleForm,
                    PaymentInformationForm, DeleteTranscriptForm,
                    CancelSubscriptionForm, TranscriptSettingsForm)
from transcript_hero.database.models import SubscriptionStanding, PayApi
from transcript_hero.business.limits import LimitService
from transcript_hero.business.grading import GradingService
from transcript_hero.payment import get_payment_api
from transcript_hero.errors import LimitError
from transcript_hero_web.uploads import signatures
from transcript_hero_web.pdf import render_pdf
from transcript_hero_web.payment import (
    contribute_payment_form, warn_subscription_absent)


class BasicViews:
    def __init__(self, th_context):
        self.db = th_context.db
        self.app = th_context.app
        self.transcript_service = th_context.transcript_service
        self.grading_service = th_context.grading_service
        self.user_service = th_context.user_service
        self.subscription_service = th_context.subscription_service
        self.sub_manager = th_context.sub_manager

    @login_required
    @warn_subscription_absent
    def index(self):
        form = TranscriptSearchForm()
        name = None
        begin = None
        end = None
        if form.validate_on_submit():
            name = form.name.data
            begin = form.year_start.data
            end = form.year_end.data

        transcripts = self.transcript_service.search_transcripts(
            current_user.id,
            name, begin, end)
        can_add_transcript = not LimitService.reached_transcript_limit(
            current_user)
        return render_template('basic/index.html', search_form=form,
                               can_add_transcript=can_add_transcript,
                               transcripts=transcripts)

    @login_required
    @warn_subscription_absent
    def grading_scales(self):
        grading_scales = self.grading_service.get_grading_scales(
            current_user.id)

        return render_template('basic/grading_scales.html',
                               grading_scales=grading_scales)

    @login_required
    @warn_subscription_absent
    def grading_scale(self, grading_scale_id=None):

        if grading_scale_id:
            grading_scale = self.grading_service.get_user_grading_scale(
                grading_scale_id, current_user.id)
        else:
            grading_scale = GradingService.new_grading_scale(current_user)

        form = GradingScaleForm(obj=grading_scale)
        do_redirect = False
        button = ''
        target = url_for('basic.grading_scales')

        if 'button' in request.form:
            button = request.form['button']

        if form.validate_on_submit():
            form.populate_obj(grading_scale)
            if button == 'add-grade-increment' and grading_scale.id:
                self.grading_service.add_grade_increment(grading_scale)
                do_redirect = True
                target = url_for('basic.grading_scale',
                                 grading_scale_id=grading_scale.id)

            elif button == 'add-grade-increment' and not grading_scale.id:
                flash(
                    "You must save the grading scale before adding increments",
                    category='warning'
                )

            elif button == 'save':
                do_redirect = True
                self.grading_service.save_grading_scale(grading_scale)
                target = url_for('basic.grading_scales')

            elif button == 'save-continue':
                do_redirect = True
                self.grading_service.save_grading_scale(grading_scale)
                flash("Grading Scale Saved")
                target = url_for('basic.grading_scale',
                                 grading_scale_id=grading_scale.id)

        if button.startswith('delete-increments'):
            try:
                increment_index = int(button.split('-')[-1])
                grade_increment = grading_scale.increments[increment_index]
                self.grading_service.delete_grade_increment(grade_increment)
                do_redirect = True
                target = url_for('basic.grading_scale',
                                 grading_scale_id=grading_scale.id)
            except (ValueError, IndexError):
                pass

        if do_redirect:
            return redirect(target)

        return render_template('basic/grading_scale.html',
                               grading_scale=grading_scale, form=form)

    @login_required
    @warn_subscription_absent
    def delete_grading_scale(self, grading_scale_id):
        delete_form = DeleteGradingScaleForm()
        grading_scale = self.grading_service.get_user_grading_scale(
            grading_scale_id, current_user.id)

        if delete_form.validate_on_submit() and grading_scale:
            grading_scale_name = grading_scale.name
            self.grading_service.delete_grading_scale(grading_scale)

            flash("Grading scale {} has been deleted".format(
                grading_scale_name), 'info')

            return redirect(url_for('basic.grading_scales'))

        return render_template("basic/delete_grading_scale.html",
                               grading_scale=grading_scale,
                               delete_form=delete_form)

    @login_required
    @warn_subscription_absent
    def account_settings(self):
        form = AccountSettingsForm(obj=current_user)
        if form.validate_on_submit():

            form.populate_obj(current_user)
            self.user_service.save(current_user)

            return redirect(url_for('basic.account_settings'))

        payment_methods = []
        can_cancel = False
        if current_user.subscription:
            payment_methods = self.sub_manager.get_payment_methods(
                current_user.subscription
            )
            payment_api = get_payment_api(
                current_user.subscription.pay_api, self.app.config)
            can_cancel = payment_api.can_cancel(
            ) and current_user.subscription.standing != SubscriptionStanding.CANCELED

            payment_update_label = payment_api.get_payment_update_label()
        else:
            payment_api = get_payment_api(
                PayApi[self.app.config['TRANSCRIPT_HERO_DEFAULT_PAY_API']], self.app.config)
            payment_update_label = payment_api.get_payment_update_label()

        context = {
            "settings_form": form,
            "subscription": current_user.subscription,
            "payment_methods": payment_methods,
            "can_cancel": can_cancel,
            "update_payment_label": payment_update_label,
        }

        return render_template('basic/account_settings.html', **context)

    @login_required
    def payment_information(self):
        form_class = contribute_payment_form(
            PaymentInformationForm, self.app.config)
        form = form_class()
        if form.validate_on_submit():
            if self.sub_manager.update_payment_method(
                    current_user.subscription, form.data["payment_token"]):
                flash("Payment information updated")
                return redirect(url_for("basic.account_settings"))
            else:
                flash("Error saving payment information", 'warning')

        return render_template(
            'basic/payment_information.html',
            form=form,
            payment_context="update"
        )

    @login_required
    def cancel_subscription(self):
        cancel_form = CancelSubscriptionForm()
        subscription = current_user.subscription

        if cancel_form.validate_on_submit() and subscription:
            destination = self.sub_manager.cancel(subscription)

            flash("Your subscription has been canceled", 'info')

            if destination is not None:
                target = destination
            else:
                target = url_for('basic.index')

            return redirect(target)

        return render_template("basic/cancel_subscription.html",
                               subscription=subscription,
                               cancel_form=cancel_form)

    def get_transcript_for_editing(self, transcript_id):
        if transcript_id:
            transcript = self.transcript_service.get_user_transcript(
                transcript_id, current_user.id)
        else:
            try:
                transcript = self.transcript_service.new(current_user)
            except LimitError:
                abort(403)

        if not transcript:
            abort(404)

        return transcript

    def update_address_country(self, field, address):
        country = field.data
        if address:
            address.country = country

    @login_required
    @warn_subscription_absent
    def transcript_student(self, transcript_id=None):

        page = 1
        goto_next = False
        button = ''
        if 'button' in request.form:
            button = request.form['button']

        transcript = self.get_transcript_for_editing(transcript_id)

        transcript_wizard = TranscriptWizard(self.db, transcript, current_user)

        current_form, page = transcript_wizard.get_form(page)

        if current_form.validate_on_submit():
            current_form.populate_obj(transcript)
            target = url_for('basic.transcript_student',
                             transcript_id=transcript.id)

            if button == "next" or button == "finish":
                flash("Transcript saved", "info")
                goto_next = button == "next"
                if button == "finish":
                    target = url_for('basic.index')

            elif button == 'add-student-address':
                country = current_form.student_country.data
                self.transcript_service.add_address(
                    transcript, "student_address", country)

            elif (button == 'change-student-country' and
                    current_form.student_country.validate(current_form)):
                self.update_address_country(
                    current_form.student_country, transcript.student_address)

            self.transcript_service.save(transcript)

            if goto_next:
                target = url_for('basic.transcript_school',
                                 transcript_id=transcript.id)

            return redirect(target)

        return render_template('basic/transcript_student.html',
                               transcript=transcript,
                               form=current_form)

    @login_required
    @warn_subscription_absent
    def transcript_school(self, transcript_id=None):
        page = 2
        goto_next = False
        button = ''
        if 'button' in request.form:
            button = request.form['button']

        transcript = self.get_transcript_for_editing(transcript_id)

        transcript_wizard = TranscriptWizard(self.db, transcript, current_user)

        current_form, page = transcript_wizard.get_form(page)

        # form validation and save transcript
        if current_form.validate_on_submit():
            current_form.populate_obj(transcript)

            target = url_for('basic.transcript_school',
                             transcript_id=transcript.id)

            if button == "next" or button == "finish":
                flash("Transcript saved", "info")
                if button == "finish":
                    target = url_for('basic.index')
                elif button == "next":
                    target = url_for('basic.transcript_academics',
                                     transcript_id=transcript.id)

            elif button == "back":
                target = url_for('basic.transcript_student',
                                 transcript_id=transcript.id)
            elif button == 'add-school-address':
                country = current_form.school_country.data
                self.transcript_service.add_address(
                    transcript, "school_address", country)

            elif (button == 'change-school-country' and
                  current_form.school_country.validate(current_form)):
                self.update_address_country(
                    current_form.school_country, transcript.school_address)

            self.transcript_service.save(transcript)

            return redirect(target)

        # Load up the form we're switching to
        return render_template('basic/transcript_school.html',
                               transcript=transcript,
                               form=current_form)

    @login_required
    @warn_subscription_absent
    def transcript_academics(self, transcript_id=None):
        page = 3
        goto_next = False
        button = ''
        if 'button' in request.form:
            button = request.form['button']

        transcript = self.get_transcript_for_editing(transcript_id)

        transcript_wizard = TranscriptWizard(self.db, transcript, current_user)

        current_form, page = transcript_wizard.get_form(page)

        # form validation and save transcript
        if current_form.validate_on_submit():
            current_form.populate_obj(transcript)
            target = url_for('basic.transcript_academics',
                             transcript_id=transcript.id)

            if button == "next" or button == "finish":
                flash("Transcript saved", "info")
                if button == "finish":
                    target = url_for('basic.index')
                elif button == "next":
                    target = url_for('basic.transcript_signature',
                                     transcript_id=transcript.id)

            elif button == "back":
                target = url_for('basic.transcript_school',
                                 transcript_id=transcript.id)

            elif button.startswith("add-course-year"):
                try:
                    # This needs to be after we validate and populate
                    # the form.

                    # last element of the value should be the year index
                    year_index = int(button.split('-')[-1])
                    year = transcript.years[year_index]
                    TranscriptService.add_course(year)
                    courses = year.courses
                    anchor = 'year-{}-course-{}'.format(
                        year_index, len(courses)-1)
                except (ValueError, IndexError):
                    # if we got a broken value, just ignore it
                    pass
            else:
                button_regex = r'delete-years-(?P<year>\d+)-courses-(?P<course>\d+)'
                delete_course_match = re.match(button_regex, button)
                if delete_course_match:
                    year_index = int(delete_course_match.group("year"))
                    course_index = int(delete_course_match.group("course"))
                    year = transcript.years[year_index]
                    course = year.courses.pop(course_index)
                    self.transcript_service.delete_course(course)

            self.transcript_service.save(transcript)
            return redirect(target)

        # Load up the form we're switching to
        return render_template('basic/transcript_academics.html',
                               transcript=transcript,
                               form=current_form)

    @login_required
    @warn_subscription_absent
    def transcript_signature(self, transcript_id=None):
        page = 4
        goto_next = False
        button = ''
        if 'button' in request.form:
            button = request.form['button']

        transcript = self.get_transcript_for_editing(transcript_id)

        transcript_wizard = TranscriptWizard(self.db, transcript, current_user)

        current_form, page = transcript_wizard.get_form(page)

        # form validation and save transcript
        if current_form.validate_on_submit():
            current_form.populate_obj(transcript)
            target = url_for('basic.transcript_signature',
                             transcript_id=transcript.id)

            # handle image upload
            sig_image_file = getattr(
                current_form, "signature_image_file", None)
            if sig_image_file is not None and sig_image_file.data is not None:
                file_storage = sig_image_file.data
                file_path = signatures.save(file_storage)
                transcript.signature_image = file_path

            # handle buttons
            if button == "save-print" or button == "finish":
                flash("Transcript saved", "info")
                if button == "finish":
                    target = url_for('basic.index')
                elif button == "save-print":
                    target = url_for('basic.transcript_settings',
                                     transcript_id=transcript.id)

            elif button == "back":
                target = url_for('basic.transcript_academics',
                                 transcript_id=transcript.id)

            elif button == 'remove-signature':
                file_path = signatures.path(transcript.signature_image)
                os.remove(file_path)
                transcript.signature_image = None

            self.transcript_service.save(transcript)
            return redirect(target)

        # Load up the form we're switching to
        return render_template('basic/transcript_signature.html',
                               transcript=transcript,
                               form=current_form)

    @login_required
    def transcript_signature_image(self, transcript_id):
        transcript = self.transcript_service.get_user_transcript(
            transcript_id, current_user.id)
        if not transcript or not transcript.signature_image:
            abort(404)
        file_path = signatures.path(transcript.signature_image)
        return send_file(file_path)

    @roles_required("subscriber")
    def print_transcript(self, transcript_id):
        transcript = self.transcript_service.get_user_transcript(
            transcript_id, current_user.id)
        transcript_grader = GradingService.get_transcript_grader(
            transcript.grading_scale, transcript.ap_grading_scale)

        if not transcript:
            abort(404)

        return render_pdf(transcript, transcript_grader)

    @login_required
    @warn_subscription_absent
    def delete_transcript(self, transcript_id):
        delete_form = DeleteTranscriptForm()
        transcript = self.transcript_service.get_user_transcript(
            transcript_id, current_user.id)
        if not transcript:
            abort(404)

        if delete_form.validate_on_submit() and transcript:
            transcript_name = transcript.student_name
            self.transcript_service.delete_transcript(transcript)

            flash("Transcript for {} has been deleted".format(
                transcript_name), 'info')

            return redirect(url_for('basic.index'))

        return render_template("basic/delete_transcript.html",
                               transcript=transcript,
                               delete_form=delete_form)

    @login_required
    @warn_subscription_absent
    def transcript_settings(self, transcript_id):
        transcript = self.transcript_service.get_user_transcript(
            transcript_id, current_user.id)
        if not transcript:
            abort(404)

        settings = transcript.settings or self.transcript_service.new_settings(
            transcript)

        button = ''
        if 'button' in request.form:
            button = request.form['button']

        target = None
        form = TranscriptSettingsForm(obj=settings)

        if form.validate_on_submit():
            form.populate_obj(settings)
            transcript.settings = settings
            self.transcript_service.save(transcript)

            if button == 'save':
                target = url_for("basic.index")

            elif button == 'print-save':
                target = url_for("basic.print", transcript_id=transcript.id)

        if target:
            return redirect(target)
        one_page_warning = LimitService.reached_course_limit(transcript)
        return render_template('basic/transcript_settings.html',
                               form=form, one_page_warning=one_page_warning)

    @login_required
    def delete_account(self):
        delete_form = DeleteAccountForm()

        if delete_form.validate_on_submit():

            if current_user.subscription:
                self.subscription_service.cancel(current_user.subscription)

            self.user_service.delete(current_user)
            flash("Your account has been deleted", 'info')
            logout_user()
            return redirect(url_for('public.index'))

        return render_template(
            "basic/delete_account.html",
            delete_form=delete_form
        )

    def register(self, basic):
        basic.add_url_rule('/', 'index', self.index, methods=["GET", "POST"])

        basic.add_url_rule('/settings', 'account_settings',
                           self.account_settings, methods=['GET', 'POST'])
        basic.add_url_rule('/settings/cancel',
                           'cancel_subscription', self.cancel_subscription,
                           methods=["GET", "POST"]
                           )
        basic.add_url_rule('/settings/delete_account', 'delete_account',
                           self.delete_account, methods=['GET', "POST"])

        basic.add_url_rule(
            '/transcript/',
            'transcript',
            self.transcript_student, methods=["GET", "POST"]
        )

        basic.add_url_rule(
            '/transcript/<int:transcript_id>/',
            'transcript', self.transcript_student, methods=["GET", "POST"]
        )
        basic.add_url_rule(
            '/transcript/<int:transcript_id>/student',
            'transcript_student', self.transcript_student, methods=["GET", "POST"]
        )
        basic.add_url_rule(
            '/transcript/<int:transcript_id>/school',
            'transcript_school', self.transcript_school, methods=["GET", "POST"]
        )
        basic.add_url_rule(
            '/transcript/<int:transcript_id>/academics',
            'transcript_academics', self.transcript_academics, methods=["GET", "POST"]
        )
        basic.add_url_rule(
            '/transcript/<int:transcript_id>/signature',
            'transcript_signature', self.transcript_signature, methods=["GET", "POST"]
        )

        basic.add_url_rule('/transcript/<int:transcript_id>/print',
                           'print', self.print_transcript)

        basic.add_url_rule(
            '/transcript/<int:transcript_id>/delete',
            'delete_transcript', self.delete_transcript,
            methods=["GET", "POST"]
        )

        basic.add_url_rule(
            '/transcript/<int:transcript_id>/settings',
            'transcript_settings', self.transcript_settings,
            methods=["GET", "POST"]
        )

        basic.add_url_rule('/transcript/<int:transcript_id>/signature_image',
                           'transcript_signature_image', self.transcript_signature_image)

        basic.add_url_rule(
            '/grading_scales/',
            'grading_scales',
            self.grading_scales
        )
        basic.add_url_rule('/grading_scale/',
                           'grading_scale', self.grading_scale,
                           methods=["GET", "POST"])
        basic.add_url_rule('/grading_scale/<int:grading_scale_id>',
                           'grading_scale', self.grading_scale,
                           methods=["GET", "POST"])

        basic.add_url_rule('/payment_information/',
                           'payment_information', self.payment_information,
                           methods=["GET", "POST"])

        basic.add_url_rule('/grading_scale/<int:grading_scale_id>/delete',
                           'delete_grading_scale', self.delete_grading_scale,
                           methods=['GET', "POST"])
