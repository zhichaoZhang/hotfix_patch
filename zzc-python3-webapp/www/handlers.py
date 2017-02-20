#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" url handlers """

import time, logging, re, json, hashlib, base64, asyncio, uuid
import string, random
from aiohttp import web
from coreweb import get, post
from db.model.models import Blog, User, next_id, App, AppVersion, PatchRecord
from apis import APIValueError, APIResourceNotFoundError, APIError

COOKIE_NAME = 'hotfix'
_COOKIE_KEY = 'configs.session.secret'

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

__signed_user = None


@get('/')
async def index(request):
    # users = await User.findAll()
    # return {
    #     '__template__': 'test.html',
    #     'users': users
    # }

    # summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    # blogs = [
    #     Blog(id='1', name='Test Blog', summary=summary, created_at=time.time() - 120),
    #     Blog(id='2', name='Something New', summary=summary, created_at=time.time() - 3600),
    #     Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time() - 7200)
    # ]
    # return {
    #     '__template__': 'blogs.html',
    #     'blogs': blogs
    # }
    global __signed_user
    return {
        '__template__': 'index.html',
        '__user__': __signed_user
    }


@get('/register')
async def register():
    return {
        '__template__': 'register.html'
    }


@get('/signin')
async def signin():
    return {
        '__template__': 'signin.html'
    }


@get('/myapps')
async def myapps():
    return {
        '__template__': 'myapps.html',
        '__user__': __signed_user
        # '__apps__':__apps
    }


@get('/create_app')
async def create_app():
    return {
        '__template__': 'create_app.html',
        # '__apps__':__apps
        'action': '/api/apps'
    }


@get('/api/users')
async def api_get_users():
    """
    查询所有用户
    """
    users = await User.findAll(orderBy='create_at')
    for u in users:
        u.passwd = '********'
    return dict(users=users)


@post('/api/login')
async def api_login(*, email, passwd):
    """
    登陆接口
    """
    if not email:
        raise APIValueError('emila', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid passwd')
    users = await User.findAll('email=?', [email])
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]
    # 检查密码
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd', 'Invalid passwd')
    # 验证通过，为响应添加cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    global __signed_user
    __signed_user = user
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@get('/signout')
async def signout(request):
    referer = request.handers.get('Referer')
    r = web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME, '-deleted-', max_age=0, httponly=True)
    global __signed_user
    __signed_user = None
    logging.info('user signed out.')
    return r


@post('/api/users')
async def api_register_user(*, email, name, passwd):
    """
    注册接口
    """
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use')
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email,
                passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
                image='')
    await user.save()
    global __signed_user
    __signed_user = user
    # make session cookie
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


@post('/api/apps')
async def api_create_app(request, *, app_name):
    """
    新建app
    """
    if not app_name or not app_name.strip():
        raise APIValueError('app_name', 'app name cannot be empty')

    app_key = create_app_key()
    app_type = 1
    app_icon = ''
    app = App(app_name=app_name.strip(), app_key=app_key, app_type=app_type, user_id=request.__user__.id,
              app_icon=app_icon)
    await app.save()
    return app


@get('/api/del_app')
async def api_delete_app(request, *, id):
    """
    删除一个应用
    """
    if not id or not id.strip():
        raise APIValueError('app id', 'app id cannot be empty')
    row = App.remove('id=?', id)
    if row == 1:
        r = web.Response()
        return r


@get('/api/update_app')
async def api_update_app(request, *, app_name):
    """
    更新应用信息
    """
    if not app_name or not app_name.strip():
        raise APIValueError('app_name', 'app_name cannot be empty')
    row = App.update('app_name', app_name)
    if row == 1:
        r = web.Response()
        return


@get('/api/apps')
async def api_apps(request):
    """
    查询用户下所有app
    """
    apps = await App.findAll('user_id=?', request.__user__.id)
    if len(apps) == 0:
        return dict(apps=())
    return dict(apps=apps)


@post('/api/app_versions')
async def api_create_app_version(request, *, app_id, version_code):
    """
    新建app版本
    """
    if not version_code or not version_code.strip():
        raise APIValueError('version_code', 'version code cannot be empty')
    if not app_id or not app_id.strip():
        raise APIValueError('app_id', 'app id cannot be empty')

    app_version = AppVersion(app_id=app_id, version_code=version_code)
    await app_version.save()
    return app_version


@get('/api/app_versions')
async def api_app_versions(*, app_id):
    """
    查询某个app的所有版本
    """
    app_versions = await AppVersion.findAll('app_id=?', app_id)
    return dict(app_versions=app_versions)


@get('/api/del_version')
async def api_delete_version(request, *, id):
    """
    删除一个app版本
    """


@post('/api/patch_records')
async def api_create_patch_record(request, *, app_id, app_version_code, patch_link, describe, patch_size):
    """
    新建补丁记录
    """
    if not app_id or not app_id.strip():
        raise APIValueError('app_id', 'app id cannot be empty')
    if not app_version_code or not app_version_code.strip():
        raise APIValueError('app_version_code', 'app version code cannot be empty')
    if not patch_link or not patch_link.strip():
        raise APIValueError('patch_link', 'patch link cannot be empty')
    if not patch_size or not patch_size.strip():
        raise APIValueError('patch_size', 'patchsize cannot be empty')
    if not describe:
        describe = ''

    patch_version_num = 1
    patch_records = patch_record(app_id, app_version_code)
    if len(patch_records) > 0:
        patch_version_num = patch_records[0].patch_version_num

    is_effective = 1
    patch_record = PatchRecord(app_id=app_id, app_version_code=app_version_code, patch_link=patch_link,
                               patch_size=patch_size, describe=describe, patch_version_num=patch_version_num,
                               is_effective=is_effective)
    await patch_record.save()
    return patch_record


@get('/api/patch_records')
async def patch_records(request, *, app_id, app_version_code):
    """
    查询某app的某版本下的补丁记录
    """
    if not app_id or not app_id.strip():
        raise APIValueError('app_id', 'app id cannot be empty')
    if not app_version_code or not app_version_code.strip():
        raise APIValueError('app_version_code', 'app version code cannot be empty')
    patch_records = await PatchRecord.findAll('app_id=? and app_version_code = ?', app_id, app_version_code)
    return patch_records


@get('/api/hjsh/clientlog')
async def log_record(request, *, log):
    """
    接收客户端日志
    """
    print(log)
    r = web.Response()
    return r


def create_app_key():
    randomlength = 16
    str = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789'
    str = ''.join(random.sample(chars, 16))
    return str


def user2cookie(user, max_age):
    '''
    通过用户信息生成cookie字符串
    cookie格式为：用户id-过期时间-sha1
    sha1由用户id、密码、过期时间、固定字符串_COOKIE_KEY 组成
    :param user: 用户信息
    :param max_age: 有效期
    :return: cookie字符串
    '''

    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


async def cookie2user(cookie_str):
    """
    解析cookie并查询用户信息
    """
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            # cookie格式不合法
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            # cookie过期
            return None
        user = await User.find(uid)
        if user is None:
            # 用户不存在
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            # sha1不匹配
            logging.info('Invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None
