import requests
import threading

from collections import Counter

class RepoDetails():
    def __init__ (self, owner, name):
        self.link = "https://github.com/{}/{}".format(owner, name)
        self.dev_link = "https://api.github.com/repos/{}/{}".format(owner, name)
        self.response = requests.get(self.dev_link+'/pulls?state=open',
            headers={
                    'Accept':'application/vnd.github.antiope-preview+json',
                    'Authorization': 'token {}'.format('b32a5cb79af5119bd7f74dde2bb7208e603abf04')
            }
        )
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
        pull = PullRequest(elem, self.dev_link)
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
    def __init__ (self, data, dev_link):
        self.number = data['number']
        info = requests.get(dev_link+"/pulls/"+str(self.number),
            headers={
                    'Accept':'application/vnd.github.antiope-preview+json',
                    'Authorization': 'token {}'.format('b32a5cb79af5119bd7f74dde2bb7208e603abf04')
            }
        ).json()
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
        try:
            info = requests.get(dev_link+"/status/"+self.last_commit,
            headers={'Accept':'application/vnd.github.antiope-preview+json',
                    'Authorization': 'token {}'.format('b32a5cb79af5119bd7f74dde2bb7208e603abf04')
                    },
            timeout=2
                            )
        except:
            print("retrying")
            try:
                info = requests.get(dev_link+"/status/"+self.last_commit,
                headers={'Accept':'application/vnd.github.antiope-preview+json',
                        'Authorization': 'token {}'.format('b32a5cb79af5119bd7f74dde2bb7208e603abf04')
                        },
                timeout=2
                                )
            except:
                return Counter('failed_to_test')

        for test in info.json()["statuses"]:
            results.update([test["state"]])
        return results
    def set_last_action(self, dev_link):
            try:
                info = requests.get(dev_link+"/issues/"+self.number+'/comments',
                headers={'Accept':'application/vnd.github.antiope-preview+json',
                        'Authorization': 'token {}'.format('b32a5cb79af5119bd7f74dde2bb7208e603abf04')
                        },
                timeout=2
                                )
            except:
                print("retrying asking comments")
                try:
                    info = requests.get(dev_link+"/issues/"+self.number+'/comments',
                    headers={'Accept':'application/vnd.github.antiope-preview+json',
                            'Authorization': 'token {}'.format('b32a5cb79af5119bd7f74dde2bb7208e603abf04')
                            },
                    timeout=2
                                    )
                except:
                        return "couldn't load comments"
