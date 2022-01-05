# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import telebot
import threading
import fpdf

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from utils import *

logger = init_logger()
logger.info("Initializing..")

try:
	logger.info("Initializing storage..")
	storage = Storage(Settings.MONGO, Settings.MONGO_DATABASE, Settings.COLLECTIONS)
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


def run_threaded(name, func):
	job_thread = threading.Thread(target=func)
	job_thread.setName(f'{name}Thread')
	job_thread.start()


def bot_polling():
	try:
		while True:
			try:
				me = bot.get_me()
				logger.info('Logged as {} ({})'.format(me.first_name, me.username))
				logger.info("Starting bot polling.")
				bot.enable_save_next_step_handlers(delay=3)
				bot.load_next_step_handlers()
				bot.polling(none_stop=True, interval=Settings.BOT_INTERVAL, timeout=Settings.BOT_TIMEOUT)
			except Exception as ex:
				logger.error(f"Bot polling failed, restarting in {Settings.BOT_TIMEOUT} sec.", exc_info=True)
				bot.stop_polling()
				time.sleep(Settings.BOT_TIMEOUT)
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
					time.sleep(t / 2)
					continue

				articles = CollegeScheduleAbc.get_articles(articles)

				for article in articles:
					date = article.get('date')
					if not date:
						continue

					path = article.get('link')

					time_diff = datetime.datetime.today() - date
					if time_diff.total_seconds() > 86400:
						logger.debug(f'Schedule polling, {date} skipped')
						continue

					article_groups = g.parse_article(path)

					article['data'] = article_groups

					storage.save_schedule(article)
			except Exception:
				logger.debug(article)
				logger.error('Schedule polling loop crashed', exc_info=True)

			time.sleep(t)
	except Exception:
		logger.error('Schedule polling loop crashed', exc_info=True)


def schedule_notify(notify_teachers=False, next_day=True):
	t = Settings.SCHEDULE_NOTIFY_PAUSE_TIME

	while True:
		today = datetime.datetime.today()

		# todo: А если в пятницу расписание не опубликовали?
		if today.isoweekday() >= 6:
			logger.info(f'Рассылка отменена, по выходным рассылка не отправляется.')
			break  # Ok.

		if today.hour >= 23:
			logger.error(f'Рассылка отменена, позже 11 часов рассылка не отправляется.')
			break  # Fail.

		day = CollegeScheduleAbc.get_weekday(next_day=next_day)

		schedule = storage.get_schedule(date=day)
		if not schedule:
			logger.debug(f'storage.get_schedule: {schedule}')
			logger.error(f'Рассылка перенесена, нет расписания на {day}.')
			logger.info(f'Повторная попытка через {t / 60} мин.')
			time.sleep(t)
			continue  # Try again.

		clients = storage.get_clients()
		if not clients:
			logger.error(f'Рассылка перенесена, нет получателей.')
			logger.info(f'Повторная попытка через {t / 60} мин.')
			time.sleep(t)
			continue  # Try again.

		notify_clients = {}

		subscribe_key = 'schedule_teachers' if notify_teachers else 'schedule_groups'
		for client in clients:
			client_id = client.get_id()

			subscribe_values = client.get(subscribe_key, [])

			if not subscribe_values:
				continue

			for subscribe_value in subscribe_values:
				if subscribe_value not in notify_clients:
					notify_clients[subscribe_value] = []

				if subscribe_value not in notify_clients[subscribe_value]:
					notify_clients[subscribe_value].append(client_id)

		for key in notify_clients.keys():
			if notify_teachers:
				text, markup = cmd_schedule_teacher(schedule, key, [key], day, include_back_button=False)
			else:
				text, markup = cmd_schedule_group(schedule, key, [key], day, include_back_button=False)

			notify_clients_ids = notify_clients.get(key, [])
			for client_id in notify_clients_ids:
				try:
					bot.send_message(client_id, text, reply_markup=markup)
				except Exception:
					logger.error(f'Ошибка при отправке сообщения клиенту <{client_id}>', exc_info=True)

		logger.debug('Рассылка завершена.')
		break  # OK.


def schedule_notify_students(next_day=True):
	schedule_notify(notify_teachers=False, next_day=next_day)


