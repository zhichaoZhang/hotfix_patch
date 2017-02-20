# coding=utf-8

# db.py
import threading
import time
import uuid
import functools
import logging

"""
DML data manipulation language 数据操作语言 对数据的增删改查 insert delete update select
DDL database definition language   数据定义语言 对数据库的增删改查 create drop alter truncate
DCL database control language 数据库控制语言 设置或更改数据库用户或角色权限的语句 commit savepoint rollback set transaction

设计数据库模块的原因：
    1、更简单的操作数据库。
    封装一次数据操作流程（连接->执行sql->取得游标->处理异常->断开连接）,使得用户仅关心业务sql的执行上面

    2、数据安全
    影虎请求以多线程处理时，为了避免多线程下的数据共享引起的数据混乱，需要将数据库连接以ThreadLocal对象传入

数据模块设计：
    1、设计原则
    根据上层调用者设计简单易用的api接口
    2、调用接口
        1、初始化数据库连接信息
            create_engine封装了如下功能:
            1、为数据库连接准备需要的信息
            2、创建连接
        2、执行sql
            支持一个数据库连接里执行多个sql语句
                 支持连接的自动获取和释放
        3、支持事务
            支持事务的嵌套
"""
# 全局的数据库引擎对象，可以创建数据库连接
engine = None


def next_id(t=None):
    # 生成一个唯一id
    # 如果没有传入参数，由系统当前时间15位+随机数（由伪随机数得来）填充3个0拼接得到一个长度为50的字符串
    if t is None:
        t = time.time()
        return '%015d%000' % (int(t * 1000), uuid.uuid4().hex)


def _profiling(start, sql=''):
    # 解析sql执行时间方法,如果耗时超过0.1毫秒则打印警告信息
    t = time.time() - start
    if t > 0.1:
        logging.warning('[PROGILING] [DB] %s: %s' % (t, sql))
    else:
        logging.info('[PROGILING] [DB] %s: %s' % (t, sql))


class DBError(Exception):
    # 自定义数据异常
    pass


class MultiColumnsError(DBError):
    # 自定义数据库异常中的多列异常
    pass


class Dict(dict):
    """
    字典对象
    实现一个简单的可以通过属性访问的字典 比如 x.key = value
    """

    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__iter__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, item):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value


def create_engine(user, password, database, host='127.0.0.1', port=3306, **kw):
    # 创建数据引擎的方法
    import mysql.connector
    global engine
    # 重复创建抛出异常
    if engine is not None:
        raise DBError('Egnine is already initialized')
    # 构建连接数据库所需要的信息
    params = dict(user=user, password=password, database=database, host=host, port=port)
    defaults = dict(use_unicode=True, charset='utf8', collation='utf8_general_ci', autocommit=False)
    # ?
    for k, v in defaults.items():
        params[k] = kw.pop(k, v)
    params.update(kw)
    params['buffered'] = True
    engine = _Engine(lambda: mysql.connector.connect(**params))
    # 此处可以测试是否连接成功
    logging.info('Init mysql engine <%s> ok.' % hex(id(engine)))


class _Engine(object):
    # 数据库引擎对象，保存create_engine创建出来的数据库连接
    def __init__(self, connect):
        self._connect = connect

    def connect(self):
        return self._connect()


class _DbCtx(threading.local):
    # 持有数据库连接的上下文对象
    def __init__(self):
        self.connection = None
        self.transaction = 0

    def is_init(self):
        return not self.connection is None

    def init(self):
        self.connection = _LazyConnection()
        self.transaction = 0

    def cleanup(self):
        self.connection.cleanup()
        self.connection = None

    def cursor(self):
        return self.connection.cursor()


_db_ctx = _DbCtx()


class _LazyConnection(object):
    """
    惰性连接对象，对一次数据库连接的封装
    仅当需要cursor对象时，才连接数据库，获取连接
    """

    def __init__(self):
        self.connection = None

    def cursor(self):
        if self.connection is None:
            _connection = engine.connect()
            logging.info('[CONNECTION] [OPEN] connection <%s>...' % hex(id(_connection)))
            self.connection = _connection
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def cleanup(self):
        if self.connection:
            _connection = self.connection
            self.connection = None
            logging.info('[Connection] [Close] connection <%s>...' % hex(id(_connection)))
            _connection.close()


class _ConnectionCtx(object):
    # 数据库连接上下文
    # 定义了enter() 和exit()方法的对象可以用于with语句，确保任何情况下exit()方法可以被调用
    def __enter__(self):
        global _db_ctx
        self.should_cleanup = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.should_cleanup = True
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _db_ctx
        if self.should_cleanup:
            _db_ctx.cleanup()


class _TransactionCtx(object):
    # 定义一个事务上下文,封装了提交和回滚操作，并在事务退出时自动清理连接
    def __enter__(self):
        global _db_ctx
        self.show_close_conn = False
        if not _db_ctx.is_init():
            _db_ctx.init()
            self.show_close_conn = True
        _db_ctx.transaction += 1
        return self


