from flask import render_template, make_response
from xhtml2pdf import pisa
from transcript_hero.business.transcripts import TranscriptService
from transcript_hero_web.uploads import signatures


def _render_year_pdf(transcript, transcript_grader, course_filter):
    return _make_pdf_transcript('pdf/transcript.html',
                                transcript, transcript_grader,
                                course_filter=course_filter)


def _render_subject_pdf(transcript, categories,
                        transcript_grader, course_filter):
    return _make_pdf_transcript('pdf/transcript_by_subject.html',
                                transcript, transcript_grader,
                                course_filter=course_filter,
                                categories=categories)


def render_pdf(transcript, transcript_grader):
    signature_file_name = transcript.signature_image
    if signature_file_name:
        transcript.signature_image = signatures.path(signature_file_name)

    settings = transcript.settings
    renderer = _render_year_pdf
    kwargs = {
        'transcript': transcript,
        'transcript_grader': transcript_grader,
        'course_filter': lambda courses: list(filter(lambda c: c.title, courses)),
    }

    if settings is not None:
        transcript_grader.unweighted = settings.unweighted_gpa
        if settings.courses_by_subject:
            categories = TranscriptService.get_course_categories(
                transcript)
            kwargs['categories'] = categories
            renderer = _render_subject_pdf
        if settings.hide_unfinished_courses:
            kwargs['course_filter'] = lambda courses: list(
                filter(lambda c: c.title and transcript_grader.filter_unfinished_courses(c), courses))
    return renderer(**kwargs)


def _make_pdf_transcript(template, transcript, transcript_grader, **ctx_kwargs):
    html = render_template(
        template,
        transcript=transcript,
        grader=transcript_grader,
        **ctx_kwargs
    )
    context = pisa.CreatePDF(html, default_css="")
    context.dest.seek(0)

    response = make_response(context.dest.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = \
        'inline; filename={}_transcript.pdf'.format(
        transcript.student_name.replace(',', '').replace(' ', '_')
    )
    return response
