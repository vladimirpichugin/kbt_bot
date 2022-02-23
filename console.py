# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
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
                logger.info("Commands: notify")
            else:
                logger.info("Command not found :C")
        except:
            logger.error("Exception in console", exc_info=True)


def console_cmd_notify(cmd_args):
    if len(cmd_args) != 3:
        logger.info("notify <type: students|teachers> <next day: true|false>")
        return

    notify_type = cmd_args[1]
    if notify_type not in ["students", "teachers"]:
        logger.error(f"Unknown arg {notify_type} Allowed: students, teachers")
        return

    teachers = True if cmd_args[1] == "teachers" else False
    next_day = True if cmd_args[2] else False

    main.notify(teachers=teachers, next_day=next_day)
