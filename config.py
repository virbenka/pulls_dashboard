import os

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ioioioioioioi"
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    MONGODB_URI = os.environ.get("MONGODB_URI")
    DB_NAME = os.environ.get("DB_NAME")
    REQUEST_RETRIES = 8
    REQUEST_TIMEOUT = 3
    ACCEPT_HEADER = "application/vnd.github.antiope-preview+json"
    SETTINGS = {"sort_type": "updated"}
