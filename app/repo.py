import requests
from collections import Counter

class RepoDetails():
    def __init__ (self, owner, name):
        self.link = "https://github.com/{}/{}".format(owner, name)
        self.dev_link = "https://api.github.com/repos/{}/{}".format(owner, name)
    def getLink(self):
        return self.link
    def validateRepo(self):
        response = requests.get(self.link)
        return response
    def getRequests(self):
        response = requests.get(self.dev_link+'/pulls?state=open').json()
        pull_requests = []
        for elem in response:
            pull_requests.append(PullRequest(elem, self.dev_link))
        return pull_requests

class PullRequest():
    def __init__ (self, data, dev_link):
        self.number = data['number']
        self.login = data['user']['login']
        self.avatar = data['user']['avatar_url']
        self.title = data['title']
        self.last_updated = data['updated_at']
        self.created = data['created_at']
        self.description = data['body']
        self.last_commit = self.set_last_commit(dev_link)
        self.statuses = self.set_tests_results(dev_link)
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
    def set_last_commit(self, dev_link):
        return(requests.get(dev_link+"/pulls/"+str(self.number)+"/commits").json()[-1]["sha"])
    def set_tests_results(self, dev_link):
        results = Counter()
        info = requests.get(dev_link+"/commits/"+self.last_commit+"/status").json()
        for test in info["statuses"]:
            results.update([test["state"]])
        return results
