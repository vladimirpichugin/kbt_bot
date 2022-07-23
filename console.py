# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import schedule
import datetime

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
