import copy
import functools
import math
import queue
import requests
import threading

from datetime import datetime, timedelta

from app.models import People, Labels, Pulls, Repos, Tests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from time import time

from collections import Counter
from app import app

EVENTS_NAMES = {"labeled" : "added a lable",
                "head_ref_force_pushed" : "force-pushed the branch",
                "ready_for_review" : "marked as ready for review",
                "commented" : "added a comment",
                "review_request_removed" : "removed review request",
                "convert_to_draft" : "marked as draft",
                "APPROVED" : "approved",
                "CHANGES_REQUESTED" : "requested changes",
                "COMMENTED" : "added a review-comment",
                }

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
    def __init__ (self, owner, name):
        #print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
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
            self.excepted = set()
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
        if info and "etag" in info.keys():
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
            #print(page)
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
        for number in self.pulls_numbers[:20]:
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
            #print(self.threads.qsize(),"number: ", number, times)
            if (elem.is_alive()):
                if times < 4:
                    #print("HAPPENED", number, times)
                    pull_thread = threading.Thread(target=self.handle_pull_request,
                                                args=[number])
                    pull_thread.daemon = True
                    pull_thread.start()
                    self.threads.put(pull_thread)
                    self.threads_numbers.put((number, times+1))
                #else:
                    #print("enough")
                #print("new elem in:", datetime.now()-self.start)
            elif number in self.excepted:
                print(number, "IN EXCEPTED")
                self.excepted.discard(number)
                if times < 4:
                    pull_thread = threading.Thread(target=self.handle_pull_request,
                                                args=[number])
                    pull_thread.daemon = True
                    pull_thread.start()
                    self.threads.put(pull_thread)
                    self.threads_numbers.put((number, times+1))

        self.done.set()
        #print(len(self.people), "len PEOPLE")
        #print("len tests", len(self.tests))
        #print("len labels", len(self.labels))
        self.repo_db.set_updated()
        self.repo_db.update_general_info(self.people, self.labels, self.tests, self.max_changes)

    def handle_pull_request(self, number):
        info = {}
        if number in self.all_pulls_info.keys():
            info = self.all_pulls_info[number]
        #try:
        pull = PullRequest(number, self.link, self.dev_link, self.session, {},
                            self.prev_people, self.prev_labels, self.prev_tests)
        self.pull_requests.add(pull)
        if pull.get_if_pull_changed():
            #print("it did")
            info = pull.get_all_info()
            if pull.get_if_only_etag_changed():
                #print("etag onlu")
                self.pulls_db.update_pull_etag(info)
            else:
                #print("it all")
                self.pulls_db.update_pull(info)
        people = pull.get_people_info()
        to_remove = set()
        for person in people:
            if person in self.people.keys():
                if people[person]["association"] == "":
                    to_remove.add(person)
        for elem in to_remove:
            people.pop(elem)
        self.people.update(people)
        self.labels.update(pull.get_labels_info())
        self.tests.update(pull.get_tests_info())
        self.update_changes_info(pull.get_changes_num())
        #except Exception as e:

         #   print("EXCEPTION", number)
         #   print(e)
            #self.excepted.add(number)

    def update_changes_info(self, changes):
        self.max_changes = max(self.max_changes, changes)
    def get_requests(self):
        self.done.wait()
        info = self.session.get(self.dev_link+"/pulls/"+self.number,
                                headers={"If-None-Match": self.current_info["etag"]}
                               )
        print("left", info.headers.get("X-RateLimit-Remaining"))
        return self.pull_requests


