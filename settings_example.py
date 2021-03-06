# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class Settings:
    DEBUG = True
    DEBUG_TELEBOT = False

    AUTH_URL = 'https://kbt.moscow/profile?act={act}&role=fast-auth&uid={uid}&hash={hash}&d={d}&s={s}&v=1'
    AUTH_SERVICE = ''
    AUTH_SERVICE_PUB_KEY = ''

    BOT_TOKEN = ''
    BOT_TIMEOUT = 10
    BOT_INTERVAL = 3

    L10N_RU_FILE = 'L10n/ru.json'

    MONGO = ''
    MONGO_DATABASE = ''
    COLLECTIONS = {
        'clients': 'clients_test',
        'schedule': 'schedule',
        'students': 'students',
        'groups': 'groups',
        'specialties': 'specialties'
    }

    SCHEDULE_NOTIFY_START_TIME = '10:00'  # Начнется проверка на наличие расписания для рассылки.
    SCHEDULE_NOTIFY_PAUSE_TIME = 60 * 5  # Если расписание не найдено, то рассылка может быть отложена на это время.
    NOTIFY = True

    DOMAIN = 'https://cbcol.mskobr.ru'

    GROUPS = {
    }

    BELL_SCHEDULE_DEFAULT = [
    ]

