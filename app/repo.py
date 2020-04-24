import requests

class RepoDetails():
    def __init__ (self, owner, name):
        self.link = "github.com/"+owner+'/'+name
        self.dev_link = "https://api.github.com/repos/"+owner+'/'+name
    def getLink(self):
        return self.link
    def validateRepo(self):
        responce = requests.get("https://" + self.link)
        return responce
    def getRequests(self):
        responce = requests.get(self.dev_link+'/pulls?state=open').json()
        pull_requests = []
        for elem in responce:
            pull_requests.append(PullRequest(elem))
        return pull_requests

class PullRequest():
    def __init__ (self, data):
        self.login = data['user']['login']
        self.avatar = data['user']['avatar_url']
        self.title = data['title']
    def getLogin(self):
        return self.login
    def getAvatar(self):
        return self.avatar
    def getTitle(self):
        return self.title
    def getStatus(self):
        return self.status
    def getLastUpdateTime(self):
        return self.last_updated