def schedule_notify_teachers(next_day=True):
	schedule_notify(notify_teachers=True, next_day=next_day)


def console():
	while True:
		try:
			try:
				cmd_args = input().split(' ')
			except EOFError:
				continue

			cmd = cmd_args[0]
			if not cmd:
				continue

			if cmd == "notify":
				if len(cmd_args) != 3:
					logger.info("notify <type: students|teachers> <next day: true|false>")
					continue

				notify_type = cmd_args[1]
				if notify_type not in ["students", "teachers"]:
					logger.error(f"Unknown arg {notify_type} Allowed: students, teachers")
					continue

				notify_teachers = True if cmd_args[1] == "teachers" else False
				next_day = True if cmd_args[2] else False

				schedule_notify(notify_teachers=notify_teachers, next_day=next_day)
			else:
				logger.info("Command not found")
		except Exception:
			logger.error("Exception in console", exc_info=True)


@bot.middleware_handler(update_types=['message'])
def middleware_handler_message(bot_instance, message):
	client = storage.get_client(message.from_user)
	message.client = client

	try:
		args = message.text.split(' ')
		cmd = args[0][1:] if args[0][0] == '/' else None

		if cmd:
			del args[0]

		text_args = ' '.join(args)
	except (IndexError, AttributeError):
		args = []
		cmd = None
		text_args = ''

	message.args = args
	message.text_args = text_args
	message.cmd = cmd


@bot.middleware_handler(update_types=['callback_query'])
def middleware_handler_callback_query(bot_instance, call):
	try:
		parsed_data = json.loads(call.data)
	except (TypeError, json.JSONDecodeError):
		parsed_data = {}

	call.parsed_data = parsed_data

	# Подгружаем клиента только для команды с расписанием.
	cmds = ['group_name', 'faculty', 'teacher', 'schedule', 'menu']

	for cmd in cmds:
		if cmd in parsed_data:
			client = storage.get_client(call.from_user)
			call.client = client
			break


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
def callback_query_menu(call):
	text, markup = cmd_start()
	text = L10n.get('start.menu')
	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.message_handler(regexp='расписание')
@bot.message_handler(commands=['raspisanie', 'расписание'])
def schedule(message):
	client = message.client
	subscribe_groups = client.get('schedule_groups', [])
	subscribe_teachers = client.get('schedule_teachers', [])

	if not subscribe_groups and not subscribe_teachers:
		text, markup = cmd_schedule(include_teacher=True)
		bot.send_message(message.chat.id, text, reply_markup=markup)
		return False

	group_name = subscribe_groups[0] if subscribe_groups else None
	teacher = subscribe_teachers[0] if subscribe_teachers else None

	day = CollegeScheduleAbc.get_weekday()
	schedule = storage.get_schedule(date=day)
	if not schedule:
		text = L10n.get('schedule.not_found').format(date=day.strftime('%d.%m.%y'))

		markup = InlineKeyboardMarkup()
		markup.row(
			InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
		)

		bot.send_message(message.chat.id, text, reply_markup=markup)

		return False

	text = ''
	link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None

	markup = InlineKeyboardMarkup()
	if group_name:
		text_group, button = cmd_schedule_group(schedule, group_name, subscribe_groups, day, return_unsubscribe_button=True)
		text += text_group
		markup.row(button)

	if teacher:
		text_teacher, button = cmd_schedule_teacher(schedule, teacher, subscribe_teachers, day, include_head=(True if not group_name else False), return_unsubscribe_button=True)
		if text:
			text += '\n\n'
		text += text_teacher
		markup.row(button)

	markup = add_schedule_buttons(markup, link, True, True)

	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('faculty') or call.parsed_data.get('group_name') or call.parsed_data.get('schedule'))
