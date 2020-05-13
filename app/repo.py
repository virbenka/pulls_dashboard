import copy
import functools
import math
import requests
import threading

from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from time import time

from collections import Counter
from app import app

def create_requests_session():
    session = requests.Session()
    session.headers.update({'Accept': app.config['ACCEPT_HEADER'],
                            'Authorization': 'token {}'.format(app.config['GITHUB_TOKEN'])}
                           )
    retry = Retry(
        total=app.config["REQUEST_RETRIES"],
        read=app.config["REQUEST_RETRIES"],
        connect=app.config["REQUEST_RETRIES"],
        backoff_factor=0.1
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.request = functools.partial(session.request, timeout=app.config['REQUEST_TIMEOUT'])
    return session



class RepoDetails():
    def __init__ (self, owner, name):
        self.session = create_requests_session()
        self.link = "https://github.com/{}/{}".format(owner, name)
        self.dev_link = "https://api.github.com/repos/{}/{}".format(owner, name)
        self.response = self.session.get(self.dev_link+'/pulls?state=open&per_page=10')
        if self.response:
            self.response = self.response.json()
            self.people = {}
            self.labels = {}
            self.tests = {}
            self.threads = []
            self.max_changes = 0
            self.set_requests()
    def validate_repo(self):
        return self.response
    def get_link(self):
        return self.link
    def handle_pull_request(self, elem):
        pull = PullRequest(elem, self.dev_link, self.session)
        self.pull_requests.add(pull)
        self.people.update(pull.get_people_info())
        self.labels.update(pull.get_labels_info())
        self.tests.update(pull.get_tests_info())
        self.update_changes_info(pull.get_changes())
    def set_requests(self):
        response = self.response
        print(len(response))
        self.pull_requests = set()
        i = 1
        for elem in response:
            pull_thread = threading.Thread(target=self.handle_pull_request, \
                                           args=[elem])
            pull_thread.daemon = True
            pull_thread.start()
            self.threads.append(pull_thread)
            i+=1
        for elem in self.threads:
            elem.join(timeout=3)
            if (elem.is_alive()):
                print("HAPPENED")
                pull_thread = threading.Thread(target=self.handle_pull_request,
                                               args=[self.response[self.threads.index(elem)]])
                pull_thread.daemon = True
                pull_thread.start()
                pull_thread.join(timeout=3)
                print(pull_thread.is_alive())
        self.sort_by_time()
    def update_changes_info(self, changes):
        self.max_changes = max(self.max_changes, changes["log"])
    def get_requests(self):
        return self.pull_requests
    def get_people(self):
        return self.people
    def get_labels(self):
        return self.labels
    def get_tests(self):
        return self.tests
    def get_max_changes(self):
        return self.max_changes
    def sort_by_time(self):
        self.pull_requests = sorted(self.pull_requests, key=lambda x: \
                                    x.get_last_update(), reverse=True)

class PullRequest():
    def __init__ (self, data, dev_link, session):
        self.session = session
        self.link = dev_link
        self.number = str(data['number'])
        info = self.session.get(dev_link+"/pulls/"+self.number).json()
        self.login = info['user']['login']
        self.people = {}
        self.update_people(self.login, info["user"]["avatar_url"], \
                           info["author_association"])
        self.title = info['title']
        self.last_updated = info['updated_at']
        self.created = info['created_at']
        self.description = info['body']
        self.last_commit = info['statuses_url'].split('/')[-1]
        self.set_tests_results()
        self.set_labels(info["labels"])
        self.changes = { "commits": info["commits"],
                         "additions": info["additions"],
                         "deletions": info["deletions"],
                         "total": int(info["additions"])+int(info["deletions"]),
                         "log": math.log(int(info["additions"])+int(info["deletions"]))
                        }
        self.comments_number = 0
        self.set_last_comment()
        self.set_last_event()
        self.set_reviews_details()
        self.set_last_action()
        #self.last_action = self.set_last_action(dev_link)
    def update_people(self, login, avatar, association):
        if association == "NONE":
            association = ""
        self.people.update({login: {
                "avatar": avatar,
                "association": association
            }
        })
    def set_labels(self, info):
        self.labels = []
        self.labels_info = {}
        for label in info:
            self.labels.append(label["name"])
            self.labels_info.update({label["name"] : {
                       "color": label["color"],
                        "description": label["description"],
                        "url": label["url"]
                }
            })
    def set_tests_results(self):
        self.statuses = Counter()
        tests = self.session.get(self.link+"/status/"+self.last_commit).json()
        self.tests = {}
        self.tests_info = {}
        for test in tests["statuses"]:
            test_status = {"context": test["context"],
                           "url": test["target_url"],
                           "description": test["description"],
                           "time": datetime.strptime(test["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
                           }
            self.statuses.update([test["state"]])
            if test["state"] in self.tests.keys():
                self.tests[test["state"]].append(test_status)
            else:
                self.tests[test["state"]] = [test_status]
            self.tests_info.update({test["context"]: {
                    "url": test["target_url"],
                    "description": test["description"],
                }
            })
    def set_last_comment(self):
        comments = self.session.get(
                                    self.link+"/issues/"+self.number+'/comments'
                                    ).json()
        self.last_comment = {}
        for comment in comments:
            self.comments_number += 1
            self.update_people(comment["user"]["login"],
                               comment["user"]["avatar_url"],
                               comment["author_association"])
        if comments:
            self.last_comment = {"person": comments[-1]["user"]["login"],
                                "time": comments[-1]["updated_at"],
                                "event": "commented",
                                "text": comments[-1]["body"]}
    def set_reviews_details(self):
        reviews = self.session.get(
                                   self.link+"/pulls/"+self.number+"/reviews"
                                   ).json()
        self.last_review = {}
        self.approved = set()
        self.reviewed_by = set()
        for review in reviews:
            self.comments_number += 1
            if review["state"] == "APPROVED":
                self.approved.add(review["user"]["login"])
            self.update_people(review["user"]["login"],
                               review["user"]["avatar_url"],
                               review["author_association"])
            if review["user"]["login"] != self.login:
                self.reviewed_by.add(review["user"]["login"])
                self.last_review = {"status": reviews[-1]["state"],
                            "person": reviews[-1]["user"]["login"],
                            "time": reviews[-1]["submitted_at"],
                            "event": "reviewed"
                            }
        if reviews:
            if reviews[-1]["user"]["login"] == self.login and self.last_comment \
                and self.time(reviews[-1]["submitted_at"]) > \
                self.time(self.last_comment["time"]):
                    print("TUT")
                    text = self.session.get(self.link+"/pulls/"+self.number+
                                                "/comments")
                    print(text)
                    text = text.json()[-1]["body"]
                    self.last_comment = {"person": review["user"]["login"],
                                        "time": review["submitted_at"],
                                        "text": text,
                                         "event": "commented"}

    def set_last_event(self):
        self.last_event = {}
        events = self.session.get(
            self.link+"/issues/"+self.number+"/events"
        ).json()
        if events:
            self.last_event = {"event": events[-1]["event"],
                            "person": events[-1]["actor"]["login"],
                            "time": events[-1]["created_at"]
                            }
            if events[-1]["actor"]["login"] not in self.people.keys():
                self.update_people(events[-1]["actor"]["login"],
                                   events[-1]["actor"]["avatar_url"], "")

    def set_last_action(self):
        commit_time = self.session.get(
            self.link+"/commits/"+self.last_commit
        ).json()["commit"]["committer"]["date"]
        self.last_action = {}
        self.last_action["diff"] = float("inf")
        for elem in [self.last_comment, self.last_event, self.last_review]:
            if elem:
                if elem["time"] == self.last_updated:
                    self.last_action = elem
                    return
                else:
                    if self.last_action["diff"] > abs(self.time(elem["time"])- \
                                                      self.time(self.last_updated)):
                        self.last_action = copy.copy(elem)
                        self.last_action["diff"] = abs(self.time(elem["time"])- \
                                                       self.time(self.last_updated))
        if self.last_action["diff"] == float("inf") and \
                commit_time == self.last_updated:
            self.last_action = "commited"
        else:
            if self.last_action["diff"] > \
                    abs(self.time(commit_time)-self.time(self.last_updated)):
                self.last_action = "commited"
            elif self.last_action["diff"] == float("inf"):
                self.last_action = {}

    @staticmethod
    def time(time):
        return int(''.join(x for x in time if x.isdigit()))

    def get_approved_by(self):
        return self.approved
    def get_avatar(self):
        return self.avatar
    def get_changes(self):
        return self.changes
    def get_comments_number(self):
        return self.comments_number
    def get_created(self):
        return datetime.strptime(self.created, "%Y-%m-%dT%H:%M:%SZ")
    def get_description(self):
        return self.description
    def get_labels(self):
        return self.labels
    def get_labels_info(self):
        return self.labels_info
    def get_last_action(self):
        return self.last_action
    def get_last_comment(self):
        return self.last_comment
    def get_last_review(self):
        return self.last_review
    def get_last_update(self):
        return datetime.strptime(self.last_updated, "%Y-%m-%dT%H:%M:%SZ")
    def get_login(self):
        return self.login
    def get_number(self):
        return str(self.number)
    def get_people_info(self):
        return self.people
    def get_reviewed_by(self):
        return self.reviewed_by
    def get_statuses(self):
        return self.statuses
    def get_tests(self):
        return self.tests
    def get_tests_info(self):
        return self.tests_info
    def get_title(self):
        return "[{}] {}".format(self.number, self.title)
