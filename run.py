# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import threading
import schedule
import time

import main
import console


if __name__ == "__main__":
    main.logger.debug("Initializing bot polling..")
    thread_bot = threading.Thread(target=main.bot_polling)
    thread_bot.setName("BotThread")
    thread_bot.daemon = True
    thread_bot.start()

    console_thread = threading.Thread(target=console.console_thread)
    console_thread.setName("ConsoleThread")
    console_thread.daemon = True
    console_thread.start()

    schedule.every().day.at(main.Settings.SCHEDULE_NOTIFY_START_TIME).do(main.run_threaded, name='NotifyStudents', func=main.notify_students)
    schedule.every().day.at(main.Settings.SCHEDULE_NOTIFY_START_TIME).do(main.run_threaded, name='NotifyTeachers', func=main.notify_teachers)

    # Поддерживать работу основной программы, пока бот работает.
    while True:
        try:
            if not thread_bot.is_alive():
                main.logger.error("Bot polling pool is not alive, shutting down..")
                break

            if not schedule.get_jobs():
                main.logger.error("Schedule jobs not found, shutting down..")
                break

            if main.Settings.NOTIFY:
                schedule.run_pending()

            time.sleep(10)
        except KeyboardInterrupt:
            main.logger.info("Shutting down..")
            break
