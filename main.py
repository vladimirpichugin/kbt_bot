# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

import urllib.parse

from utils import *
from notify import *
from commands import *

logger.debug("Initializing telebot..")

telebot.apihelper.ENABLE_MIDDLEWARE = True

telebot.logger.removeHandler(telebot.logger.handlers[0])
telebot.logger.setLevel(level=logging.DEBUG if Settings.DEBUG_TELEBOT else logging.INFO)

telebot.logger.addHandler(get_logger_file_handler())
telebot.logger.addHandler(get_logger_stream_handler())

bot = telebot.TeleBot(Settings.BOT_TOKEN, parse_mode='html')


def bot_polling():
    try:
        while True:
            try:
                me = bot.get_me()
                logger.info("Logged as {} ({})".format(me.first_name, me.username))
                logger.info("Starting bot polling.")
                bot.enable_save_next_step_handlers(delay=3)
                bot.load_next_step_handlers()
                bot.polling(none_stop=True, interval=Settings.BOT_INTERVAL, timeout=Settings.BOT_TIMEOUT)
            except:
                logger.error(f"Bot polling failed, restarting in {Settings.BOT_TIMEOUT} sec.", exc_info=True)
                bot.stop_polling()
                time.sleep(Settings.BOT_TIMEOUT)
            else:
                bot.stop_polling()
                logger.info("Bot polling loop finished.")
                break
    except:
        logger.error("Bot polling loop crashed.", exc_info=True)


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
        call_data = call.data

        if call_data[0] == '{':  # Legacy.
            parsed_data = json.loads(call_data)
        else:
            parsed_data = urllib.parse.parse_qs(call_data)
            for key, value in parsed_data.items():
                value = value[0]
                if value == 'y':
                    value = True
                if value == 'n':
                    value = False
                parsed_data[key] = value

    except (TypeError, IndexError, ValueError, json.JSONDecodeError):
        parsed_data = {}

    call.parsed_data = parsed_data

    # Подгружаем клиента только при появлении аргументов.
    cmds = ['group_name', 'faculty', 'teacher', 'schedule']

    for cmd in cmds:
        if cmd in parsed_data:
            client = storage.get_client(call.from_user)
            call.client = client
            break


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('menu'))
def callback_query_menu(call):
    text, markup = cmd_start()
    text = L10n.get('start.menu')
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.message_handler(regexp='расписание')
@bot.message_handler(commands=['raspisanie', 'расписание'])
@bot.message_handler(func=lambda message: message.text_args == 'raspisanie')
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

    day = get_weekday()
    schedule = storage.get_schedule(date=day)
    if not schedule:
        text = L10n.get('schedule.not_found').format(date=day.strftime('%d.%m.%y'))

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )

        bot.send_message(message.chat.id, text, reply_markup=markup)

        return False

    text = ''
    link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None

    markup = InlineKeyboardMarkup()
    if group_name:
        text_group, button = cmd_schedule_group(schedule, group_name, subscribe_groups, day,
                                                return_unsubscribe_button=True)
        text += text_group
        markup.row(button)

    if teacher:
        text_teacher, button = cmd_schedule_teacher(schedule, teacher, subscribe_teachers, day,
                                                    include_head=(True if not group_name else False),
                                                    return_unsubscribe_button=True)
        if text:
            text += '\n\n'
        text += text_teacher
        markup.row(button)

    markup = add_schedule_buttons(markup, link, True, True)

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(
    func=lambda call: call.parsed_data.get('faculty') or call.parsed_data.get('group_name') or call.parsed_data.get(
        'schedule'))
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
            InlineKeyboardButton(L10n.get('back.button'), callback_data='group_name={}'.format(group_name))
        )

        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
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
            InlineKeyboardButton(L10n.get('back.button'), callback_data='group_name={}'.format(group_name))
        )

        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )

        text = L10n.get("schedule.unsubscribe.alert").format(group_name=group_name)
        bot.answer_callback_query(call.id, text, show_alert=True)

        text = L10n.get("schedule.unsubscribe").format(group_name=group_name)
        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)

        client = call.client
        client['schedule_groups'] = []
        storage.save_client(call.from_user, client)

        return False

    day = get_weekday()
    schedule = storage.get_schedule(date=day)
    if not schedule:
        text = L10n.get('schedule.not_found').format(date=day.strftime('%d.%m.%y'))

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )

        bot.send_message(call.message.chat.id, text, reply_markup=markup)

        return False

    text = ''
    link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None

    markup = InlineKeyboardMarkup()
    if group_name:
        text_group, button = cmd_schedule_group(schedule, group_name, subscribe_groups, day,
                                                return_unsubscribe_button=True)
        text += text_group
        markup.row(button)

    if teacher:
        text_teacher, button = cmd_schedule_teacher(schedule, teacher, subscribe_teachers, day,
                                                    include_head=(True if not group_name else False),
                                                    return_unsubscribe_button=True)
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
            InlineKeyboardButton(L10n.get('schedule.by_teacher.button'), callback_data='teacher=y')
        )
        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y')
        )
        bot.edit_message_text(L10n.get('schedule.by_teacher.cancel'), call.message.chat.id, call.message.id,
                              reply_markup=markup)

        return False

    if unsubscribe:
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(L10n.get('schedule.by_teacher.button'), callback_data='teacher=y')
        )
        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y')
        )
        bot.edit_message_text(L10n.get('schedule.by_teacher.unsubscribe'), call.message.chat.id, call.message.id,
                              reply_markup=markup)

        client['schedule_teachers'] = []
        storage.save_client(call.from_user, client)

        return False

    if client.get('schedule_teachers'):
        teacher = client.get('schedule_teachers', [])[0]

        day = get_weekday(next_day=False)
        schedule = storage.get_schedule(date=day)
        if not schedule:
            text = L10n.get('schedule.not_found').format(date=day.strftime('%d.%m.%y'))

            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
            )

            bot.send_message(call.message.chat.id, text, reply_markup=markup)

            return False

        text, _ = cmd_schedule_teacher(schedule, teacher, [], day, include_back_button=False)
        text += '\n\n' + L10n.get('schedule.by_teacher.status.subscribed').format(teacher=teacher)

        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton(
                L10n.get('schedule.by_teacher.unsubscribe.button').format(teacher=teacher),
                callback_data='teacher=y&unsubscribe=y'
            )
        )
        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y')
        )

        bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)
    else:
        bot.register_next_step_handler(call.message, schedule_by_teacher_start, origin_call=call)

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(L10n.get('schedule.by_teacher.cancel.button'), callback_data='teacher=cancel')
        )

        bot.edit_message_text(L10n.get('schedule.by_teacher'), call.message.chat.id, call.message.id,
                              reply_markup=markup)


