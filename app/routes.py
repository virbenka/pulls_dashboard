from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import RepoChoice
from app.repo import RepoDetails

@app.route('/', methods=['GET', 'POST'])
@app.route('/choice', methods=['GET', 'POST'])
def choice():
    form = RepoChoice()
    if form.validate_on_submit():
        flash('Repository {} requested'.format(form.repo_name.data))

        return redirect(url_for('create_dashboard', repo=form.repo_name.data))
    return render_template('choice.html', title='Form', form=form)

@app.route('/dashboard/<repo>', methods=['GET', 'POST'])
def create_dashboard(repo):
    repo = RepoDetails(repo)
    repo_name = repo.getName()
    return render_template('dashboard.html', title='Dashboard', text="lalalla", repo_name=repo_name)
