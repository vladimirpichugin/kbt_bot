# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import os
import re
import datetime
import json
import fpdf

from operator import itemgetter

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import get_fast_auth_url
from storage import *

from settings import Settings

from localization import L10n


def cmd_start():
    text = L10n.get("start")

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.schedule'), callback_data='schedule=y')
    )

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.abiturient'), callback_data='abiturient=y'),
        InlineKeyboardButton(L10n.get('start.button.student_cert'), callback_data='student_cert=y')
    )

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.website'), url=L10n.get('start.button.website.link')),
        InlineKeyboardButton(L10n.get('start.button.social_networks'), callback_data='contacts=social_networks'),
        InlineKeyboardButton(L10n.get('start.button.contacts'), callback_data='contacts=y')
    )

    return text, markup


def cmd_abiturient():
    text = L10n.get('abiturient')
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.button.faq'), callback_data='faq=home')
    )

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.1.button'), url=L10n.get('abiturient.1.button.link')),
        InlineKeyboardButton(L10n.get('abiturient.2.button'), url=L10n.get('abiturient.2.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.3.button'), url=L10n.get('abiturient.3.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.4.button'), url=L10n.get('abiturient.4.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
    )

    return text, markup


def cmd_schedule(faculty=None, include_teacher=False, include_menu=True):
    text = L10n.get('schedule')
    markup = InlineKeyboardMarkup()

    if faculty:
        groups = Settings.GROUPS.get(faculty).get('GROUPS')

        for _ in range(0, len(groups), 3):
            buttons = [InlineKeyboardButton(group_name, callback_data='group_name={}'.format(group_name)) for group_name in
                       groups[_:_ + 3]]
            markup.row(*buttons)

        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y')
        )

        return text, markup

    for _ in range(0, len(Settings.GROUPS), 4):
        buttons = [InlineKeyboardButton(faculty, callback_data='faculty={}'.format(faculty)) for faculty in
                   list(Settings.GROUPS.keys())[_:_ + 4]]
        markup.row(*buttons)

    if include_teacher:
        markup.row(InlineKeyboardButton(L10n.get('schedule.by_teacher.button'), callback_data='teacher=y'))

    if include_menu:
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )

    return text, markup


def cmd_student_cert(include_menu=True):
    text = L10n.get('student_cert')

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(L10n.get('student_cert.button'), url=L10n.get('student_cert.button.link')))

    if include_menu:
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )

    return text, markup


def cmd_faq(faq=None, include_menu=False):
    questions = 12

    if not faq or faq == 'home' or type(faq) != int:
        faq = 0

    q = L10n.get('faq.{}.q'.format(faq))
    a = L10n.get('faq.{}.a'.format(faq))

    text = L10n.get('faq.body').format(
        q=q, a=a, qid=faq+1, qmax=questions+1
    )

    markup = InlineKeyboardMarkup()

    faq_previous = faq-1 if faq > 0 else questions
    faq_next = faq+1 if faq < questions else 0

    markup.row(
        InlineKeyboardButton(L10n.get('previous.button'), callback_data=json.dumps({'faq': faq_previous})),
        InlineKeyboardButton(L10n.get('next.button'), callback_data=json.dumps({'faq': faq_next}))
    )

    if include_menu:
        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data='abiturient=y')
        )

    return text, markup


def get_menu_markup():
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
    )

    return markup


def cmd_schedule_group(schedule, group_name, subscribe_schedule_groups, day, include_head=True, include_back_button=True, include_menu_button=False, return_unsubscribe_button=False):
    day_fmt = day.strftime('%d.%m.%y')

    lessons_text = []
    link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None
    schedule_groups = schedule.get('data')
    room = None

    for schedule_group in schedule_groups:
        info = schedule_group.get('info', {})
        lessons = schedule_group.get('lessons', [])

        schedule_group_name = info.get('group').get('name')
        room = info.get('room')

        group_time = info.get('time')
        if not any(group_time):
            group_time = Settings.BELL_SCHEDULE_DEFAULT

        if schedule_group_name != group_name:
            continue

        if not any(lessons):
            break

        for l in lessons:
            lesson_text = L10n.get('schedule.body.lesson')

            l_id = int(l.get('id'))

            time_position = l_id - 1
            if len(group_time) >= l_id:
                l_time = group_time[time_position]
            else:
                l_time = ''

            name = l.get('name')
            teacher = l.get('teacher', {}).get('full_name')
            info = l.get('info')

            if info:
                info = info.title()

            lesson = [name]

            if teacher:
                lesson.append(teacher)

            if info:
                lesson.append(info)

            lesson = '\n'.join(lesson)
            lesson_text = lesson_text.format(l_id=l_id, l_time=l_time, lesson=lesson)

            lessons_text.append(lesson_text)

        lessons_text = '\n\n'.join(lessons_text)

        break

    if lessons_text:
        text = ''

        if include_head:
            text = L10n.get('schedule.head').format(date=day_fmt) + '\n'

        text += L10n.get('schedule.body').format(
            group_name=group_name,
            room=room if room else '',
            lessons=lessons_text
        )
    else:
        text = L10n.get('schedule.not_found.group').format(
            group_name=group_name,
            date=day_fmt
        )

    markup = InlineKeyboardMarkup()

    if group_name in subscribe_schedule_groups:
        text += '\n\n' + L10n.get('schedule.subscribe.status.subscribed').format(group_name=group_name)
        button = InlineKeyboardButton(
            L10n.get('schedule.unsubscribe.button').format(group_name=group_name),
            callback_data='unsubscribe=y&group_name={}'.format(group_name))
        markup.row(button)
    else:
        if not subscribe_schedule_groups:
            text += '\n\n' + L10n.get('schedule.subscribe.status.not_subscribed').format(group_name=group_name)
        button = InlineKeyboardButton(
            L10n.get('schedule.subscribe.button').format(group_name=group_name),
            callback_data='subscribe=y&group_name={}'.format(group_name))
        markup.row(button)

    markup = add_schedule_buttons(markup, link, include_menu_button, include_back_button)

    if return_unsubscribe_button:
        markup = button

    return text, markup


