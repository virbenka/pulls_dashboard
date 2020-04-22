from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

class RepoChoice(FlaskForm):
    repo_name = StringField(
        'Enter the name of your repo', validators=[DataRequired()]
    )
    submit = SubmitField('Create dashboard')
