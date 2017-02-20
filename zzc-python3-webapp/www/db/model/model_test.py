import asyncio
import logging
import sys

from www.db import User


async def test():
    await www.db.orm.create_pool(loop=loop, user='root', password='admin_zzc', db='android_hot_fix')
    u = User(name='joye', email='zhichao@qfpay.com', passwd='123456', image='')
    await u.save()
    # await db.orm.destroy_pool()
    logging.info('test ok')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()
    if loop.is_closed():
        sys.exit(0)
