# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import telebot
import traceback
from time import sleep
from functools import wraps

from utils import *

logger = init_logger()

logger.info("Initializing..")

logger.info("Initializing localization..")
L10n = Json(Settings.L10N_RU_FILE)

try:
	logger.info("Initializing storage..")
	storage = Storage(Settings.MONGO, Settings.MONGO_DATABASE)
	logger.debug(f"MongoDB Server version: {storage.mongo_client.server_info()['version']}")
except Exception as e:
	logger.error('Storage crashed', exc_info=True)
	raise RuntimeError from e

logger.debug("Initializing telebot..")

telebot.apihelper.ENABLE_MIDDLEWARE = True

telebot.logger.removeHandler(telebot.logger.handlers[0])
telebot.logger.setLevel(level=logging.DEBUG if Settings.DEBUG_TELEBOT else logging.INFO)

telebot.logger.addHandler(get_logger_file_handler())
telebot.logger.addHandler(get_logger_stream_handler())

bot = telebot.TeleBot(Settings.BOT_TOKEN, parse_mode='html')

bot.enable_save_next_step_handlers(delay=3)
bot.load_next_step_handlers()

bot.str = L10n


def bot_polling():
	try:
		while True:
			try:
				logger.info("Starting bot polling.")
				bot.polling(none_stop=True, interval=Settings.BOT_INTERVAL, timeout=Settings.BOT_TIMEOUT)
			except Exception as ex:
				logger.error(f"Bot polling failed, restarting in {Settings.BOT_TIMEOUT} sec. Error:\n{traceback.format_exc()}")
				bot.stop_polling()
				sleep(Settings.BOT_TIMEOUT)
			else:
				bot.stop_polling()
				logger.info("Bot polling loop finished.")
				break
	except Exception:
		logger.error('Bot polling loop crashed', exc_info=True)


def schedule_polling():
	try:
		t = Settings.SCHEDULE_TIME
		g = CollegeScheduleGrabber(Settings.DOMAIN, Settings.BLOG_PATH)

		while True:
			blog = g.get_blog()
			day_dt = CollegeScheduleAbc.get_day()
			article_link = CollegeScheduleAbc.find_article(day_dt, blog)

			if not article_link:
				sleep(t / 2)
				continue

			schedule = g.get_article(article_link)

			if not schedule:
				sleep(t / 2)
				continue

			logger.info(schedule)

			sleep(t)
	except Exception:
		logger.error('Schedule polling loop crashed', exc_info=True)


def load_client(func):
	@wraps(func)
	def wrapper(self, *args, **kwargs):
		logger.debug('Hello from test wrapper')

		logger.debug(args)
		logger.debug(kwargs)

		message = get_variable('message')
		logger.debug(f'message: {message}')

		client = storage.get_client(message.from_user)

		message.client = client

		return func(self, *args, **kwargs)

	return wrapper


@bot.middleware_handler(update_types=['message'])
def middleware_handler(bot_instance, message):
	client = storage.get_client(message.from_user)
	message.client = client


@bot.message_handler(commands=['test'])
def test_cmd(message):
	bot.reply_to(message, 'ok')


"""
@bot.message_handler(commands=['join'])
def send_welcome(message):
	msg = bot.reply_to(message, "What's your name?")
	bot.register_next_step_handler(msg, process_name_step)


def process_name_step(message):
	try:
		name = message.text

		client = message.client
		client['name'] = name
		storage.save_client(message.from_user, client)

		msg = bot.reply_to(message, 'How old are you?')
		bot.register_next_step_handler(msg, process_age_step)
	except Exception as e:
		bot.reply_to(message, 'oooops')


def process_age_step(message):
	try:
		age = message.text
		if not age.isdigit():
			msg = bot.reply_to(message, 'Age should be a number. How old are you?')
			bot.register_next_step_handler(msg, process_age_step)
			return

		client = message.client
		client['age'] = age
		storage.save_client(message.from_user, client)

		markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
		markup.add('Male', 'Female')
		msg = bot.reply_to(message, 'What is your gender', reply_markup=markup)
		bot.register_next_step_handler(msg, process_sex_step)
	except Exception as e:
		bot.reply_to(message, 'oooops')


def process_sex_step(message):
	try:
		sex = message.text

		client = message.client

		if (sex == u'Male') or (sex == u'Female'):
			client['sex'] = sex

			storage.save_client(message.from_user, client)
		else:
			raise Exception("Unknown sex")
			bot.send_message(chat_id, 'Nice to meet you ' + client['name'] + '\n Age:' + str(client['age']) + '\n Sex:' + client['sex'])
	except Exception as e:
		bot.reply_to(message, 'oooops')
"""

"""
@bot.message_handler(commands=['is_admin', 'isadmin'])
def is_admin(message):
	text = bot.str.get('cmd.is_admin.yes') if message.client.is_admin == True else bot.str.get('cmd.is_admin.no')
	bot.reply_to(message, text)


@bot.message_handler(commands=['is_staff', 'isstaff'])
def is_staff(message):
	text = bot.str.get('cmd.is_staff.yes') if message.client.is_staff == True else bot.str.get('cmd.is_staff.no')
	bot.reply_to(message, text, parse_mode='html')


@bot.message_handler(commands=['id'])
def get_my_id(message):
	bot.reply_to(message, f'&#10145; Ваш идентификатор Telegram:\n<code>{message.from_user.id}</code>')


@bot.message_handler(commands=['reg'])
def staff_reg(message):
	client = message.client
	email = message.text.split(' ')[-1]

	text = f'На почту <code>{email}</code> отправлено письмо с кодом подтверждения.'

	client['email'] = email

	save = storage.save_client(message.from_user, client)

	bot.reply_to(message, text)


@bot.message_handler(regexp='помощь')
@bot.message_handler(commands=['start', 'help', 'commands', 'старт', 'помощь', 'команды', 'комманды'])
def send_help(message):
	logger.debug('cmd send_help')
	text, markup = gen_help()
	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(regexp='расписание')
@bot.message_handler(commands=['расписание'])
def send_schedule_select_group(message):
	text, markup = gen_schedule_groups()
	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query_schedule_select_group(call):
	callback_data = json.dumps({'test': True})

	markup = telebot.types.InlineKeyboardMarkup()
	markup.row(
		telebot.types.InlineKeyboardButton('Подтвердить', callback_data=call.data),
		telebot.types.InlineKeyboardButton('Назад', callback_data=callback_data)
	)

	group = call.data
	text = f'Хочешь подписаться на расписание группы {group}?'

	bot.edit_message_text(text=text, chat_id=call.message.chat.id, message_id=call.message.id, reply_markup=markup)

	#bot.answer_callback_query(call.id, f"answer: {call.data}")
"""

