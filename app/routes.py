from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import RepoChoice

@app.route('/', methods=['GET', 'POST'])
@app.route('/choice', methods=['GET', 'POST'])
def choice():
    form = RepoChoice()
    if form.validate_on_submit():
        flash('Repository {} requested'.format(form.repo_name.data))
        return redirect(url_for('choice'))
    return render_template('choice.html', title='Form', form=form)

