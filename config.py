import os

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ioioioioioioi"
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    MONGODB_URI = os.environ.get("MONGODB_URI")
    REQUEST_RETRIES = 8
    REQUEST_TIMEOUT = 2
    ACCEPT_HEADER = "application/vnd.github.antiope-preview+json"
    SETTINGS = {"sort_type": "updated"}
