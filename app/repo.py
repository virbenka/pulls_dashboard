import functools
import requests
import threading

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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
        self.response = self.session.get(self.dev_link+'/pulls?state=open')
        if self.response:
            self.response = self.response.json()
            self.people = {}
            self.threads = []
            self.set_requests()
    def validate_repo(self):
        return self.response
    def get_link(self):
        return self.link
    def handle_pull_request(self, elem):
        pull = PullRequest(elem, self.dev_link, self.session)
        self.pull_requests.add(pull)
        self.people.update(pull.get_people())
    def set_requests(self):
        response = self.response
        print(len(response))
        self.pull_requests = set()
        i = 1
        for elem in response:
            pull_thread = threading.Thread(target=self.handle_pull_request, args=[elem])
            pull_thread.daemon = True
            pull_thread.start()
            self.threads.append(pull_thread)
            i+=1
    def get_requests(self):
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

        return self.pull_requests

class PullRequest():
    def __init__ (self, data, dev_link, session):
        self.session = session
        self.number = data['number']
        info = self.session.get(dev_link+"/pulls/"+str(self.number)).json()
        self.login = info['user']['login']
        self.people = {}
        self.update_people(self.login, info["user"]["avatar_url"], info["author_association"])
        self.title = info['title']
        self.last_updated = info['updated_at']
        self.created = info['created_at']
        self.description = info['body']
        self.last_commit = info['statuses_url'].split('/')[-1]
        self.statuses = self.set_tests_results(dev_link)
        self.labels = [label["name"] for label in info["labels"]]
        self.changes = { "commits": info["commits"],
                         "additions": info["additions"],
                         "deletions": info["deletions"]
                        }
        #self.last_action = self.set_last_action(dev_link)
    def update_people(self, login, avatar, association):
        self.people.update({login: {
                "avatar": avatar,
                "association": association
            }
        })
    def get_login(self):
        return self.login
    def get_avatar(self):
        return self.avatar
    def get_title(self):
        return self.title
    def get_statuses(self):
        return self.statuses
    def get_last_update(self):
        return self.last_updated
    def get_created(self):
        return self.created
    def get_description(self):
        return self.description
    def get_labels(self):
        return self.labels
    def get_changes(self):
        return self.changes
    def get_people(self):
        return self.people
    def set_tests_results(self, dev_link):
        results = Counter()
        info = self.session.get(dev_link+"/status/"+self.last_commit)
        for test in info.json()["statuses"]:
            results.update([test["state"]])
        return results
    def set_last_action(self, dev_link):
            info = self.session.get(dev_link+"/issues/"+self.number+'/comments')
