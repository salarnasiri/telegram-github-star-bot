class State(object):
    START = 0
    GITHUB_LINK = 1
    STACK_LINK = 2
    SECRET = 3
    GITHUB_SECRET = 4
    STACK_SECRET = 5
    GITHUB_HISTORY = 6
    GITHUB_PASS = 7
    GITHUB_TOKEN = 8
    GITHUB_PERMISSION = 9
    GITHUB_PERMITTED = 11
    GITHUB_NOT_PERMITTED = 12


class Site(object):
    GITHUB = 0
    STACK_OVER_FLOW = 1


class SecretType(object):
    TOKEN = 0
    PASS = 1


class SitePrefix(object):
    GITHUB = "https://github.com"


class Const(object):
    REQUEST_DELAY = 1
    MAX_TRY = 5