def __exit__(self, exc_type, exc_val, exc_tb):
    global _db_ctx
    _db_ctx.transaction -= 1
    try:
        if _db_ctx.transaction == 0:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
    finally:
        if self.show_close_conn:
            _db_ctx.cleanup()


def commit(self):
    global _db_ctx
    try:
        _db_ctx.connection.commit()
    except:
        _db_ctx.connection.rollback()
        raise


def rollback(self):
    global _db_ctx
    _db_ctx.connection.rollback()


def connection():
    """
    获取一个连接
    通过_ConnectionCtx对_db_ctx的封装，使得惰性连接可以自动获取和释放
    """
    return _ConnectionCtx()


def with_connection(func):
    """
    设计一个连接装饰器 替换with，让代码更优雅
    @with_connection
    def fpp(*args, **kw):
    f1()
    f2()
    f3()
    :param func: 一个方法
    :return:
    """

    @functools.wraps(func)
    def _wrapper(*args, **kw):
        with _ConnectionCtx():
            return func(*args, **kw)

    return _wrapper


def transaction():
    """
    db核心模块函数 用户实现事务功能
    支持事务：
        with db.transaction():
        db.select('')
        db.update('')

    支持事务嵌套：
        with db.transaction():
            transaction1
            transaction1
    :return:
    """
    return _TransactionCtx()


def with_transaction(func):
    """
    设计一个事务装饰器 替换with语法，让代码更优雅
    @with_transaction
    def do_in_transaction():

    :param func:
    :return:
    """

    @functools.wraps(func)
    def _wrapper(*args, **kw):
        start = time.time()
        with _TransactionCtx():
            func(*args, **kw)
        _profiling(start)

    return _wrapper


@with_connection
def _select(sql, first, *args):
    """
    封装的查询方法，返回一个结果或多个结果组成的列表
    :param sql: sql语句
    :param first: 是否只返回第一条数据
    :param args: 参数
    :return:   查询结果
    """
    global _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')
    logging.info('SQL:%s, ARGS:%s' % (sql, args))
    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        if cursor.description:
            names = [x[0] for x in cursor.description]
        if first:
            values = cursor.fetchone()
            if not values:
                return None
            return Dict(names, values)
        return [Dict(names, x) for x in cursor.fetchall()]
    finally:
        if cursor:
            cursor.close()


def select_one(sql, *args):
    """
    执行查询语句，只返回第一条结果，如果没有则返回none
    :param sql:
    :param args:
    :return:
    """
    return _select(sql, True, *args)


def select_int(sql, *args):
    """
    执行查询语句 返回一个数值，有可能是查询结果数或者第一行的第一列数据
    :param sql: sql语句
    :param args: 参数
    :return: 数值
    """
    d = _select(sql, True, *args)
    if len(d) != 1:
        raise MultiColumnsError('Error only one column')
    return d.values()[0]


def select(sql, *args):
    """
    执行查询语句，返回列表集合
    :param sql: sql语句
    :param args: 参数
    :return: 查询结果
    """
    return _select(sql, False, *args)


@with_connection
def _update(sql, *args):
    """
    封装的更新方法，返回update的行数
    :param sql:
    :param args:
    :return:
    """
    global _db_ctx
    cursor = None
    sql = sql.replace('?', '%s')
    logging.info('SQL:%s, ARGS:%s' % (sql, args))

    try:
        cursor = _db_ctx.connection.cursor()
        cursor.execute(sql, args)
        r = cursor.rowcount
        if _db_ctx.transaction == 0:
            # no transactions environment
            logging.info('auto commit')
        _db_ctx.connection.commit()
        return r
    finally:
        if cursor:
            cursor.close()


def update(sql, *args):
    """
    对外提供的更新方法
    :param sql: sql语句
    :param args: 参数
    :return: 更新行数
    """
    return _update(sql, *args)


def insert(table, **kw):
    """
    对外提供的插入方法
    :param table: 表名
    :param kw: 字段和值的集合
    :return: 变更的行数
    """
    cols, args = zip(*kw.iteritems())
    sql = 'insert into `%s` (%s) values (%s)' % (
        table, ','.join(['`%s`' % col for col in cols]), ','.join(['?' for i in range(len(cols))]))
    return _update(sql, *args)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    create_engine('root', 'admin_zzc', 'test')
    update('drop table if exists user')
    update('create table user (id int primary key, name text, email text, passwd text, last_modified real)')
    first_select = select('select * from user')
    print('first_select = %s', first_select)
    new_user = dict(id=1000, name='zzc', email='631965991@qq.com', passwd='123456', last_modified=time.time())
    insert_result = insert('user', new_user)
    print('insert_result = %s', insert_result)
    second_select = select('select * from user')
    print('second_select = %s', second_select)

    import doctest
    doctest.testmod()
