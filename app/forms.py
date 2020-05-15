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
    number = StringField(
        "How many pull requests you want to see?", default="all"
    )
    submit = SubmitField('Create dashboard')


class DashboardSettings(FlaskForm):
    sort_options = [("updated", "Time updated"), ("created", "Time created"), \
                    ("tests", "Number of tests passed"), ("diff", "Diff size")]
    sort = CheckboxField('Label', choices=sort_options, default="updated")
    submit = SubmitField('Submit')
