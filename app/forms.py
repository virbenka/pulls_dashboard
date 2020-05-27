from app import app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectMultipleField, widgets, SelectField
from wtforms.validators import DataRequired

class CheckboxField(SelectField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()

class RepoChoice(FlaskForm):
    owner = StringField(
        "Repo's owner", validators=[DataRequired()]
    )
    name = StringField(
        "Repo's name", validators=[DataRequired()]
    )
    dropdown_list = [('all', 'all')]
    for elem in range(1, 150):
        dropdown_list.append((str(elem), str(elem)))
    number = SelectField('Number of pull requests to show', choices=dropdown_list,
                         default='all')
    submit = SubmitField('Create dashboard')
