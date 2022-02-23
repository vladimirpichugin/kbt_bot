# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import re
import time
import datetime
import hashlib
import threading

from settings import Settings


def run_threaded(name, func):
    job_thread = threading.Thread(target=func)
    job_thread.setName(f'{name}Thread')
    job_thread.start()


def get_weekday(next_day=False):
    dt = datetime.datetime.today()

    if dt.isoweekday() < 5 and (dt.hour >= 17 or next_day):
        return dt + datetime.timedelta(days=1)

    if dt.isoweekday() == 5 and (dt.hour >= 17 or next_day):
        return dt + datetime.timedelta(days=-dt.weekday(), weeks=1)

    if dt.isoweekday() > 5:
        return dt + datetime.timedelta(days=-dt.weekday(), weeks=1)

    return dt


def get_phone(string):
    pattern = re.compile(r'^\+?(?P<phone_number>\d{11})$')
    r = re.search(pattern, string)
    if r is not None:
        return int(r.group())
    return None


def get_fast_auth_url(uid):
    url = Settings.AUTH_URL
    date = int(time.time())

    a_hash = ' {up} '.join(str(_) for _ in [uid, Settings.AUTH_SERVICE, date, Settings.AUTH_SERVICE_PUB_KEY])
    a_hash = a_hash.encode('utf-8')
    a_hash = hashlib.sha256(a_hash).hexdigest()

    url = url.format(hash=a_hash, uid=uid, d=date, s=Settings.AUTH_SERVICE)

    return url
