from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import RepoChoice
from app.repo import RepoDetails, PullRequest

@app.route('/', methods=['GET', 'POST'])
@app.route('/choice', methods=['GET', 'POST'])
def choice():
    form = RepoChoice()
    if form.validate_on_submit():
        return redirect(url_for('create_dashboard', owner=form.owner.data, name=form.name.data))
    return render_template('choice.html', title='Form', form=form)

@app.route('/dashboard/<owner>/<name>', methods=['GET', 'POST'])
def create_dashboard(owner, name):
    repo = RepoDetails(owner, name)
    if repo.validate_repo():
        repo_link = repo.get_link()
        pull_requests = repo.get_requests()
        people = repo.get_people()
        return render_template('dashboard.html', title='Dashboard',
                               text="lalalla", repo_link=repo_link, pull_requests=pull_requests,
                               people=people)
    else:
        flash("This repository doesn't exist")
        return redirect(url_for('choice'))
