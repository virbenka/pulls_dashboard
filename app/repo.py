import copy
import functools
import math
import queue
import requests
import threading

from datetime import datetime

from app.models import People, Labels, Pulls, Repos, Tests

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



class RepoInfoCollection():
    def __init__ (self, owner, name, number):
        self.session = create_requests_session()
        self.link = "https://github.com/{}/{}".format(owner, name)
        self.dev_link = "https://api.github.com/repos/{}/{}".format(owner, name)
        self.repo_db = Repos(self.link)
        self.pulls_db = Pulls(self.link)
        self.exists = False
        self.update_repo_info()
        if self.exists:
            self.all_pulls_info = self.pulls_db.get_current_pulls(self.pulls_numbers)
            self.prev_people, self.prev_labels, self.prev_tests, _ = self.repo_db.get_general_info()
            self.labels = {}
            self.people = {}
            self.tests = {}
            self.threads = queue.Queue()
            self.threads_numbers = queue.Queue()
            self.max_changes = 0
            self.done = threading.Event()
            self.validated = False
            self.response = []
            self.start = datetime.now()
            self.set_requests()

    def update_repo_info(self):
        info = self.repo_db.get_repo_info()
        etag = ""
        if info:
            etag = info["etag"]
        response = self.session.get(self.dev_link+'/pulls?state=open',
                                    headers={'If-None-Match': etag},
                                    timeout=4)
        if response.status_code == 304:
            self.exists = True
            self.pulls_numbers = info["pulls_numbers"]
            return
        self.pulls_numbers = []
        page = 1
        if not response:
            return
        else:
            etag = response.headers.get('etag')

        while True:
            print(page)
            self.exists = True
            pull_per_page = [elem["number"] for elem in response.json()]
            if not pull_per_page:
                self.repo_db.update(self.pulls_numbers, etag)
                return
            self.pulls_numbers += pull_per_page
            page += 1
            response = self.session.get(
                self.dev_link+'/pulls?state=open&page={}'.format(page),
                timeout=4)

    def validate_repo(self):
        return self.exists
    def get_link(self):
        return self.link
    def set_requests(self):
        self.pull_requests = set()
        for number in self.pulls_numbers:
            pull_thread = threading.Thread(target=self.handle_pull_request, \
                                           args=[number])
            pull_thread.daemon = True
            pull_thread.start()
            self.threads.put(pull_thread)
            self.threads_numbers.put((number, 1))
        while not self.threads.empty():
            elem = self.threads.get()
            number, times = self.threads_numbers.get()
            elem.join(timeout=5)
            print(self.threads.qsize(),"number: ", number, times)
            if (elem.is_alive()):
                if times < 3:
                    print("HAPPENED", number, times)
                    pull_thread = threading.Thread(target=self.handle_pull_request,
                                                args=[number])
                    pull_thread.daemon = True
                    pull_thread.start()
                    self.threads.put(pull_thread)
                    self.threads_numbers.put((number, times+1))
                else:
                    print("enough")
            print("new elem in:", datetime.now()-self.start)
        self.done.set()
        print(len(self.people), "len PEOPLE")
        print("len tests", len(self.tests))
        print("len labels", len(self.labels))
        self.repo_db.update_general_info(self.people, self.labels, self.tests, self.max_changes)
    def handle_pull_request(self, number):
        if number in self.all_pulls_info.keys():
            pull = PullRequest(number, self.link, self.dev_link,
                               self.session, self.all_pulls_info[number],
                               self.prev_people, self.prev_labels, self.prev_tests)
        else:
            pull = PullRequest(number, self.link, self.dev_link, self.session, {},
                               self.prev_people, self.prev_labels, self.prev_tests)
        self.pull_requests.add(pull)
        if pull.get_if_pull_changed():
            info = pull.get_all_info()
            if pull.get_if_only_etag_changed:
                self.pulls_db.update_pull_etag(info)
            else:
                self.pulls_db.update_pull(info)
        self.people.update(pull.get_people_info())
        self.labels.update(pull.get_labels_info())
        self.tests.update(pull.get_tests_info())
        self.update_changes_info(pull.get_changes_num())
    def update_changes_info(self, changes):
        self.max_changes = max(self.max_changes, changes)
    def get_requests(self):
        self.done.wait()
        #self.repo_db.update_people(self.people, self.link)
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
    def __init__ (self, number, link, dev_link, session, saved_info, people, labels, tests):
        self.session = session
        self.link = dev_link
        self.repo_link = link
        self.number = str(number)
        self.current_info = copy.copy(saved_info)

        if not self.current_info:
            self.set_minimal_data()
        info = self.session.get(dev_link+"/pulls/"+self.number,
                                headers={"If-None-Match": self.current_info["etag"]}
                               )
        self.prev_people = people
        self.prev_labels = labels
        self.prev_tests = tests
        self.labels_info = {}
        self.people = {}
        self.tests_info = {}
        if info.status_code != 304:
            self.current_info["etag"] = info.headers.get('etag')
            info = info.json()
            self.update_people(info["user"]["url"], info["user"]["login"], info["user"]["avatar_url"], \
                               info["author_association"])
            self.current_info.update({"number": info["number"],
                                      "title": info["title"],
                                      "description": info["body"],
                                      "author": info['user']['login'], # login
                                      "created": info['created_at'],
                                      "last_commit": info['statuses_url'].split('/')[-1],
                                      })

            self.set_labels(info["labels"]),
            self.set_changes(info)
            if self.current_info["last_updated"] != info["updated_at"]:
                self.current_info["last_updated"] = info["updated_at"]
                if self.current_info["standard_comments"] != info["comments"]:
                    self.current_info["standard_comments"] = info["comments"]
                    self.set_last_comment()
                self.set_last_event()
                self.set_last_action()
                self.review_comments=info["review_comments"]
            self.set_reviews_details()
        self.set_tests_results()
        self.changes_num = self.current_info["changes"]["log"]
        self.changed = not (self.current_info == saved_info)
        saved_info["etag"] = self.current_info["etag"]
        self.only_etag_changed = not (self.current_info == saved_info)
    def __repr__(self):
        return "pull number {}".format(self.number)
    def __eq__(self, other):
        if isinstance(other, PullRequest):
            return self.number == other.number
        else:
            return False
    def __hash__(self):
        return hash(self.__repr__())

    def set_minimal_data(self):
        self.current_info.update({"etag": "",
                                  "last_updated": "0",
                                  "standard_comments": 0,
                                  "review_comments": 0,
                                  "last_comment": {
                                      "time": "0",
                                      "etag": ""
                                  },
                                  "last_review": {
                                      "time": "0",
                                      "etag": ""
                                  },
                                  "last_event": {
                                      "time": "0",
                                      "etag": ""
                                  },
                                  "tests": {
                                      "etag": ""
                                  }

                                 })
    def update_people(self, url, login, avatar, association):
        if association == "NONE":
            association = ""
        info = {"url": url,
                "name": login,
                "avatar": avatar,
                "association": association,
                "repo_link": self.repo_link
               }
        if login in self.prev_people.keys():
            if self.prev_people[login] == info:
                return
            if not association:
                return
        self.people.update({login: info})

    def set_changes(self, info):
        changes = { "commits": info["commits"],
                         "additions": info["additions"],
                         "deletions": info["deletions"],
                         "total": int(info["additions"])+int(info["deletions"]),
                        }
        if changes["total"] > 0:
            changes.update({"log": math.log(int(info["additions"])+int(info["deletions"]))})
        else:
            changes.update({"log": 0})
        self.current_info["changes"] = changes
    def set_labels(self, info):
        labels = []
        for label in info:
            labels.append(label["name"])
            label_info = {"name": label["name"],
                    "url": label["url"],
                    "color": label["color"],
                    "description": label["description"],
                    "url": label["url"],
                    "repo_link": self.repo_link}
            if label["name"] in self.prev_labels.keys() and \
                    self.prev_labels[label["name"]] == label_info:
                continue
            self.labels_info.update({label["name"]: label_info})
        self.current_info["labels"] = labels
    def set_tests_results(self):
        statuses = Counter()
        tests = self.session.get(self.link+"/status/"+self.current_info["last_commit"],
                                 headers={"If-None-Match": self.current_info["tests"]["etag"]})
        if tests.status_code == 304:
            return
        self.current_info["tests"]["etag"] = tests.headers.get('etag')
        tests_ = tests.json() #tests
        tests = {}
        for test in tests_["statuses"]:
            test_status = {"context": test["context"],
                           "url": test["target_url"],
                           "description": test["description"],
                           "time": datetime.strptime(test["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
                           }
            statuses.update([test["state"]])
            if test["state"] in tests.keys():
                tests[test["state"]].append(test_status)
            else:
                tests[test["state"]] = [test_status]
            test_info = {"name": test["context"],
                         "repo_link": self.repo_link}
            if test["context"] in self.prev_tests.keys():
                if  self.prev_tests[test["context"]] == test_info:
                    continue
            self.tests_info.update({test["context"]: test_info})
        self.current_info["tests"].update(tests)
        self.current_info["statuses"] = statuses
    def set_last_comment(self):
        comments = self.session.get(
                                    self.link+"/issues/"+self.number+'/comments',
                                    headers={
                                        "If-None-Match": self.current_info["last_comment"]["etag"]
                                    })
        if comments.status_code == 304:
            return
        self.current_info["last_comment"]["etag"] = comments.headers.get('etag')
        comments = comments.json()
        last_comment = {}
        for comment in comments:
            self.update_people(comment["user"]["url"],
                               comment["user"]["login"],
                               comment["user"]["avatar_url"],
                               comment["author_association"])
        if "comments" in self.current_info.keys():
            if self.current_info["time"] < comments[-1]["updated_at"]:
                self.current_info["comments"] = {
                    "person": comments[-1]["user"]["login"],
                    "time": comments[-1]["updated_at"],
                    "event": "commented",
                    "text": comments[-1]["body"],
                    "url": comments[-1]["url"]
                }
        self.current_info["last_comment"].update(last_comment)
    def set_reviews_details(self):
        reviews = self.session.get(
                                self.link+"/pulls/"+self.number+"/reviews",
                                headers={
                                    "If-None-Match": self.current_info["last_review"]["etag"]
                                })
        if reviews.status_code == 304:
            return
        self.current_info["last_review"]["etag"] = reviews.headers.get('etag')
        reviews = reviews.json()
        last_review = {}
        approved = set()
        reviewed = set()
        for review in reviews:
            if review["state"] == "APPROVED":
                approved.add(review["user"]["login"])
            self.update_people(review["user"]["url"],
                               review["user"]["login"],
                               review["user"]["avatar_url"],
                               review["author_association"])
            if review["user"]["login"] != self.current_info["author"]:
                reviewed.add(review["user"]["login"])
                last_review = {"status": reviews[-1]["state"],
                                    "person": reviews[-1]["user"]["login"],
                                    "time": reviews[-1]["submitted_at"],
                                    "event": "reviewed",
                                    "url": reviews[-1]["_links"]["html"]["href"]
                                   }
                self.current_info["last_review"].update(last_review)
        if reviews:
            if reviews[-1]["user"]["login"] == self.current_info["author"]  \
                and self.time(reviews[-1]["submitted_at"]) > \
                self.time(self.current_info["last_comment"]["time"]):
                    text = self.session.get(self.link+"/pulls/"+self.number+
                                                "/comments")
                    text = text.json()[-1]["body"]
                    self.current_info["last_comment"] = {
                                            "person": review["user"]["login"],
                                            "time": review["submitted_at"],
                                            "text": text,
                                            "event": "commented",
                                            "url": review["_links"]["html"]["href"]}
        self.current_info["appoved"] = [elem for elem in approved]
        self.current_info["reviewed"] = [elem for elem in reviewed]

    def set_last_event(self):
        last_event = {}
        events = self.session.get(
            self.link+"/issues/"+self.number+"/events",
            headers={
                "If-None-Match": self.current_info["last_review"]["etag"]
            })
        if events.status_code == 304:
            return
        self.current_info["last_event"]["etag"] = events.headers.get('etag')
        events = events.json()
        if events and self.current_info["last_event"]["time"] < events[-1]["created_at"]:
            last_event = {"event": events[-1]["event"],
                          "person": events[-1]["actor"]["login"],
                          "time": events[-1]["created_at"],
                          "url": events[-1]["url"]
                          }
            if events[-1]["actor"]["login"] not in self.people.keys():
                self.update_people(events[-1]["actor"]["url"],
                                   events[-1]["actor"]["login"],
                                   events[-1]["actor"]["avatar_url"], "")
            self.current_info["last_event"].update(last_event)

    def set_last_action(self):
        commit_time = self.session.get(
            self.link+"/commits/"+self.current_info["last_commit"]
        ).json()["commit"]["committer"]["date"]
        last_action = {}
        last_action["diff"] = float("inf")
        for elem in [self.current_info["last_comment"], self.current_info["last_event"], self.current_info["last_review"]]:
            if elem:
                if elem["time"] == self.current_info["last_updated"]:
                    last_action = elem
                    return
                else:
                    if last_action["diff"] > abs(self.time(elem["time"])- \
                                                 self.time(self.current_info["last_updated"])):
                        last_action = copy.copy(elem)
                        last_action["diff"] = abs(self.time(elem["time"])- \
                                                  self.time(self.current_info["last_updated"]))
        if last_action["diff"] == float("inf") and \
            commit_time == self.current_info["last_updated"]:
                last_action = "commited"
        else:
            if last_action["diff"] > \
                    abs(self.time(commit_time)-self.time(self.current_info["last_updated"])):
                last_action = "commited"
            elif last_action["diff"] == float("inf"):
                last_action = {}
        self.current_info["last_action"] = last_action

    @staticmethod
    def time(time):
        return int(''.join(x for x in time if x.isdigit()))

    def get_all_info(self):
        return self.current_info
    def get_if_pull_changed(self):
        return self.changed
    def get_if_only_etag_changed(self):
        return self.only_etag_changed
    def get_changes_num(self):
        return self.changes_num
    def get_last_update(self):
        return datetime.strptime(self.last_updated, "%Y-%m-%dT%H:%M:%SZ")
    def get_labels_info(self):
        return self.labels_info
    def get_people_info(self):
        return self.people
    def get_tests_info(self):
        return self.tests_info

