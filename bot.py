# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import telebot
import threading
import fpdf
from time import sleep

from utils import *

logger = init_logger()
logger.info("Initializing..")

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


def run_threaded(name, func):
	job_thread = threading.Thread(target=func)
	job_thread.setName(f'{name}Thread')
	job_thread.start()


def bot_polling():
	try:
		while True:
			try:
				logger.info("Starting bot polling.")
				bot.polling(none_stop=True, interval=Settings.BOT_INTERVAL, timeout=Settings.BOT_TIMEOUT)
			except Exception as ex:
				logger.error(f"Bot polling failed, restarting in {Settings.BOT_TIMEOUT} sec.", exc_info=True)
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
			try:
				articles = g.parse_articles()

				if not articles:
					sleep(t / 2)
					continue

				articles = CollegeScheduleAbc.get_articles(articles)

				for article in articles:
					path = article.get('link')

					date = article.get('date')
					if not date:
						continue

					if date < datetime.datetime.now():
						logger.debug(f'{date} skipped')
						continue

					article_groups = g.parse_article(path)
					for group in article_groups:
						lessons = CollegeScheduleAbc.parse_lessons(group.get('lessons'))
						group['lessons'] = lessons

					article['data'] = article_groups

					for group in article_groups:
						logger.debug(group)

					storage.save_schedule(article)
			except Exception:
				logger.debug(article)
				logger.error('Schedule polling loop crashed', exc_info=True)

			sleep(t)
	except Exception:
		logger.error('Schedule polling loop crashed', exc_info=True)


def schedule_notify():
	t = Settings.SCHEDULE_NOTIFY_PAUSE_TIME

	while True:
		today = datetime.datetime.today()

		if today.isoweekday() >= 6:
			logger.info(f'По выходным рассылка не отправляется.')
			break  # Ok.

		if today.hour >= 23:
			logger.error(f'Рассылка отменена, вышли за границы времени.')
			break  # Fail.

		day = CollegeScheduleAbc.get_weekday(next_day=True)

		schedule = storage.get_schedule(date=day)
		if not schedule:
			logger.error(f'Рассылка отменена, нет расписания на {day}. Повторная попытка через {t / 60} минут.')
			logger.debug(f'schedule: {schedule}')
			sleep(t)
			continue  # Try again.

		clients = storage.get_clients()
		if not clients:
			logger.error(f'Рассылка отменена, нет получателей. Повторная попытка через {t / 60} минут.')
			sleep(t)
			continue  # Try again.

		groups_clients = {}
		for client in clients:
			client_id = client.get_id()
			schedule_groups = client.get('schedule_groups', [])

			if not schedule_groups:
				continue

			for group in schedule_groups:
				if group not in groups_clients.keys():
					groups_clients[group] = []

				if client_id not in groups_clients[group]:
					groups_clients[group].append(client_id)

		for group_name in groups_clients.keys():
			text, markup = cmd_schedule_group(schedule, group_name, [group_name], day, include_back_button=False)

			group_clients_ids = groups_clients[group_name]
			for client_id in group_clients_ids:
				try:
					bot.send_message(client_id, text, reply_markup=markup)
				except Exception as e:
					logger.error(f'Ошибка при отправке сообщения клиенту <{client_id}>', exc_info=True)

		logger.debug('Рассылка завершена.')
		break  # OK.


def console():
	while True:
		try:
			try:
				cmd_args = input().split(' ')
			except EOFError:
				continue

			cmd = cmd_args[0]

			if cmd == "notify":
				schedule_notify()
			else:
				logger.info("Command not found")
		except Exception:
			logger.error("Exception in console", exc_info=True)


@bot.middleware_handler(update_types=['message'])
def middleware_handler_message(bot_instance, message):
	client = storage.get_client(message.from_user)
	message.client = client


@bot.middleware_handler(update_types=['callback_query'])
def middleware_handler_callback_query(bot_instance, call):
	try:
		parsed_data = json.loads(call.data)
	except (TypeError, json.JSONDecodeError):
		parsed_data = {}

	call.parsed_data = parsed_data

	# Подгружаем клиента только для команды с расписанием.
	if 'group_name' in parsed_data.keys() or 'faculty' in parsed_data.keys():
		client = storage.get_client(call.from_user)
		call.client = client


@bot.message_handler(commands=['start', 'старт'])
def start(message):
	text, markup = cmd_start()
	text += '\n\n' + L10n.get('start.menu')
	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['menu', 'меню'])
def menu(message):
	text, markup = cmd_start()
	text = L10n.get('start.menu')
	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('menu'))
def callback_query_schedule_groups(call):
	text, markup = cmd_start()
	text = L10n.get('start.menu')
	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.message_handler(regexp='расписание')
