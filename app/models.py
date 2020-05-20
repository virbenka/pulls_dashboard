import pymongo

from copy import copy
from datetime import datetime
from pymongo import MongoClient

from app import app

cluster = pymongo.MongoClient(app.config["MONGODB_URI"])
db = cluster[app.config["DB_NAME"]]

class People():
    def __init__(self, link):
        document_name = "people"
        if not document_name in db.list_collection_names():
            db.create_collection(document_name)
        self.collection = db[document_name]
        self.link = link
    def update_people(self, people):
        for person in people:
            person = people[person]
            self.collection.find_one_and_replace({"name": person["name"],
                                                   "repo_link": self.link},
                                                   person, upsert=True)
    def get_people(self):
        info = self.collection.find({"repo_link": self.link})
        res = {}
        for elem in info:
            elem.pop('_id')
            res.update({elem["name"]: elem})
        return res

class Labels():
    def __init__(self, link):
        document_name = "labels"
        if not document_name in db.list_collection_names():
            db.create_collection(document_name)
        self.collection = db[document_name]
        self.link = link
    def update_labels(self, labels):
        for label in labels:
            label = labels[label]
            self.collection.find_one_and_replace({"name": label["name"],
                                                  "repo_link": self.link},
                                                   label, upsert=True)
    def get_labels(self):
        info = self.collection.find({"repo_link": self.link})
        res = {}
        for elem in info:
            elem.pop('_id')
            res.update({elem["name"]: elem})
        return res

class Tests():
    def __init__(self, link):
        document_name = "tests"
        if not document_name in db.list_collection_names():
            db.create_collection(document_name)
        self.collection = db[document_name]
        self.link = link
    def update_tests(self, tests):
        for test in tests:
            test = tests[test]
            self.collection.find_one_and_replace({"name": test["name"],
                                                  "repo_link": self.link},
                                                   test, upsert=True)
    def get_tests(self):
        info = self.collection.find({"repo_link": self.link})
        res = {}
        for elem in info:
            elem.pop('_id')
            res.update({elem["name"]: elem})
        return res

class Pulls():
    def __init__(self, link):
        document_name = "pull_requests"
        if not document_name in db.list_collection_names():
            db.create_collection(document_name)
        self.collection = db[document_name]
        self.info = {"repo_link": link}
    def update_pull(self, pull):
        to_put = copy(self.info)
        to_put.update(pull)
        to_replace = copy(self.info)
        to_replace.update({"number": pull["number"]})
        self.collection.replace_one(to_replace, to_put, upsert=True)
    def update_pull_etag(self, pull):
        to_replace = copy(self.info)
        to_replace.update({"number": pull["number"]})
        self.collection.update_one(to_replace, {'$set': {"etag": pull["etag"]}})
    def get_pulls(self):
        return self.collection.find().sort('last_action.time', pymongo.DESCENDING)
    def get_current_pulls(self, pulls=[]):
        if pulls:
            self.delete_closed_pulls(pulls)
        res = {}
        for elem in self.collection.find(self.info):
            res[elem["number"]] = elem
        return res

    def delete_closed_pulls(self, pulls):
        current_pulls_numbers = set(pulls)
        avaliable_pulls_numbers = set([pull["number"] for pull in \
                                  self.collection.find({})])
        to_remove = copy(self.info)
        to_remove.update({'number' : {
            '$in' : list(avaliable_pulls_numbers - current_pulls_numbers)
        }})
        self.collection.delete_many(to_remove)



class Repos():
    def __init__(self, link=""):
        document_name = "repos"
        if not document_name in db.list_collection_names():
            db.create_collection(document_name)
        self.collection = db[document_name]
        if link:
            self.link = link
            self.info = {"repo_link": link}
    def repo_exists(self, owner, name):
        if self.collection.find_one({"name": name, "owner": owner}):
            return True
        else:
            return False
    def get_repos_names(self):
        return [(elem["owner"], elem["name"], elem["used"], elem["repo_link"]) for \
                elem in self.collection.find({})]
    def get_repo_info(self):
        res = self.collection.find_one(self.info)
        self.set_used()
        return res

    def update(self, numbers, etag):
        new_info = copy(self.info)
        new_info.update({"pulls_numbers":numbers, "etag": etag,
                         "name": self.link.split('/')[4],
                         "owner": self.link.split('/')[3]})
        self.collection.update_one(self.info, {'$set': new_info},
                                    upsert=True)
    def set_used(self):
        self.collection.update_one(self.info,
                                   {'$set': {"used": datetime.now()}}, upsert=True)
    def update_general_info(self, people, labels, tests, changes):
        People(self.link).update_people(people)
        Labels(self.link).update_labels(labels)
        Tests(self.link).update_tests(tests)
        self.collection.update_one(self.info, {'$set': {"changes_num": changes}})
    def get_general_info(self):
        people = People(self.link).get_people()
        labels = Labels(self.link).get_labels()
        tests = Tests(self.link).get_tests()
        max_changes = 0
        res = self.collection.find_one(self.info)
        if "changes_num" in res.keys():
            max_changes = res["changes_num"]
        return people, labels, tests, max_changes
    def delete_info(self):
        self.collection.delete_one(self.info)
        db["people"].delete_many(self.info)
        db["tests"].delete_many(self.info)
        db["pull_requests"].delete_many(self.info)
        db["labels"].delete_many(self.info)




  #  def get_time(self, link):
