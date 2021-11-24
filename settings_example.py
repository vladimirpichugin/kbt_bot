# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

class Settings:
    DEBUG = True
    DEBUG_TELEBOT = False

    BOT_TOKEN = ''
    BOT_TIMEOUT = 10
    BOT_INTERVAL = 3

    L10N_RU_FILE = 'L10n/ru.json'

    MONGO = ''
    MONGO_DATABASE = ''

    SCHEDULE_TIME = 60 * 10  # Частота обращений к сайту за расписанием.
    SCHEDULE_NOTIFY_START_TIME = '10:00'  # Начнется проверка на наличие расписания для рассылки.
    SCHEDULE_NOTIFY_PAUSE_TIME = 60 * 5  # Если расписание не найдено, то рассылка может быть отложена на это время.

    DOMAIN = 'https://cbcol.mskobr.ru'
    BLOG_PATH = '/elektronnye_servisy/blog/'

    GROUPS = {
    }