@bot.message_handler(commands=['raspisanie', 'расписание'])
def schedule_select_group(message):
	client = message.client
	subscribe_schedule_groups = client.get('schedule_groups', [])

	if not subscribe_schedule_groups:
		text, markup = cmd_schedule_groups(include_teacher=True)
		bot.send_message(message.chat.id, text, reply_markup=markup)
		return False

	group_name = subscribe_schedule_groups[0]

	day = CollegeScheduleAbc.get_weekday()

	schedule = storage.get_schedule(date=day)
	if not schedule:
		text = L10n.get('schedule.not_found').format(
			group_name=group_name,
			date=day.strftime('%d.%m.%y')
		)

		bot.edit_message_text(text, message.chat.id, message.id, reply_markup=message.reply_markup)

		return False

	text, markup = cmd_schedule_group(schedule, group_name, subscribe_schedule_groups, day, include_menu_button=True)

	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('faculty') or call.parsed_data.get('group_name'))
def callback_query_schedule_groups(call):
	faculty = call.parsed_data.get('faculty', None)
	group_name = call.parsed_data.get('group_name', None)
	subscribe = call.parsed_data.get('subscribe', False)
	unsubscribe = call.parsed_data.get('unsubscribe', False)

	client = call.client
	subscribe_schedule_groups = client.get('schedule_groups', [])

	if group_name == 'my_group':
		if subscribe_schedule_groups:
			group_name = subscribe_schedule_groups[0]
			faculty = None
		else:
			group_name = None
			faculty = True

	if not group_name and (not faculty or faculty == True):
		text, markup = cmd_schedule_groups(include_teacher=True)
		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
		return False

	if faculty and type(faculty) == str and faculty not in Settings.GROUPS:
		bot.answer_callback_query(
			callback_query_id=call.id,
			text=L10n.get("schedule.faculty_not_found").format(faculty=faculty),
			show_alert=True
		)
		return False

	if not group_name:
		text, markup = cmd_schedule_groups(faculty=faculty)
		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
		return False

	if subscribe:
		markup = InlineKeyboardMarkup()

		markup.row(
			InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'group_name': group_name}))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
		)

		text = L10n.get("schedule.subscribe.alert").format(group_name=group_name)
		bot.answer_callback_query(call.id, text, show_alert=True)

		text = L10n.get("schedule.subscribe").format(group_name=group_name)
		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)

		client = call.client
		client['schedule_groups'] = [group_name]
		storage.save_client(call.from_user, client)

		return False

	if unsubscribe:
		markup = InlineKeyboardMarkup()

		markup.row(
			InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'group_name': group_name}))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
		)

		text = L10n.get("schedule.unsubscribe.alert").format(group_name=group_name)
		bot.answer_callback_query(call.id, text, show_alert=True)

		text = L10n.get("schedule.unsubscribe").format(group_name=group_name)
		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)

		client = call.client
		client['schedule_groups'] = []
		storage.save_client(call.from_user, client)

		return False

	day = CollegeScheduleAbc.get_weekday()

	schedule = storage.get_schedule(date=day)
	if not schedule:
		text = L10n.get('schedule.not_found').format(
			group_name=group_name,
			date=day.strftime('%d.%m.%y')
		)

		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=call.message.reply_markup)

		return False

	text, markup = cmd_schedule_group(schedule, group_name, subscribe_schedule_groups, day)

	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('teacher'))
def callback_query_schedule_teachers(call):
	bot.edit_message_text(
		chat_id=call.message.chat.id,
		message_id=call.message.id,
		text='Отправьте фамилию и инициалы преподавателя, как указано в расписании.\nПример: Иванов И И',
		reply_markup=None
	)
	#bot.register_next_step_handler(call.message, callback_text_schedule_select_teacher)


@bot.message_handler(regexp='справка')
@bot.message_handler(commands=['spravka', 'справка'])
def docs(message):
	text, markup = cmd_docs(include_menu=False)

	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['зп'])
