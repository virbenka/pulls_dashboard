from datetime import datetime
from flask import render_template, flash, redirect, url_for, request

from app import app
from app.forms import RepoChoice, DashboardSettings
from app.models import Repos, Pulls
from app.repo import RepoInfoCollection, PullRequest

global settings
global repo
repo = ""
settings = app.config["SETTINGS"]

@app.route('/', methods=['GET', 'POST'])
@app.route('/choice', methods=['GET', 'POST'])
def choice():
    form = RepoChoice()
    if form.validate_on_submit():

        return redirect(url_for('create_dashboard', number=form.number.data, owner=form.owner.data, name=form.name.data))
    return render_template('choice.html', title='Form', form=form)

@app.route('/dashboard/<owner>/<name>', methods=['GET', 'POST'])
def create_dashboard(owner, name):
    number = request.args.get('number')
    link = "https://github.com/{}/{}".format(owner, name)
    if not Repos().repo_exists(owner, name):
        repo = RepoInfoCollection(owner, name, number)
        if not repo.validate_repo():
            flash("This repository doesn't exist")
            return redirect(url_for('choice'))
        else:
            print("created @route")
    print("exists @route")
    pulls = [elem for elem in Pulls(link).get_current_pulls().values()]
    people, labels, tests, max_changes = Repos(link).get_general_info()
    return render_template('dashboard.html', repo_link=link, owner=owner, name=name, title="Dashboard",
                            people=people, labels=labels, tests=tests, max_changes=max_changes,
                            pull_requests=pulls, settings=1)
@app.route('/dashboard/<owner>/<name>/settings', methods=['GET', 'POST'])
def dashboard_settings(owner, name):
    form = DashboardSettings()
    if form.validate_on_submit():
        settings["sort_type"]=form.sort.data
        return redirect(url_for('create_dashboard', owner=owner, name=name, number="all"))
    else:
        print("Validation Failed")
        print(form.errors)
    return render_template('settings.html', title='Settings', form=form)

@app.route('/task')
def task():
    x = datetime.now()
    for repo in Repos().get_repos_names():
        owner = repo[0]
        name = repo[1]
        used = repo[2]
        link = repo[3]
        if (datetime.now() - used).days > 15:
            Repos(link).delete_info()
        else:
            RepoInfoCollection(owner, name, 2)
    print(datetime.now()-x)
    return redirect(url_for('choice'))

