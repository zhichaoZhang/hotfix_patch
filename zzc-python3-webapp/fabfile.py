# fabfile.py
# coding=utf-8

import os, re
from datetime import datetime

# 导入Fabric API
from fabric.api import *

# 服务器登录用户名
env.user = 'zzc'

# sudo用户为root
env.sudo_user = 'root'

# 服务器地址
env.hosts = ['120.26.215.30']

# 服务器MySQL用户名和口令
db_user = 'zzc'
db_password = '123456'

_TAR_FILE = 'dist-hotfix.tar.gz'
_REMOTE_TMP_TAR = '/home/zzc/tmp/%s' % _TAR_FILE
_REMOTE_BASE_DIR = '/home/zzc/srv/hotfix'


def _current_path():
    return os.path.abspath('.')


def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')


def backup():
    dt = _now();
    f = 'backup-hotfix-%s.sql' % dt
    with cd('/tmp'):
        run(
            'mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick awesome > %s' % (
            db_user, db_password, f))
    run('tar -czvf %s.tar.gz %s' % (f, f))
    get('%s.tar.gz' % f, '%s/backup/' % _current_path())
    run('rm -f %s' % f)
    run('rm -f %s.tar.gz' % f)


def build():
    '''
    Build dist package.
    '''
    includes = ['static', 'templates', 'db',
                # 'transwarp', 
                'favicon.ico',
                '*.py']
    excludes = ['test', '.*', '*.pyc', '*.pyo']
    local('rm -f dist/%s' % _TAR_FILE)
    with lcd(os.path.join(_current_path(), 'www')):
        cmd = ['tar', '--dereference', '-czvf', '../dist/%s' % _TAR_FILE]
        cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
        cmd.extend(includes)
        local(' '.join(cmd))


def deploy():
    newdir = 'www-%s' % _now()
    run('rm -f %s' % _REMOTE_TMP_TAR)
    put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)
    with cd(_REMOTE_BASE_DIR):
        sudo('mkdir %s' % newdir)
    with cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):
        sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
    with cd(_REMOTE_BASE_DIR):
        sudo('rm -f www')
        sudo('ln -s %s www' % newdir)
        sudo('chown zzc:zzc www')
        sudo('chown -R zzc:zzc %s' % newdir)
    with settings(warn_only=True):
        sudo('supervisorctl stop hotfix')
        sudo('supervisorctl start hotfix')
        run('nginx -s reload')


RE_FILES = re.compile('\r?\n')


def rollback():
    '''
    rollback to previous version
    '''
    with cd(_REMOTE_BASE_DIR):
        r = run('ls -p -1')
        files = [s[:-1] for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]
        files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)
        r = run('ls -l www')
        ss = r.split(' -> ')
        if len(ss) != 2:
            print('ERROR: \'www\' is not a symbol link.')
            return
        current = ss[1]
        print('Found current symbol link points to: %s\n' % current)
        try:
            index = files.index(current)
        except ValueError, e:
            print('ERROR: symbol link is invalid.')
            return
        if len(files) == index + 1:
            print('ERROR: already the oldest version.')
        old = files[index + 1]
        print('==================================================')
        for f in files:
            if f == current:
                print('      Current ---> %s' % current)
            elif f == old:
                print('  Rollback to ---> %s' % old)
            else:
                print('                   %s' % f)
        print('==================================================')
        print('')
        yn = raw_input('continue? y/N ')
        if yn != 'y' and yn != 'Y':
            print('Rollback cancelled.')
            return
        print('Start rollback...')
        sudo('rm -f www')
        sudo('ln -s %s www' % old)
        sudo('chown www-data:www-data www')
        with settings(warn_only=True):
            sudo('supervisorctl stop awesome')
            sudo('supervisorctl start awesome')
            sudo('/etc/init.d/nginx reload')
        print('ROLLBACKED OK.')


def restore2local():
    '''
    Restore db to local
    '''
    backup_dir = os.path.join(_current_path(), 'backup')
    fs = os.listdir(backup_dir)
    files = [f for f in fs if f.startswith('backup-') and f.endswith('.sql.tar.gz')]
    files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)
    if len(files) == 0:
        print
        'No backup files found.'
        return
    print('Found %s backup files:' % len(files))
    print('==================================================')
    n = 0
    for f in files:
        print('%s: %s' % (n, f))
        n = n + 1
    print('==================================================')
    print('')
    try:
        num = int(raw_input('Restore file: '))
    except ValueError:
        print('Invalid file number.')
        return
    restore_file = files[num]
    yn = raw_input('Restore file %s: %s? y/N ' % (num, restore_file))
    if yn != 'y' and yn != 'Y':
        print('Restore cancelled.')
        return
    print('Start restore to local database...')
    p = raw_input('Input mysql root password: ')
    sqls = [
        'drop database if exists android_hot_fix;',
        'create database android_hot_fix;',
        'grant select, insert, update, delete on android_hot_fix.* to \'%s\'@\'localhost\' identified by \'%s\';' % (
        db_user, db_password)
    ]
    for sql in sqls:
        local(r'mysql -uroot -p%s -e "%s"' % (p, sql))
    with lcd(backup_dir):
        local('tar zxvf %s' % restore_file)
    local(r'mysql -uroot -p%s android_hot_fix < backup/%s' % (p, restore_file[:-7]))
    with lcd(backup_dir):
        local('rm -f %s' % restore_file[:-7])