class PullRequest():
    def __init__ (self, number, link, dev_link, session, saved_info, people, labels, tests):
        self.session = session
        self.link = dev_link
        self.repo_link = link
        self.current_info = copy.copy(saved_info)
        self.number = str(number)
        if not self.current_info:
            self.set_minimal_data()
        info = self.session.get(dev_link+"/pulls/"+self.number,
                                headers={"If-None-Match": self.current_info["etag"]}
                               )
        print(info.headers.get("X-RateLimit-Remaining"))
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
                                      "created": self.time(info['created_at']),
                                      "mergeable": info["mergeable"],
                                      })
            self.set_assignees(info["assignees"])
            self.set_requested_reviewers(info["requested_reviewers"])
            self.set_labels(info["labels"])
            self.set_changes(info)
            updated_at=self.time(info["updated_at"])
            if self.current_info["last_updated"] != updated_at:
                self.current_info["last_updated"] = updated_at
                self.set_last_event()
                if self.current_info["standard_comments"] != info["comments"]:
                    self.current_info["standard_comments"] = info["comments"]
                    self.set_last_comment()
                if self.current_info["last_commit"]["number"] != info['statuses_url'].split('/')[-1]:
                    self.current_info["last_commit"]["number"] = info['statuses_url'].split('/')[-1]
                    self.set_last_commit()
                self.current_info["review_comments"]=info["review_comments"]
            self.set_reviews_details()
        self.set_last_action()
        self.set_tests_results()
        elem = self.current_info["last_action"]
        self.changes_num = self.current_info["changes"]["log"]
        self.changed = not (self.current_info == saved_info)
        saved_info["etag"] = self.current_info["etag"]
        #print(self.current_info == saved_info)
        self.only_etag_changed = (self.current_info == saved_info)
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
                                  "last_updated": datetime(1,1,1),
                                  "standard_comments": 0,
                                  "review_comments": 0,
                                  "last_commit": {
                                      "number": -1
                                  },
                                  "last_comment": {
                                      "time": datetime(1,1,1),
                                      "etag": ""
                                  },
                                  "last_review": {
                                      "time": datetime(1,1,1),
                                      "etag": ""
                                  },
                                  "last_event": {
                                      "time": datetime(1,1,1),
                                  },
                                  "events": {
                                      "etag": "",
                                      "pages": "1",
                                  },
                                  "tests": {
                                      "pages_etags": {"1" : ""},
                                      "all": {}
                                  },
                                 })
    def update_people(self, url, login, avatar, association=""):
        if association == "NONE":
            association = ""
        info = {"url": url,
                "name": login,
                "avatar": avatar,
                "association": association,
                "repo_link": self.repo_link
               }
        if login in self.people.keys():
            if not association:
                return
        if login in self.prev_people.keys():
            if self.prev_people[login] == info:
                return
            if not association:
                return
        self.people.update({login: info})
    def set_assignees(self, info):
        assignees = []
        for elem in info:
            assignees.append(elem["login"])
        self.current_info["assignees"] = [elem for elem in assignees]

    def set_requested_reviewers(self, info):
        requested_reviewers = []
        for elem in info:
            requested_reviewers.append(elem["login"])
        self.current_info["requested_reviewers"] = [elem for elem in requested_reviewers]
    def set_requested_reviewers(self, info):
        for elem in info:
            self.current_info["requested_reviewerd"].append(elem["login"])
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
        statuses = {}
        page = 1
        count = 0
        tests = {}
        total = -1
        while True:
            if str(page) in self.current_info["tests"]["pages_etags"].keys():
                etag = self.current_info["tests"]["pages_etags"][str(page)]
            else:
                etag = ""
            tests_ = self.session.get(self.link+"/status/"+self.current_info["last_commit"]["number"] \
                                        + "?page={}".format(page),
                                    headers={"If-None-Match": etag})
            if tests_.status_code == 304:
                continue
            self.current_info["tests"]["pages_etags"][str(page)] = tests_.headers.get('etag')
            tests_ = tests_.json() #tests
            if "total_count" in tests_.keys():
                total = tests_["total_count"]
            if "statuses" in tests_.keys():
                for test in tests_["statuses"]:
                    count += 1
                    test_status = {"context": test["context"],
                                "url": test["target_url"],
                                "description": test["description"],
                                "time": self.time(test["updated_at"])
                                }
                    if test["state"] in tests.keys():
                        tests[test["state"]].append(test_status)
                    else:
                        tests[test["state"]] = [test_status]
                    test_info = {"name": test["context"],
                                "repo_link": self.repo_link}
                    if test["context"] in self.prev_tests.keys():
                        if self.prev_tests[test["context"]] == test_info:
                            continue
                    self.tests_info.update({test["context"]: test_info})
                self.current_info["tests"]["all"].update(tests)
            else:
                break
            page += 1
            if total != -1 and total == count:
                break
        for elem in self.current_info["tests"]["all"]:
            statuses[elem] = len(self.current_info["tests"]["all"][elem])
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
        if comments:
            commented_at = self.time(comments[-1]["updated_at"])
            if self.current_info["last_comment"]["time"] < commented_at:
                last_comment = {
                    "person": comments[-1]["user"]["login"],
                    "time": commented_at,
                    "event": "commented",
                    "text": comments[-1]["body"],
                    "url": comments[-1]["url"],
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
            if "state" in review.keys() and review["state"] == "APPROVED":
                approved.add(review["user"]["login"])
            self.update_people(review["user"]["url"],
                               review["user"]["login"],
                               review["user"]["avatar_url"],
                               review["author_association"])
            reviewed_at = self.time(review["submitted_at"])
            if review["user"]["login"] == self.current_info["author"] and \
                    reviewed_at > self.current_info["last_comment"]["time"]:
                self.current_info["last_comment"].update({
                    "person": review["user"]["login"],
                    "time": reviewed_at,
                    "event": "commented",
                    "url": review["_links"]["html"]["href"]
                }) # not touching etag because we'll compare it with last comment
            elif review["user"]["login"] != self.current_info["author"]:
                review_state=review["state"]
                if review["state"] in EVENTS_NAMES:
                    review_state=EVENTS_NAMES[review_state]
                reviewed.add(review["user"]["login"])
                last_review = {"status": review["state"],
                               "person": review["user"]["login"],
                               "time": reviewed_at,
                               "event": review_state,
                               "url": review["_links"]["html"]["href"]
                              }
        self.current_info["last_review"].update(last_review)
        self.current_info["approved"] = [elem for elem in approved]
        self.current_info["reviewed"] = [elem for elem in reviewed]
        # get comment body
        # text = self.session.get(self.link+"/pulls/"+self.number+
        #                           "/comments")
        # text = text.json()[-1]["body"]

    def set_last_event(self):
        last_event = {}
        page = self.current_info["events"]["pages"]
        event_ = {}
        while True:
            etag = self.current_info["events"]["etag"]
            events = self.session.get(
                self.link+"/issues/"+self.number+"/events?page={}".format(page),
                headers={
                    "If-None-Match": self.current_info["events"]["etag"]
                })
            if events.status_code == 304:
                return
            self.current_info["events"]["etag"] = events.headers.get('etag')
            self.current_info["events"]["pages"] = page
            if events.json():
                event_ = events.json()[-1]
            if len(events.json()) < 30: # because limit per page is set to 30
                break
            else:
                page += 1
        events = events.json()
        if event_:
            happend_at = self.time(event_["created_at"])
            if self.current_info["last_event"]["time"] < happend_at:
                event = event_["event"]
                if event in EVENTS_NAMES.keys():
                    event = EVENTS_NAMES[event]
                last_event = {"event": event,
                            "person": event_["actor"]["login"],
                            "time": happend_at,
                            "url": event_["url"]
                            }
                if events[-1]["actor"]["login"] not in self.people.keys():
                    self.update_people(event_["actor"]["url"],
                                    event_["actor"]["login"],
                                    event_["actor"]["avatar_url"])
                self.current_info["last_event"].update(last_event)

    def set_last_commit(self):
        commit = self.session.get(
            self.link+"/commits/"+self.current_info["last_commit"]["number"])
        commit = commit.json()
        try:
            person = commit["author"]

            self.current_info["last_commit"]["person"] = person["login"]
            self.update_people(person["html_url"], person["login"],
                               person["avatar_url"])
        except:
            self.current_info["last_commit"]["person"] = self.current_info["author"]
        self.current_info["last_commit"]["time"] = self.time(commit["commit"]["committer"]["date"])
        self.current_info["last_commit"]["url"] = commit["html_url"]
        self.current_info["last_commit"]["event"] = "made a commit"

    def set_last_action(self):
        last_action = {}
        diff = timedelta(1000,0,0)
        open_pr = {"time": self.current_info["created"],
                   "event": "opened pull request",
                   "person": self.current_info["author"]}
        for elem in [self.current_info["last_comment"],
                     self.current_info["last_event"],
                     self.current_info["last_review"],
                     self.current_info["last_commit"],
                     open_pr]:

            try:
                a = elem["time"]
            except:
                print(elem, self.current_info["number"])
                return
            if elem["time"] == self.current_info["last_updated"]:
                self.current_info["last_action"] = elem
                return
            else:
                if diff > self.substr(elem["time"], self.current_info["last_updated"]):
                    last_action = copy.copy(elem)
                    diff = self.substr(elem["time"], self.current_info["last_updated"])

        self.current_info["last_action"] = last_action

    @staticmethod
    def time(time):
        return datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
    @staticmethod
    def substr(time1, time2):
        if time1 >= time2:
            return time1-time2
        return time2-time1

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

