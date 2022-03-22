# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import pymongo
from bson.objectid import ObjectId
import datetime
from telebot.types import User

from utils import logger
from utils.data import *


class Storage:
    def __init__(self, connect, database, collections):
        self.mongo_client = pymongo.MongoClient(connect, authSource='admin')
        self.db = self.mongo_client.get_database(database)
        self.clients = self.db.get_collection(collections.get('clients'))
        self.schedule = self.db.get_collection(collections.get('schedule'))
        self.students = self.db.get_collection(collections.get('students'))

    def get_client(self, user: User) -> Client:
        data = self.get_data(self.clients, user.id)

        if not data:
            #logger.debug(f'User <{user.id}:{user.username}> not found.')
            data = SDict({'_id': user.id})

        client = Client(data)

        return client

    def get_clients(self):
        data = self.clients.find()

        clients = []
        for _ in data:
            clients.append(Client(_))

        return clients

    def get_student_data_by_phone_number(self, phone):
        data = self.get_data(self.students, phone, 'phone')

        if not data:
            return None

        student = Student(data)

        return student

    def get_student_by_id(self, sid):
        key = ObjectId(sid)

        data = self.get_data(self.students, key)
        if not data:
            return None

        student = Student(data)

        return student

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

        save_result = self.save_data(self.clients, user.id, client)

        if save_result:
            logger.debug(f'Client <{user.id}:{user.username}> saved, result: {save_result}')
            return True

        logger.error(f'Client <{user.id}:{user.username}> not saved, result: {save_result}')

        return False

    def save_student(self, student: Student) -> bool:
        if not student.changed:
            logger.debug(f'Student <{student.get_id()}:{student.get_name(False)}> already saved, data not changed.')
            return True

        save_result = self.save_data(self.students, student.get_id(), student)

        if save_result:
            logger.debug(f'Student <{student.get_id()}:{student.get_name(False)}> saved, result: {save_result}')
            return True

        logger.error(f'Student <{student.get_id()}:{student.get_name(False)}> not saved, result: {save_result}')

        return False

    def save_schedule(self, schedule: ScheduleArticle) -> bool:
        _id = schedule['date'].strftime('%d-%m-%y')
        schedule['_id'] = _id

        if not schedule.changed:
            logger.debug(f'Schedule <{_id}> already saved, data not changed.')
            return True

        schedule['timestamp'] = int(datetime.datetime.now().timestamp())

        save_result = self.save_data(self.schedule, _id, schedule)
        if save_result:
            logger.debug(f'Schedule <{_id}> saved, result: {save_result}')
            return True

        logger.error(f'Schedule <{_id}> not saved, result: {save_result}')

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
            operation = c.update_one({name: value}, {"$set": data})
            result = operation.raw_result if operation else None
        else:
            operation = c.insert_one(data)
            result = operation.inserted_id if operation else None

        return result
