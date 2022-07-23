# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import schedule
import datetime
import time

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import main
from utils import logger


def console_thread():
    while True:
        try:
            try:
                cmd_args = input().split(' ')
            except (EOFError, UnicodeDecodeError):
                continue

            cmd = cmd_args[0]
            if not cmd:
                continue

            if cmd == "notify":
                console_cmd_notify(cmd_args)
            elif cmd == "alert":
                console_cmd_alert(cmd_args)
            elif cmd == "help":
                logger.info("Commands: notify jobs")
            elif cmd == "jobs":
                logger.info("Schedule Jobs:")
                for job in schedule.get_jobs():
                    logger.info(f'{job}: {job.next_run.date()}')
            else:
                logger.info("Command not found :C")
        except:
            logger.error("Exception in console", exc_info=True)


def console_cmd_notify(cmd_args):
    if len(cmd_args) != 3:
        logger.info("notify <type: students|teachers> <date: dd-mm-yyyy or empty>")
        return

    notify_type = cmd_args[1]
    if notify_type not in ["students", "teachers"]:
        logger.error(f"Unknown arg {notify_type} Allowed: students, teachers")
        return

    teachers = True if cmd_args[1] == "teachers" else False
    date = cmd_args[2] if len(cmd_args) == 3 else None

    try:
        date = datetime.datetime.strptime(date, '%d-%m-%Y')
    except:
        logger.error("Error in date", exc_info=True)
        return

    main.notify(
        teachers=teachers,
        date=date
    )


def console_cmd_alert(cmd_args):
    if len(cmd_args) != 2:
        logger.info("Подтвердите рассылку дополнительным любым аргументом.")
        return

    text = '👋 Ты планируешь развиваться в IT? Тебе интересно находить новых людей, общаться и обмениваться опытом?\n\n👨‍💻 Приглашаю вступить в чат начинающих <b>разработчиков</b>.\n\n<i>Чат создан выпускниками и не относится к образовательному учреждению.</i>'

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton('❌ Не интересно', callback_data='chat=n'),
        InlineKeyboardButton('✨ Интересно', callback_data='chat=y'))

    clients = main.storage.get_clients()

    for client in clients:
        try:
            client_id = client.get_id()

            r = main.bot.send_message(client_id, text, reply_markup=markup)
            #main.bot.pin_chat_message(r.chat.id, r.message_id, disable_notification=True)
        except:
            logger.error(f'Ошибка при отправке сообщения клиенту <{client_id}>', exc_info=True)
        time.sleep(0.25)
        
    logger.info('Рассылка завершена.')

