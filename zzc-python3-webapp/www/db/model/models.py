# coding=utf-8

"""
业务模型类集合
"""

import time
import uuid

from db.orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    """
    用户
    """
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(50)')
    create_at = FloatField(default=time.time)


class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)


class App(Model):
    """
    应用模型
    """
    __table__ = 'app'

    id = IntegerField(primary_key=True)
    app_name = StringField(ddl='varchar(50)')
    app_key = StringField(ddl='varchar(50)')
    app_type = IntegerField()
    user_id = StringField(ddl='varchar(50)')
    app_icon = StringField(ddl='varchar(500)')
    create_time = FloatField(default=time.time)


class AppVersion(Model):
    """
    应用版本模型
    """
    __table__ = 'app_version'

    id = IntegerField(primary_key=True)
    app_id = IntegerField()
    version_code = StringField(ddl='varchar(45)')
    create_time = FloatField(default=time.time)


class PatchRecord(Model):
    """
    补丁包记录
    """
    __table__ = 'patch_record'

    id = IntegerField(primary_key=True)
    app_version_code = StringField(ddl='varchar(45)')
    app_id = IntegerField()
    patch_version_num = IntegerField()
    update_time = FloatField(default=time.time)
    patch_link = StringField(ddl='varchar(500)')
    describe = TextField()
    is_effective = BooleanField(default=True)
