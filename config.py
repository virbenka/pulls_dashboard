import os

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "ioioioioioioi"
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    REQUEST_RETRIES = 4
    REQUEST_TIMEOUT = 1.5
    ACCEPT_HEADER = "application/vnd.github.antiope-preview+json"
    SETTINGS = {"sort_type": "updated"}
