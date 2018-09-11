# -*- coding: utf-8 -*-
#
# forms_notes.py - Notes Flask Forms
#

from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import FileField
from wtforms import SelectField
from wtforms import StringField
from wtforms import SubmitField
from wtforms import TextAreaField
from wtforms import widgets
from wtforms.validators import DataRequired

from mycodo.databases.models import Notes
from mycodo.databases.models import NoteTags


#
# Notes
#

class NoteAdd(FlaskForm):
    list_inputs_sorted = generate_form_input_list(dict_inputs)

    name = StringField(lazy_gettext('Name'))
    tags = SelectField(
        choices=list_inputs_sorted,
        validators=[DataRequired()]
    )
    note = TextAreaField(lazy_gettext('Note'))
    files = FileField(lazy_gettext('Upload'))
    note_add = SubmitField(lazy_gettext('Save Note'))

class NoteOptions(FlaskForm):
    note_id = StringField(widget=widgets.HiddenInput())
    note_mod = SubmitField(lazy_gettext('Edit'))
    note_del = SubmitField(lazy_gettext('Delete'))

class NoteMod(FlaskForm):
    name = StringField(lazy_gettext('Name'))
    tag = StringField(lazy_gettext('Tags'))
    note = StringField(lazy_gettext('Note'))
    files = FileField(lazy_gettext('Upload'))
    note_save = SubmitField(lazy_gettext('Save'))


#
# Tags
#

class TagAdd(FlaskForm):
    tag_name = StringField(lazy_gettext('Name'))
    tag_add = SubmitField(lazy_gettext('Save'))

class TagOptions(FlaskForm):
    tag_id = StringField(widget=widgets.HiddenInput())
    tag_del = SubmitField(lazy_gettext('Delete'))
