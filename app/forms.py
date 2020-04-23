from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

class RepoChoice(FlaskForm):
    owner = StringField(
        "Repo's owner", validators=[DataRequired()]
    )
    name = StringField(
        "Repo's name", validators=[DataRequired()]
    )
    submit = SubmitField('Create dashboard')
