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

    STAFF_IDS = []
    ADMIN_IDS = []
    DEV_IDS = []

    SCHEDULE_TIME = 60 * 60

    DOMAIN = 'https://cbcol.mskobr.ru'
    BLOG_PATH = '/elektronnye_servisy/blog/'

    GROUPS = {
        'Б': {
            'NAME': 'Банковское дело',
            'GROUPS': [
                'Б11-21', 'Б12-21', 'Б21-20',
                'Б22-20', 'Б31-19'
            ]
        },
        'БА': {
            'NAME': 'Эксплуатация беспилотных авиационных систем',
            'GROUPS': [
                'БА11-21', 'БА12-21', 'БА13-21',
                'БА21-20', 'БА22-20', 'БА23-20',
                'БА31-19', 'БА32-19', 'БА33-19',
                'БА34-19', 'БА35-19', 'БА41-18',
                'БА42-18'
            ]
        },
        'И': {
            'NAME': 'Прикладная информатика (по отраслям)',
            'GROUPS': [
                'И32-19'
            ]
        },
        'ИБ': {
            'NAME': 'Информационная безопасность',
            'GROUPS': [
                'ИБ11-21', 'ИБ12-21', 'ИБ13-21',
                'ИБ21-20', 'ИБ22-20', 'ИБ23-20',
                'ИБ31-19', 'ИБ32-19', 'ИБ33-19',
                'ИБ41-18'
            ]
        },
        'ИС': {
            'NAME': 'Информатика и вычислительные системы',
            'GROUPS': [
                'ИС11-21', 'ИС12-21', 'ИС22-20',
                'ИС31-19', 'ИС32-19'
            ]
        },
        'СА': {
            'NAME': 'Сетевое и системное администрирование',
            'GROUPS': [
                'СА11-21', 'СА21-20', 'СА22-20',
                'СА31-19', 'СА32-19', 'СА41-18'
            ]
        },
        'Ф': {
            'NAME': 'Финансы',
            'GROUPS': [
                'Ф11-21', 'Ф21-20', 'Ф31-19'
            ]
        },
        'Э': {
            'NAME': 'Экономика и бухгалтерский учёт',
            'GROUPS': [
                'Э11-21', 'Э21-20', 'Э31-19'
            ]
        }
    }