def callback_query_schedule(call):
	show_subscribe = True if (call.parsed_data.get('group_name') is True or call.parsed_data.get('schedule')) else False
	faculty = call.parsed_data.get('faculty')
	group_name = call.parsed_data.get('group_name')
	teacher = None
	subscribe = call.parsed_data.get('subscribe', False)
	unsubscribe = call.parsed_data.get('unsubscribe', False)

	client = call.client
	subscribe_groups = client.get('schedule_groups', [])
	subscribe_teachers = client.get('schedule_teachers', [])

	if show_subscribe:
		group_name = subscribe_groups[0] if subscribe_groups else None
		faculty = None if (subscribe_groups and subscribe_teachers) else True
		teacher = subscribe_teachers[0] if subscribe_teachers else None

	if not group_name and (not faculty or faculty is True) and not teacher:
		text, markup = cmd_schedule(include_teacher=True)
		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
		return False

	if faculty and type(faculty) == str and faculty not in Settings.GROUPS:
		bot.answer_callback_query(
			text=L10n.get("schedule.faculty_not_found").format(faculty=faculty),
			callback_query_id=call.id, show_alert=True
		)
		return False

	if not group_name and not teacher:
		text, markup = cmd_schedule(faculty=faculty)
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
		text = L10n.get('schedule.not_found').format(date=day.strftime('%d.%m.%y'))

		markup = InlineKeyboardMarkup()
		markup.row(
			InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
		)

		bot.send_message(call.message.chat.id, text, reply_markup=markup)

		return False

	text = ''
	link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None

	markup = InlineKeyboardMarkup()
	if group_name:
		text_group, button = cmd_schedule_group(schedule, group_name, subscribe_groups, day, return_unsubscribe_button=True)
		text += text_group
		markup.row(button)

	if teacher:
		text_teacher, button = cmd_schedule_teacher(schedule, teacher, subscribe_teachers, day, include_head=(True if not group_name else False), return_unsubscribe_button=True)
		if text:
			text += '\n\n'
		text += text_teacher
		markup.row(button)

	markup = add_schedule_buttons(markup, link, True, True)

	bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('teacher'))
def callback_query_schedule_by_teacher(call):
	client = call.client
	teacher = call.parsed_data.get('teacher')
	unsubscribe = call.parsed_data.get('unsubscribe', False)

	if teacher == 'cancel':
		bot.clear_step_handler(call.message)
		markup = InlineKeyboardMarkup()
		markup.row(
			InlineKeyboardButton(L10n.get('schedule.by_teacher.button'), callback_data=json.dumps({'teacher': True}))
		)
		markup.row(
			InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
		)
		bot.edit_message_text(L10n.get('schedule.by_teacher.cancel'), call.message.chat.id, call.message.id, reply_markup=markup)

		return False

	if unsubscribe:
		markup = InlineKeyboardMarkup()
		markup.row(
			InlineKeyboardButton(L10n.get('schedule.by_teacher.button'), callback_data=json.dumps({'teacher': True}))
		)
		markup.row(
			InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
		)
		bot.edit_message_text(L10n.get('schedule.by_teacher.unsubscribe'), call.message.chat.id, call.message.id, reply_markup=markup)

		client['schedule_teachers'] = []
		storage.save_client(call.from_user, client)

		return False

	if client.get('schedule_teachers'):
		teacher = client.get('schedule_teachers', [])[0]

		day = CollegeScheduleAbc.get_weekday(next_day=False)
		schedule = storage.get_schedule(date=day)

		text, _ = cmd_schedule_teacher(schedule, teacher, [], day, include_back_button=False)
		text += '\n\n' + L10n.get('schedule.by_teacher.status.subscribed').format(teacher=teacher)

		markup = InlineKeyboardMarkup()

		markup.row(
			InlineKeyboardButton(
				L10n.get('schedule.by_teacher.unsubscribe.button').format(teacher=teacher),
				callback_data=json.dumps({'teacher': True, 'unsubscribe': True})
			)
		)
		markup.row(
			InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
		)

		bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
	else:
		bot.register_next_step_handler(call.message, schedule_by_teacher_start, origin_call=call)

		markup = InlineKeyboardMarkup()
		markup.row(
			InlineKeyboardButton(L10n.get('schedule.by_teacher.cancel.button'), callback_data=json.dumps({'teacher': 'cancel'}))
		)

		bot.edit_message_text(L10n.get('schedule.by_teacher'), call.message.chat.id, call.message.id, reply_markup=markup)