def cmd_schedule_teacher(schedule, teacher, subscribe_schedule_teachers, day, include_head=True, include_back_button=True, include_menu_button=False, return_unsubscribe_button=False):
    find_teacher = teacher.split(' ')[0]
    day_fmt = day.strftime('%d.%m.%y')

    lessons_items = []
    link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None
    schedule_groups = schedule.get('data')

    for schedule_group in schedule_groups:
        info = schedule_group.get('info', {})
        lessons = schedule_group.get('lessons', [])

        schedule_group_name = info.get('group').get('name')

        schedule_group_time = info.get('time')
        if not any(schedule_group_time):
            schedule_group_time = Settings.BELL_SCHEDULE_DEFAULT

        room = info.get('room')

        if not any(lessons):
            continue

        for l in lessons:
            lesson_text = L10n.get('schedule.by_teacher.body.lesson')

            l_id = int(l.get('id'))

            time_position = l_id - 1
            if len(schedule_group_time) >= l_id:
                l_time = schedule_group_time[time_position]
            else:
                l_time = ''

            name = l.get('name')
            info = l.get('info')
            raw = l.get('raw')

            if not re.search(find_teacher, raw):
                continue

            if info:
                info = info.title()

            lesson = []

            if info:
                lesson.append(info)
            elif room:
                lesson.append(room)

            lesson = '\n'.join(lesson)
            lesson_text = lesson_text.format(l_id=l_id, l_time=l_time, group_name=schedule_group_name, lesson=name, info=lesson)

            lessons_items.append((lesson_text, l_id))

    lessons_items = sorted(lessons_items, key=itemgetter(1))

    lessons_text = '\n\n'.join([item[0] for item in lessons_items])

    if lessons_text:
        text = ''

        if include_head:
            text = L10n.get('schedule.by_teacher.head').format(date=day_fmt) + '\n'

        text += L10n.get('schedule.by_teacher.body').format(
            teacher=teacher,
            lessons=lessons_text
        )
    else:
        text = L10n.get('schedule.by_teacher.not_found').format(
            teacher=teacher,
            date=day_fmt
        )

    markup = InlineKeyboardMarkup()

    button = None
    if teacher in subscribe_schedule_teachers:
        text += '\n\n' + L10n.get('schedule.by_teacher.status.subscribed').format(teacher=teacher)
        button = InlineKeyboardButton(
            L10n.get('schedule.by_teacher.unsubscribe.button').format(teacher=teacher),
            callback_data='teacher=y&unsubscribe=y')
        markup.row(button)

    markup = add_schedule_buttons(markup, link, include_menu_button, include_back_button)

    if return_unsubscribe_button and button:
        markup = button

    return text, markup


def add_schedule_buttons(markup, link, include_menu_button, include_back_button):
    if link:
        link += '?utm_source=telegram_bot&utm_medium=MosKBT_BOT'
        markup.row(
            InlineKeyboardButton(L10n.get('schedule.open_site.button'), url=link)
        )

    if include_back_button and include_menu_button:
        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y'),
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )
    else:
        if include_back_button:
            markup.row(
                InlineKeyboardButton(L10n.get('back.button'), callback_data='faculty=y')
            )

        if include_menu_button:
            markup.row(
                InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
            )

    return markup


def cmd_auth(uid):
    auth_url = get_fast_auth_url(uid)

    text = L10n.get('auth.students')
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('auth.students.button'), url=auth_url)
    )

    return text, markup


def cmd_zp(bot, message):
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
    except:
        bot.send_message(message.chat.id,
                         'Например, для заявки с 24 по 28 января на 10 человек: <code>/зп 24.01.22 28.01.22 10</code>\n\nЗапомнить группу и ФИО: <code>/зп запомни И32-19 Романова Н. С.</code>')
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

    pdf_file = '{} {}-{} {}.pdf'.format(
        placeholders['group'], from_date, to_date, placeholders['fio']
    )

    share_directory = os.path.join(os.getcwd(), 'share')

    if not os.path.exists(share_directory):
        os.makedirs(share_directory)

    pdf_file = os.path.join(share_directory, pdf_file)

    pdf.output(pdf_file, 'F')

    with open(pdf_file, 'rb') as f:
        bot.send_document(message.chat.id, data=f)
        f.close()
