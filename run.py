# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import time
import threading
import schedule

import bot


if __name__ == "__main__":
    bot.logger.debug("Initializing bot polling..")
    thread_bot = threading.Thread(target=bot.bot_polling)
    thread_bot.setName('BotThread')
    thread_bot.daemon = True
    thread_bot.start()

    bot.logger.debug("Initializing schedule polling..")
    thread_schedule = threading.Thread(target=bot.schedule_polling)
    thread_schedule.setName('ScheduleThread')
    thread_schedule.daemon = True
    thread_schedule.start()

    console_thread = threading.Thread(target=bot.console)
    console_thread.setName('ConsoleThread')
    console_thread.daemon = True
    console_thread.start()

    schedule.every().day.at(bot.Settings.SCHEDULE_NOTIFY_START_TIME).do(bot.run_threaded, name='NotifyStudents', func=bot.schedule_notify_students)
    schedule.every().day.at(bot.Settings.SCHEDULE_NOTIFY_START_TIME).do(bot.run_threaded, name='NotifyTeachers', func=bot.schedule_notify_teachers)

    # Поддерживать работу основной программы, пока бот работает.
    while True:
        try:
            if not thread_bot.is_alive():
                bot.logger.error("Bot polling pool is not alive, shutting down..")
                break

            if not schedule.get_jobs():
                bot.logger.error("Schedule jobs not found, shutting down..")
                break

            schedule.run_pending()

            time.sleep(10)
        except KeyboardInterrupt:
            bot.logger.info("Shutting down..")
            break
