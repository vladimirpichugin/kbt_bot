# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import json
import re

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from operator import itemgetter

from .helpers import init_logger, get_fast_auth_url
from .json import Json

from settings import Settings

logger = init_logger()

logger.info("Initializing localization..")
L10n = Json(Settings.L10N_RU_FILE)


def cmd_start():
    text = L10n.get("start")

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.schedule'), callback_data=json.dumps({'schedule': True}))
    )
    #markup.row(
    #    InlineKeyboardButton(L10n.get('start.button.staff'), callback_data=json.dumps({'staff': True}))
    #)

    #markup.row(
    #    InlineKeyboardButton(L10n.get('start.button.docs.student_proof'), callback_data=json.dumps({'docs': 'student_proof'}))
    #)

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.abiturient'), callback_data=json.dumps({'abiturient': True}))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.website'), url=L10n.get('start.button.website.link')),
        InlineKeyboardButton(L10n.get('start.button.social_networks'), callback_data=json.dumps({'contacts': 'social_networks'})),
        InlineKeyboardButton(L10n.get('start.button.contacts'), callback_data=json.dumps({'contacts': True}))
    )

    return text, markup


def cmd_abiturient():
    text = L10n.get('abiturient')
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.button.faq'), callback_data=json.dumps({'faq': 'home'}))
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
        InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
    )

    return text, markup


def cmd_schedule(faculty=None, include_teacher=False, include_menu=True):
    text = L10n.get('schedule')
    markup = InlineKeyboardMarkup()

    if faculty:
        groups = Settings.GROUPS.get(faculty).get('GROUPS')

        for _ in range(0, len(groups), 4):
            buttons = [InlineKeyboardButton(group_name, callback_data=json.dumps({'group_name': group_name})) for group_name in
                       groups[_:_ + 4]]
            markup.row(*buttons)

        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
        )

        return text, markup

    for _ in range(0, len(Settings.GROUPS), 4):
        buttons = [InlineKeyboardButton(faculty, callback_data=json.dumps({'faculty': faculty})) for faculty in
                   list(Settings.GROUPS.keys())[_:_ + 4]]
        markup.row(*buttons)

    if include_teacher:
        markup.row(InlineKeyboardButton(L10n.get('schedule.by_teacher.button'), callback_data=json.dumps({'teacher': True})))

    if include_menu:
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
        )

    return text, markup


def cmd_docs(include_menu=True):
    text = L10n.get('docs')

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(L10n.get('docs.student_proof'), callback_data=json.dumps({'docs': 'student_proof'})))

    if include_menu:
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
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
            InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'abiturient': True}))
        )

    return text, markup


def get_menu_markup():
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
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

        if schedule_group_name != group_name:
            continue

        if not any(lessons):
            break

        for l in lessons:
            lesson_text = L10n.get('schedule.body.lesson')

            l_id = int(l.get('id'))
            l_time = group_time[l_id - 1]
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
            lesson_text = lesson_text.format(l_id, l_time, lesson)

            lessons_text.append(lesson_text)

        lessons_text = '\n\n'.join(lessons_text)

        break

    if lessons_text:
        text = ''

        if include_head:
            text = L10n.get('schedule.head').format(date=day_fmt) + '\n'

        text += L10n.get('schedule.body').format(
            group_name=group_name,
            room=room,
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
            callback_data=json.dumps({'group_name': group_name, 'unsubscribe': True}))
        markup.row(button)
    else:
        if not subscribe_schedule_groups:
            text += '\n\n' + L10n.get('schedule.subscribe.status.not_subscribed').format(group_name=group_name)
        button = InlineKeyboardButton(
            L10n.get('schedule.subscribe.button').format(group_name=group_name),
            callback_data=json.dumps({'group_name': group_name, 'subscribe': True}))
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
        room = info.get('room')

        if not any(lessons):
            continue

        for l in lessons:
            lesson_text = L10n.get('schedule.by_teacher.body.lesson')

            l_id = int(l.get('id'))
            l_time = schedule_group_time[l_id - 1]
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
            lesson_text = lesson_text.format(l_id, l_time, schedule_group_name, name, lesson)

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
            callback_data=json.dumps({'teacher': True, 'unsubscribe': True}))
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
            InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True})),
            InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
        )
    else:
        if include_back_button:
            markup.row(
                InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
            )

        if include_menu_button:
            markup.row(
                InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
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
