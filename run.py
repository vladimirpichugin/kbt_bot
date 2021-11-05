# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import time
import threading

import bot


if __name__ == "__main__":
    bot.logger.debug("Initializing schedule polling..")
    thread_schedule = threading.Thread(target=bot.schedule_polling)
    thread_schedule.setName('ScheduleThread')
    thread_schedule.daemon = True
    thread_schedule.start()

    bot.logger.debug("Initializing bot polling..")
    bot_thread = threading.Thread(target=bot.bot_polling)
    bot_thread.setName('BotThread')
    bot_thread.daemon = True
    bot_thread.start()

    # Поддерживать работу основной программы, пока бот работает.
    while True:
        try:
            if not bot_thread.is_alive():
                bot.logger.error("Bot polling pool is not alive, shutting down..")
                break
            time.sleep(10)
        except KeyboardInterrupt:
            bot.logger.info("Shutting down..")
            break
