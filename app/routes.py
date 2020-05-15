from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import RepoChoice, MultiCheckboxField, DashboardSettings
from app.repo import RepoDetails, PullRequest

global settings
settings = app.config["SETTINGS"]

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
    if not repo.validate_repo():
        flash("This repository doesn't exist")
        return redirect(url_for('choice'))
    else:
        print("AKLALALA")
        print(settings)
        repo.sort(settings["sort_type"])
        repo_link = repo.get_link()
        pull_requests = repo.get_requests()
        people = repo.get_people()
        labels = repo.get_labels()
        tests = repo.get_tests()
        max_changes = repo.get_max_changes()
        return render_template('dashboard.html', owner=owner, name = name, title='Dashboard',
                                repo_link=repo_link, pull_requests=pull_requests,
                                people=people, labels=labels, tests=tests, max_changes=max_changes, settings=1)

@app.route('/dashboard/<owner>/<name>/settings', methods=['GET', 'POST'])
def dashboard_settings(owner, name):
    form = DashboardSettings()
    if form.validate_on_submit():
        print(form.sort.data)
        settings["sort_type"]=form.sort.data
        print(app.config["SETTINGS"])
        return redirect(url_for('create_dashboard', owner=owner, name=name))
    else:
        print("Validation Failed")
        print(form.errors)
    return render_template('settings.html', title='Settings', form=form)