def schedule_by_teacher_start(message, origin_call=None):
    pattern = re.compile(r'(?P<l>[А-Яа-я\-]+)[ ]?(?P<f>[А-Яа-я]+)?(\.)?[ ]?((?P<m>[А-Яа-я]+)(\.)?)',
                         flags=re.IGNORECASE)

    find_teacher = message.text_args

    find_teacher = re.search(pattern, find_teacher)
    if not find_teacher:
        bot.register_next_step_handler(message, schedule_by_teacher_start)
        bot.delete_message(message.chat.id, message.id)

        if origin_call:
            bot.answer_callback_query(origin_call.id, L10n.get('schedule.by_teacher.subscribe.incorrect_fio.alert'),
                                      show_alert=True)
        else:
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton(L10n.get('schedule.by_teacher.cancel.button'), callback_data='teacher=cancel')
            )

            bot.send_message(message.chat.id, L10n.get('schedule.by_teacher.subscribe.incorrect_fio'),
                             reply_markup=markup)

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

    day = get_weekday(next_day=False)
    schedule = storage.get_schedule(date=day)

    text, _ = cmd_schedule_teacher(schedule, teacher, [], day, include_back_button=False)
    text += '\n\n' + L10n.get('schedule.by_teacher.subscribe').format(teacher=teacher)

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            L10n.get('schedule.by_teacher.unsubscribe.button').format(teacher=teacher),
            callback_data='teacher=y&unsubscribe=y'
        )
    )
    markup.row(
        InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y')
    )

    bot.send_message(message.chat.id, text, reply_markup=markup)
    bot.delete_message(message.chat.id, message.id)


@bot.message_handler(regexp='справка')
@bot.message_handler(commands=['spravka', 'справка'])
def student_cert(message):
    text, markup = cmd_student_cert(include_menu=False)

    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('student_cert'))
def callback_query_student_cert(call):
    text, markup = cmd_student_cert(include_menu=True)

    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


@bot.message_handler(commands=['зп', 'zp'])
def zp_pdf_gen(message):
    cmd_zp(bot, message)


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
            InlineKeyboardButton(L10n.get('back.button'), callback_data='contacts=y')
        )
    elif contacts == 'social_networks':
        text = L10n.get('contacts.social_networks')
        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton(L10n.get('contacts.social_networks.vk.button'),
                                 url=L10n.get('contacts.social_networks.vk.button.link')),
            InlineKeyboardButton(L10n.get('contacts.social_networks.facebook.button'),
                                 url=L10n.get('contacts.social_networks.facebook.button.link')),
            InlineKeyboardButton(L10n.get('contacts.social_networks.instagram.button'),
                                 url=L10n.get('contacts.social_networks.instagram.button.link')),
            InlineKeyboardButton(L10n.get('contacts.social_networks.telegram.button'),
                                 url=L10n.get('contacts.social_networks.telegram.button.link'))
        )

        markup.row(
            InlineKeyboardButton(L10n.get('contacts.social_networks.website.button'),
                                 url=L10n.get('contacts.social_networks.website.button.link'))
        )

        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )
    else:
        text = L10n.get('contacts')
        markup = InlineKeyboardMarkup()

        markup.row(
            InlineKeyboardButton(L10n.get('contacts.address.button'), callback_data='contacts=address')
        )

        markup.row(
            InlineKeyboardButton(L10n.get('contacts.virtual_tour.button'),
                                 url=L10n.get('contacts.virtual_tour.button.link'))
        )

        markup.row(
            InlineKeyboardButton(L10n.get('contacts.staff.button'), url=L10n.get('contacts.staff.button.link'))
        )
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
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


@bot.callback_query_handler(func=lambda call: call.parsed_data.get('about_bot') is True)
def callback_query_about_bot(call):
    text, markup = cmd_about_bot()
    bot.edit_message_text(text, call.message.chat.id, call.message.id, reply_markup=markup)


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


@bot.message_handler(commands=['start', 'menu', 'старт', 'меню', 'help'])
def welcome(message):
    text, markup = cmd_start()

    if message.cmd in ['start', 'старт']:
        text += '\n\n' + L10n.get('start.menu')
    else:
        text = L10n.get('start.menu')

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
        InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
    )

    bot.edit_message_text(L10n.get('error.callback_query'), call.message.chat.id, call.message.id, reply_markup=markup)
