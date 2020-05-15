from app import app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectMultipleField, widgets, SelectField
from wtforms.validators import DataRequired

class RepoChoice(FlaskForm):
    owner = StringField(
        "Repo's owner", validators=[DataRequired()]
    )
    name = StringField(
        "Repo's name", validators=[DataRequired()]
    )
    submit = SubmitField('Create dashboard')

class MultiCheckboxField(SelectField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.RadioInput()

class DashboardSettings(FlaskForm):
    sort_options = [("updated", "Time updated"), ("created", "Time created"), \
                    ("tests", "Number of tests passed"), ("diff", "Diff size")]
    sort = MultiCheckboxField('Label', choices=sort_options, default="updated")
    submit = SubmitField('Submit')
