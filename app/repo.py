import requests

class RepoDetails():
    def __init__ (self, owner, name):
        self.link = "github.com/"+owner+'/'+name
        self.dev_link = "https://api.github.com/"+owner+'/'+name
    def getLink(self):
        return self.link
    def validateRepo(self):
        responce = requests.get("https://" + self.link)
        return responce