def zp_pdf_gen(message):
	client = message.client
	text = message.text

	try:
		args = text.split(' ')
		if 'запомни' in text:
			pattern = re.compile(r'^([А-Я]{1,2}[0-9]{1,2}\-[0-9]{2})?', flags=re.IGNORECASE)
			match = re.fullmatch(pattern, args[2])
			if not match:
				logger.debug(match)
				bot.send_message(message.chat.id, 'Ошибка в группе.')
				return False

			client['_zp_value_group'] = args[2]
			client['_zp_value_fio'] = ' '.join(args[3:])
			storage.save_client(message.from_user, client)
			bot.send_message(message.chat.id, 'Сохранено.')
			return False

		from_date = str(args[1])
		to_date = str(args[2])
		people = int(args[3])
	except Exception:
		logger.error('error', exc_info=True)
		bot.send_message(message.chat.id, 'Ошибка в аргументах.\nПример для заявки с 29 ноября по 3 декабря на 7 человек: <code>/зп 29.11.2021 03.12.2021 7</code>\n\nЗапомнить группу и ФИО: <code>/зп запомни И32-19 Романова Н. С.</code>')
		return False

	body = [
		[110, 10, 'Заместителю директора ГБПОУ КБТ'],
		[110, 16, 'Воробьевой О. Б.'],
		[110, 21, 'От куратора'],
		[110, 26, '%fio%'],
		[110, 31, 'Группы %group%'],
		[95, 70, 'Заявка'],
		[15, 90, 'В период с %from_date% года по %to_date% года'],
		[15, 96, 'группа %group% будет питаться в количестве %people%.'],
		[130, 130, '__________ / %fio%'],
		[15, 130, '%from_date%']
	]

	placeholders = dict()
	placeholders['fio'] = client.get('_zp_value_fio', 'Куратор')
	placeholders['group'] = client.get('_zp_value_group', 'Группа')
	placeholders['from_date'] = from_date
	placeholders['to_date'] = to_date
	placeholders['people'] = '{} человек'.format(people)

	try:
		for placeholder in ['from_date', 'to_date']:
			dt = datetime.datetime.strptime(placeholders[placeholder], '%d.%m.%y')
			date = dt.strftime('«%d» %B %Y').split(' ')
			date[1] = L10n.get("months.{month}".format(month=date[1]))
			date = ' '.join(date)
			placeholders[placeholder] = date
	except ValueError:
		bot.send_message(message.chat.id, 'Ошибка в дате.\nПример даты: <code>01.12.21</code>')
		return False

	pdf = fpdf.FPDF()
	pdf.add_page()

	pdf.add_font('DejaVu', '', 'assets/DejaVuSansCondensed.ttf', uni=True)
	pdf.set_font('DejaVu', '', 15)

	for line in body:
		txt = line[2]

		for placeholder, placeholder_value in placeholders.items():
			txt = txt.replace(f'%{placeholder}%', placeholder_value.strip().replace('\n', ''))

		pdf.text(x=float(line[0]), y=float(line[1]), txt=txt)

	pdf_file = 'assets/upload/{} {}-{} {}.pdf'.format(
		placeholders['group'], from_date, to_date, placeholders['fio']
	)

	pdf.output(pdf_file, 'F')

	with open(pdf_file, 'rb') as f:
		bot.send_document(message.chat.id, data=f)
		f.close()


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('docs'))
def callback_query_docs(call):
	docs = call.parsed_data.get('docs', None)

	text = docs
	markup = get_menu_markup()

	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('faq') is not None)
def callback_query_faq(call):
	faq = call.parsed_data.get('faq', 'home')

	text, markup = cmd_faq(faq=faq, include_menu=True)

	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('abiturient'))
def callback_query_abiturient(call):
	text, markup = cmd_abiturient()

	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('contacts'))
def callback_query_contacts(call):
	contacts = call.parsed_data.get('contacts', None)

	if contacts == 'address':
		text = L10n.get('contacts.address')
		markup = InlineKeyboardMarkup()

		markup.row(
			InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'contacts': True}))
		)
	elif contacts == 'social_networks':
		text = L10n.get('contacts.social_networks')
		markup = InlineKeyboardMarkup()

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.social_networks.telegram.button'), url=L10n.get('contacts.social_networks.telegram.button.link'))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.social_networks.vk.button'), url=L10n.get('contacts.social_networks.vk.button.link')),
			InlineKeyboardButton(L10n.get('contacts.social_networks.facebook.button'), url=L10n.get('contacts.social_networks.facebook.button.link'))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.social_networks.instagram.button'), url=L10n.get('contacts.social_networks.instagram.button.link'))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.social_networks.website.button'), url=L10n.get('contacts.social_networks.website.button.link'))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
		)
	else:
		text = L10n.get('contacts')
		markup = InlineKeyboardMarkup()

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.address.button'), callback_data=json.dumps({'contacts': 'address'}))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.virtual_tour.button'), url=L10n.get('contacts.virtual_tour.button.link'))
		)

		markup.row(
			InlineKeyboardButton(L10n.get('contacts.staff.button'), url=L10n.get('contacts.staff.button.link'))
		)
		markup.row(
			InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
		)

	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_debug(call):
	logger.debug('Не смог обработать событие с клавиатуры, очищаю это сообщение.')

	logger.debug(f'Call: {call}')
	logger.debug(f'Call data: {call.data}')
	logger.debug(f'Call parsed data: {call.parsed_data}')

	bot.edit_message_text('&#10071; Возникла ошибка, попробуйте еще раз.', call.message.chat.id, call.message.id, reply_markup=None)
