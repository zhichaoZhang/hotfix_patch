# coding=utf-8
# 导出MySql驱动
import mysql.connector  # 设置用户名、密码、数据库名

conn = mysql.connector.connect(user='root',
                               password='admin_zzc',
                               host='127.0.0.1',
                               database='test')
cursor = conn.cursor()

# 创建user表
cursor.execute('create table user2 (id varchar(20) primary key, name varchar(20))')

# 插入一行记录，注意mysql的占位符是%s
cursor.execute('insert into user2 (id, name) value (%s, %s)', ['1', 'Michael'])
cursor.rowcount

# 提交事务
conn.commit()
cursor.close()

# 运行查询
cursor = conn.cursor()
cursor.execute('select * from user2 where id = %s', ('1',))
values = cursor.fetchall()
print(values)

cursor.close()

# 关闭连接
conn.close()