def schedule_by_teacher_start(message, origin_call=None):
	pattern = re.compile(r'(?P<l>[А-Яа-я\-]+)[ ]?(?P<f>[А-Яа-я]+)?(\.)?[ ]?((?P<m>[А-Яа-я]+)(\.)?)', flags=re.IGNORECASE)

	find_teacher = message.text_args

	find_teacher = re.search(pattern, find_teacher)
	if not find_teacher:
		bot.register_next_step_handler(message, schedule_by_teacher_start)
		bot.delete_message(message.chat.id, message.id)

		if origin_call:
			bot.answer_callback_query(origin_call.id, L10n.get('schedule.by_teacher.subscribe.incorrect_fio.alert'), show_alert=True)
		else:
			bot.send_message(message.chat.id, L10n.get('schedule.by_teacher.subscribe.incorrect_fio'))

		return False

	n_last = find_teacher.group('l')
	n_first = find_teacher.group('f')
	n_middle = find_teacher.group('m')

	teacher = []
	if type(n_last) == str:
		teacher.append(n_last.lower().title())
	if type(n_first) == str:
		teacher.append(n_first[0].upper())
	if type(n_middle) == str:
		teacher.append(n_middle[0].upper())

	teacher = ' '.join(teacher)

	client = message.client
	client['schedule_teachers'] = [teacher]
	storage.save_client(message.from_user, client)

	day = CollegeScheduleAbc.get_weekday(next_day=False)
	schedule = storage.get_schedule(date=day)

	text, _ = cmd_schedule_teacher(schedule, teacher, [], day, include_back_button=False)
	text += '\n\n' + L10n.get('schedule.by_teacher.subscribe').format(teacher=teacher)

	markup = InlineKeyboardMarkup()
	markup.row(
		InlineKeyboardButton(
			L10n.get('schedule.by_teacher.unsubscribe.button').format(teacher=teacher),
			callback_data=json.dumps({'teacher': True, 'unsubscribe': True})
		)
	)
	markup.row(
		InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
	)

	bot.send_message(message.chat.id, text, reply_markup=markup)
	bot.delete_message(message.chat.id, message.id)


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
			InlineKeyboardButton(L10n.get('contacts.social_networks.vk.button'), url=L10n.get('contacts.social_networks.vk.button.link')),
			InlineKeyboardButton(L10n.get('contacts.social_networks.facebook.button'), url=L10n.get('contacts.social_networks.facebook.button.link')),
			InlineKeyboardButton(L10n.get('contacts.social_networks.instagram.button'), url=L10n.get('contacts.social_networks.instagram.button.link')),
			InlineKeyboardButton(L10n.get('contacts.social_networks.telegram.button'), url=L10n.get('contacts.social_networks.telegram.button.link'))
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


@bot.message_handler(commands=['auth'])
def auth(message):
	client = message.client

	if not client.get('phone_number'):
		text = 'Вход для студентов.'

		markup = ReplyKeyboardMarkup(one_time_keyboard=True)
		markup.add(KeyboardButton(text='🔑 Войти', request_contact=True))
	else:
		text, markup = cmd_auth(message.chat.id)

	bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('auth') is not None)
def callback_query_auth(call):
	client = call.client

	if not client.get('phone_number'):
		text = L10n.get('auth.students')

		markup = ReplyKeyboardMarkup(one_time_keyboard=True)
		markup.add(KeyboardButton(text=L10n.get('auth.students.button'), request_contact=True))
	else:
		text, markup = cmd_auth(call.message.chat.id)

	bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.message_handler(content_types=['contact'])
def callback_query_contact(message):
	if message.contact is not None:
		client = message.client
		contact = message.contact

		client['phone_number'] = get_phone(contact.phone_number)
		storage.save_client(message.from_user, client)

		bot.delete_message(message.chat.id, message.id)
		if message.reply_to_message:
			if message.reply_to_message.from_user.is_bot:
				bot.delete_message(message.chat.id, message.reply_to_message.id)

		text, markup = cmd_auth(message.chat.id)

		bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
	logger.debug('Событие с кнопки не обработано. Сообщение с клавиатурой удалено.')

	logger.debug(f'Call: {call}')
	logger.debug(f'Call data: {call.data}')
	logger.debug(f'Call parsed data: {call.parsed_data}')
	logger.debug(f'Chat id: {call.message.chat.id}')

	markup = InlineKeyboardMarkup()
	markup.row(
		InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
	)

	bot.edit_message_text(L10n.get('error.callback_query'), call.message.chat.id, call.message.id, reply_markup=markup)
