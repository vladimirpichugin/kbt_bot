# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import main

import datetime
import time

from utils import logger, get_weekday
from commands import cmd_schedule_teacher, cmd_schedule_group

from settings import Settings


def notify(teachers=False, next_day=True, date=None):
    t = Settings.SCHEDULE_NOTIFY_PAUSE_TIME

    while True:
        today = datetime.datetime.today()

        if today.hour >= 23:
            logger.error(f'Рассылка отменена, позже 11 часов рассылка не отправляется.')
            break  # Fail.

        day = date if date else get_weekday(next_day=next_day)

        schedule = main.storage.get_schedule(date=day)
        if not schedule:
            logger.debug(f'storage.get_schedule: {schedule}')
            logger.error(f'Рассылка перенесена, нет расписания на {day}.')
            logger.info(f'Повторная попытка через {t / 60} мин.')
            time.sleep(t)
            continue  # Try again.

        clients = main.storage.get_clients()
        if not clients:
            logger.error(f'Рассылка перенесена, нет получателей.')
            logger.info(f'Повторная попытка через {t / 60} мин.')
            time.sleep(t)
            continue  # Try again.

        notify_clients = {}

        subscribe_key = 'schedule_teachers' if teachers else 'schedule_groups'
        for client in clients:
            client_id = client.get_id()

            subscribe_values = client.get(subscribe_key, [])

            if not subscribe_values:
                continue

            for subscribe_value in subscribe_values:
                if subscribe_value not in notify_clients:
                    notify_clients[subscribe_value] = []

                if subscribe_value not in notify_clients[subscribe_value]:
                    notify_clients[subscribe_value].append(client_id)

        for key in notify_clients.keys():
            if teachers:
                text, markup = cmd_schedule_teacher(schedule, key, [key], day, include_back_button=False)
            else:
                text, markup = cmd_schedule_group(schedule, key, [key], day, include_back_button=False)

            notify_clients_ids = notify_clients.get(key, [])
            for client_id in notify_clients_ids:
                try:
                    main.bot.send_message(client_id, text, reply_markup=markup)
                except:
                    logger.error(f'Ошибка при отправке сообщения клиенту <{client_id}>', exc_info=True)

        logger.debug('Рассылка завершена.')
        break  # OK.


def notify_students():
    today = datetime.datetime.today()

    # todo: А если в пятницу расписание не опубликовали?
    if today.isoweekday() >= 6:
        logger.info(f'Рассылка отменена, по выходным рассылка не отправляется.')
        return

    notify(teachers=False, next_day=True)


def notify_teachers():
    today = datetime.datetime.today()

    # todo: А если в пятницу расписание не опубликовали?
    if today.isoweekday() >= 6:
        logger.info(f'Рассылка отменена, по выходным рассылка не отправляется.')
        return

    notify(teachers=True, next_day=True)
