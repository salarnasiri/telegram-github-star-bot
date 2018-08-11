from peewee import *
from playhouse.sqliteq import SqliteQueueDatabase

db = SqliteQueueDatabase('db/voting.db')


class User(Model):
    first_name = CharField(null=False)
    uid = IntegerField(null=False, unique=True)

    class Meta:
        database = db


class Github(Model):
    owner = ForeignKeyField(User, backref='githubs')
    link = CharField(null=True)
    repo_owner = CharField(null=True)
    repo_name = CharField(null=True)

    class Meta:
        database = db


class Secret(Model):
    owner = ForeignKeyField(User, backref='secrets')
    site_type = IntegerField()
    secret_type = IntegerField()
    user_name = CharField(null=True)
    secret = CharField(null=True, unique=True)
    permitted = BooleanField(default=True)

    class Meta:
        database = db


class Submit(Model):
    secret = ForeignKeyField(Secret, backref='submit')
    repo_owner = CharField(null=True)
    repo_name = CharField(null=True)
    is_submitted = BooleanField(default=True)

    class Meta:
        database = db