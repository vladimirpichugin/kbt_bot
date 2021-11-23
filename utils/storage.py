# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import datetime

import pymongo
from telebot.types import User

from .data import *
from .helpers import init_logger


logger = init_logger()


class Storage:
    def __init__(self, connect, database):
        self.mongo_client = pymongo.MongoClient(connect, authSource='admin')
        self.db = self.mongo_client.get_database(database)
        self.clients = self.db.get_collection('clients')
        self.schedule = self.db.get_collection('schedule')

    def get_client(self, user: User) -> Client:
        data = self.get_data(self.clients, user.id)

        if not data:
            logger.debug(f'User <{user.id}:{user.username}> not found.')
            data = SDict({'_id': user.id})

        client = Client(data)

        return client

    def get_schedule(self, date: datetime.datetime):
        key = date.strftime('%d-%m-%y')

        data = self.get_data(self.schedule, key)
        if not data:
            return None

        schedule = ScheduleArticle(data)

        return schedule

    def save_client(self, user: User, client: Client) -> bool:
        if not client.changed:
            logger.debug(f'Client <{user.id}:{user.username}> already saved, data not changed.')
            return True

        save = self.save_data(self.clients, user.id, client)

        if save:
            logger.debug(f'Client <{user.id}:{user.username}> saved, result: {save}')
            return True

        logger.error(f'Client <{user.id}:{user.username}> not saved, result: {save}')

        return False

    def save_schedule(self, schedule: ScheduleArticle) -> bool:
        _id = schedule['date'].strftime('%d-%m-%y')
        schedule['_id'] = _id

        if not schedule.changed:
            logger.debug(f'Schedule <{_id}> already saved, data not changed.')
            return True

        schedule['timestamp'] = int(datetime.datetime.now().timestamp())

        save = self.save_data(self.schedule, _id, schedule)

        if save:
            logger.debug(f'Schedule <{_id}> saved, result: {save}')
            return True

        logger.error(f'Schedule <{_id}> not saved, result: {save}')

        return False

    @staticmethod
    def get_data(c: pymongo.collection.Collection, value, name="_id"):
        data = c.find_one({name: value})

        if data:
            return SDict(data)

        return None

    @staticmethod
    def save_data(c: pymongo.collection.Collection, value, data: SDict, name="_id"):
        if c.find_one({name: value}):
            return c.update_one({name: value}, {"$set": data})
        else:
            return c.insert_one(data)
