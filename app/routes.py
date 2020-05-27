from copy import copy
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request

from app import app
from app.forms import RepoChoice
from app.models import Repos, Pulls
from app.repo import RepoInfoCollection, PullRequest

global settings
global repo
repo = ""
settings = app.config["SETTINGS"]

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
@app.route('/choice', methods=['GET', 'POST'])
def choice():
    form = RepoChoice()
    if form.validate_on_submit():
        return redirect(url_for('create_dashboard', owner=form.owner.data, \
                                name=form.name.data, number=form.number.data))
    return render_template('choice.html', title='Form', form=form)

@app.route('/dashboard/<owner>/<name>', methods=['GET', 'POST'])
def create_dashboard(owner, name):
    number = request.args.get('number')
    owner, name = owner.lower(), name.lower()
    link = "https://github.com/{}/{}".format(owner, name)
    if not Repos().repo_exists(owner, name):
        repo = RepoInfoCollection(owner, name)
        if not repo.validate_repo():
            flash("This repository doesn't exist or API rate limit exceeded. It'll be back in one hour or even sooner.")
            return redirect(url_for('choice'))
        else:
            print("created @route")
    pulls = Pulls(link).get_pulls(number)
    people, labels, tests = Repos(link).get_general_info()
    updated = Repos(link).get_updated()
    Repos(link).set_used()
    changes = [elem["changes"]["log"] for elem in pulls]
    max_changes = 0
    if changes:
        max_changes = max(changes)
    return render_template('dashboard.html', repo_link=link, owner=owner, name=name, title="Dashboard",
                            people=people, labels=labels, tests=tests, max_changes=max_changes,
                            pull_requests=pulls, number=number, updated=updated)

@app.route('/task')
def task():
    x = datetime.now()
    print(x)
    print("ISFAOIOSAFSAIFOSAIOAIOI")
    for repo in Repos().get_repos_names():
        print("here we go", repo)
        owner = repo[0]
        name = repo[1]
        used = repo[2]
        link = repo[3]
        print("got info")
        print("OWNER:", owner)
        if (datetime.utcnow() - used).days > 18:
            Repos(link).delete_info()
        else:
            print("GOING TO UPDATE ALL REPOS")
            RepoInfoCollection(owner, name)
    print(datetime.now()-x)
    return redirect(url_for('choice'))

@app.route('/dashboard/<owner>/<name>/refresh_data')
def refresh(owner, name, number=""):
    number = request.args.get('number')
    print(number)
    print("HERE")
    if not number:
        number = "all"
    owner, name = owner.lower(), name.lower()
    RepoInfoCollection(owner, name)
    return redirect(url_for('create_dashboard', owner=owner, name=name, number=number))
