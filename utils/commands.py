# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import json
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from .helpers import init_logger
from .json import Json

from settings import Settings

logger = init_logger()

logger.info("Initializing localization..")
L10n = Json(Settings.L10N_RU_FILE)


def cmd_start():
    text = L10n.get("start")

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.schedule'), callback_data=json.dumps({'group_name': 'my_group'}))
    )

    # todo: Добавить поддержку получения расписания по ФИО.
    #markup.row(
    #    InlineKeyboardButton(L10n.get('start.button.docs.student_proof'), callback_data=json.dumps({'docs': 'student_proof'}))
    #)

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.abiturient'), callback_data=json.dumps({'abiturient': True})),
        InlineKeyboardButton(L10n.get('start.button.contacts'), callback_data=json.dumps({'contacts': True}))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.social_networks'), callback_data=json.dumps({'contacts': 'social_networks'})),
        InlineKeyboardButton(L10n.get('start.button.website'), url=L10n.get('start.button.website.link')),
    )

    return text, markup


def cmd_abiturient():
    text = L10n.get('abiturient')
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.button.faq'), callback_data=json.dumps({'faq': 'home'}))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.1.button'), url=L10n.get('abiturient.1.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.2.button'), url=L10n.get('abiturient.2.button.link')),
        InlineKeyboardButton(L10n.get('abiturient.3.button'), url=L10n.get('abiturient.3.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('abiturient.4.button'), url=L10n.get('abiturient.4.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
    )

    return text, markup


def cmd_schedule_groups(faculty=None, include_teacher=False, include_menu=True):
    markup = InlineKeyboardMarkup()

    if faculty:
        text = "Выберите группу."
        groups = Settings.GROUPS.get(faculty).get('GROUPS')

        for _ in range(0, len(groups), 4):
            buttons = [InlineKeyboardButton(group_name, callback_data=json.dumps({'group_name': group_name})) for group_name in
                       groups[_:_ + 4]]
            markup.row(*buttons)

        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
        )

        return text, markup

    text = "Выберите группу."

    for _ in range(0, len(Settings.GROUPS), 4):
        buttons = [InlineKeyboardButton(faculty, callback_data=json.dumps({'faculty': faculty})) for faculty in
                   list(Settings.GROUPS.keys())[_:_ + 4]]
        markup.row(*buttons)

    include_teacher = False
    if include_teacher:
        markup.row(InlineKeyboardButton('По преподавателю', callback_data=json.dumps({'teacher': True})))

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


def cmd_schedule_group(schedule, group_name, subscribe_schedule_groups, day, include_back_button=True, include_menu_button=False):
    day_fmt = day.strftime('%d.%m.%y')

    lessons_text = []
    link = Settings.DOMAIN + schedule.get('link') if schedule.get('link') else None
    groups = schedule.get('data')

    for group in groups:
        if group.get('group') != group_name:
            continue

        room = group.get('room')
        if room in ['ауд.', 'ауд']:  # todo: Заменить на регулярку
            room = ''

        lessons = group.get('lessons')

        if not any(lessons):
            break

        for lesson in lessons:
            if not lesson:
                continue

            if lesson[-1].lower() in ['ауд.', 'ауд']:  # todo: Заменить на регулярку
                del lesson[-1]

            lessons_text.append('\n'.join(lesson))
        lessons_text = '\n\n'.join(['<b>№ {}.</b> {}'.format(num + 1, value) for num, value in enumerate(lessons_text)])

        break

    if lessons_text:
        text = L10n.get('schedule.body').format(
            date=day_fmt,
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
        markup.row(
            InlineKeyboardButton(L10n.get('schedule.unsubscribe.button').format(group_name=group_name),
                                 callback_data=json.dumps({'group_name': group_name, 'unsubscribe': True}))
        )
    else:
        if not subscribe_schedule_groups:
            text += '\n\n' + L10n.get('schedule.subscribe.status.not_subscribed').format(group_name=group_name)
        markup.row(
            InlineKeyboardButton(L10n.get('schedule.subscribe.button').format(group_name=group_name),
                                 callback_data=json.dumps({'group_name': group_name, 'subscribe': True}))
        )

    if link:
        markup.row(
            InlineKeyboardButton(L10n.get('schedule.open_site.button'), url=link)
        )

    if include_back_button:
        markup.row(
            InlineKeyboardButton(L10n.get('back.button'), callback_data=json.dumps({'faculty': True}))
        )

    if include_menu_button:
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data=json.dumps({'menu': True}))
        )

    return text, markup
