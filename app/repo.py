import copy
import functools
import math
import queue
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
    def __init__ (self, owner, name, number):
        self.session = create_requests_session()
        self.link = "https://github.com/{}/{}".format(owner, name)
        self.dev_link = "https://api.github.com/repos/{}/{}".format(owner, name)
        self.people = {}
        self.labels = {}
        self.tests = {}
        self.threads = queue.Queue()
        self.indexes = queue.Queue()
        self.max_changes = 0
        self.done = threading.Event()
        self.validated = False
        self.response = []
        page = 1
        try:
            number = int(number)
        except:
            number = 500
        self.number = number
        while number > 0:

            res = self.session.get(self.dev_link+'/pulls?state=open&page={}'.format(page), timeout=3)
            number -= 30
            page += 1
            print(res)
            if res and res.json():
                self.validated = True
                self.response += res.json()
            else:
                break
        self.start = datetime.now()
        self.set_requests()

    def validate_repo(self):
        return self.validated
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
        self.pull_requests = set()
        for i in range(min(len(response), self.number)):
            elem = response[i]
            pull_thread = threading.Thread(target=self.handle_pull_request, \
                                           args=[elem])
            pull_thread.daemon = True
            pull_thread.start()
            self.threads.put(pull_thread)
            self.indexes.put((i, 1))
        while not self.threads.empty():
            elem = self.threads.get()
            index,times = self.indexes.get()
            elem.join(timeout=5)
            print(self.threads.qsize(),"number: ", response[index]["number"], times)
            if (elem.is_alive()):
                if times < 3:
                    print("HAPPENED", self.response[index]["number"], times)
                    pull_thread = threading.Thread(target=self.handle_pull_request,
                                                args=[self.response[index]])
                    pull_thread.daemon = True
                    pull_thread.start()
                    self.threads.put(pull_thread)
                    self.indexes.put((index, times+1))
                else:
                    print("enough")
            print("new elem in:", datetime.now()-self.start)

        self.done.set()
    def update_changes_info(self, changes):
        self.max_changes = max(self.max_changes, changes["log"])
    def get_requests(self):
        self.done.wait()
        #self.sort("updated")
        return self.pull_requests
    def get_people(self):
        return self.people
    def get_labels(self):
        return self.labels
    def get_tests(self):
        return self.tests
    def get_max_changes(self):
        return self.max_changes
    def sort(self, option="updated"):
        if option == "created":
            self.pull_requests = sorted(self.pull_requests, key=lambda x: \
                                        x.get_created(), reverse=True)
        elif option == "updated":
            self.pull_requests = sorted(self.pull_requests, key=lambda x: \
                                        x.get_last_update(), reverse=True)
        elif option == "tests":
            self.pull_requests = sorted(self.pull_requests, key=lambda x: \
                                        x.get_statuses()["success"], reverse=True)
        else:
            self.pull_requests = sorted(self.pull_requests, key=lambda x: \
                                        x.get_changes()["total"], reverse=True)



class PullRequest():
    def __init__ (self, data, dev_link, session):
        self.session = session
        self.link = dev_link
        self.number = str(data['number'])
        try:
            info = self.session.get(dev_link+"/pulls/"+self.number).json()
        except:
            print(self.number, "pulls_info")

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
        self.set_changes(info)
        self.comments_number = 0
        self.set_last_comment()
        self.set_last_event()
        self.set_reviews_details()
        self.set_last_action()
        #self.last_action = self.set_last_action(dev_link)
    def __repr__(self):
        return "pull number {}".format(self.number)
    def __eq__(self, other):
        if isinstance(other, PullRequest):
            return self.number == other.number
        else:
            return False
    def __hash__(self):
        return hash(self.__repr__())

    def update_people(self, login, avatar, association):
        if association == "NONE":
            association = ""
        self.people.update({login: {
                "avatar": avatar,
                "association": association
            }
        })
    def set_changes(self, info):
        self.changes = { "commits": info["commits"],
                         "additions": info["additions"],
                         "deletions": info["deletions"],
                         "total": int(info["additions"])+int(info["deletions"]),
                        }
        if self.changes["total"] > 0:
            self.changes.update({"log": math.log(int(info["additions"])+int(info["deletions"]))})
        else:
            self.changes.update({"log": 0})
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
        try:
            tests = self.session.get(self.link+"/status/"+self.last_commit).json()
        except:
            print(self.number, "tests_results_status")
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
        try:
            comments = self.session.get(
                                        self.link+"/issues/"+self.number+'/comments'
                                        ).json()
        except:
            print(self.number, "comments")
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
        try:
            reviews = self.session.get(
                                    self.link+"/pulls/"+self.number+"/reviews"
                                    ).json()
        except:
            print(self.number, "reviews_details")
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
                    try:
                        text = self.session.get(self.link+"/pulls/"+self.number+
                                                    "/comments")
                    except:
                        print(self.number, "reviews_pulls_commens")
                    text = text.json()[-1]["body"]
                    self.last_comment = {"person": review["user"]["login"],
                                        "time": review["submitted_at"],
                                        "text": text,
                                         "event": "commented"}

    def set_last_event(self):
        self.last_event = {}
        try:
            events = self.session.get(
                self.link+"/issues/"+self.number+"/events"
            ).json()
        except:
            print(self.number, "last_event_issiues")
        if events:
            self.last_event = {"event": events[-1]["event"],
                            "person": events[-1]["actor"]["login"],
                            "time": events[-1]["created_at"]
                            }
            if events[-1]["actor"]["login"] not in self.people.keys():
                self.update_people(events[-1]["actor"]["login"],
                                   events[-1]["actor"]["avatar_url"], "")

    def set_last_action(self):
        try:
            commit_time = self.session.get(
                self.link+"/commits/"+self.last_commit
            ).json()["commit"]["committer"]["date"]
        except:
            print(self.number, "last_action_commit_time")
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

