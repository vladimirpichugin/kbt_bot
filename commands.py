# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import os
import re
import datetime
import json
import fpdf

from operator import itemgetter

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from utils import get_fast_auth_url
from storage import *

from settings import Settings

from localization import L10n


def cmd_start():
    text = L10n.get("start")

    markup = InlineKeyboardMarkup()

    #markup.row(
    #    InlineKeyboardButton(L10n.get('start.button.profile'), callback_data='profile=y')
    #)

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.schedule'), callback_data='schedule=y'),
        InlineKeyboardButton(L10n.get('start.button.student_cert'), url=L10n.get('student_cert.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.abiturient'), callback_data='abiturient=y'),
        #InlineKeyboardButton(L10n.get('start.button.website'), url=L10n.get('start.button.website.link')),
        InlineKeyboardButton(L10n.get('start.button.social_networks'), callback_data='contacts=social_networks'),
        InlineKeyboardButton(L10n.get('start.button.contacts'), callback_data='contacts=y')
    )

    markup.row(
        InlineKeyboardButton(L10n.get('chat.button'), url=L10n.get('chat.button.link'))
    )

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.about_bot'), callback_data='about_bot=y')
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

    faculties = list()
    for faculty, faculty_o in Settings.GROUPS.items():
        if len(faculty_o.get('GROUPS', [])) == 1:
            group_name = faculty_o.get('GROUPS')[0]
            group_name_view = group_name

            if group_name == '??32-19':
                group_name_view = '???? ??32-19'

            faculties.append((group_name_view, 'group_name={}'.format(group_name)))
        else:
            faculties.append((faculty, 'faculty={}'.format(faculty)))

    for _ in range(0, len(faculties), 4):
        buttons = [InlineKeyboardButton(name, callback_data=callback_data) for name, callback_data in
                   faculties[_:_ + 4]]
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
    button = L10n.get('faq.{}.button'.format(faq))
    button_link = L10n.get('faq.{}.button.link'.format(faq))

    text = L10n.get('faq.body').format(
        q=q, a=a, qid=faq+1, qmax=questions+1
    )

    markup = InlineKeyboardMarkup()

    faq_previous = faq-1 if faq > 0 else questions
    faq_next = faq+1 if faq < questions else 0

    if button and button_link:
        markup.row(
            InlineKeyboardButton(button, url=button_link)
        )

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


def cmd_profile_edit(message, call, bot, edit=None):
    if call:
        message = call.message
        bot.delete_message(message.chat.id, message.id)
    return L10n.get('profile.disabled'), get_menu_markup()

    if not message:
        client = call.client
        message = call.message
    else:
        client = message.client

    student = storage.get_student_by_id(client.get('sid'))

    if not student:
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )
        return L10n.get('profile.student_not_found'), markup

    markup = InlineKeyboardMarkup()

    if edit in ('employer', 'employer_set', 'employer_l_moscow', 'employer_l_oblast', 'employer_l_other', 'bezdelnik', 'employer_1', 'employer_2'):
        text, markup = cmd_profile_edit_employer(message=message, call=call, bot=bot, edit=edit, client=client, student=student)
    elif edit in ('future', 'vuz_y', 'vuz_n', 'vuz_y_fulltime', 'vuz_y_parttime', 'army_y', 'army_y_already', 'army_n', 'army_n_other'):
        text, markup = cmd_profile_edit_future_plans(message=message, call=call, bot=bot, edit=edit, client=client, student=student)
    elif edit == 'email':
        text, markup = cmd_profile_edit_email(message=message, call=call, bot=bot, edit='email', client=client, student=student)
    elif edit == 'cancel':
        bot.clear_step_handler(call.message)
        text = L10n.get('profile.student.edit.cancel')
        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))
    elif not edit:
        text = L10n.get('profile.student.edit')

        text += cmd_profile_employer(student)
        text += cmd_profile_future_plans(student)

        # markup.row(InlineKeyboardButton(L10n.get('profile.edit.website.button'), url=get_fast_auth_url(message.from_user.id, 'edit_profile')))

        markup.row(InlineKeyboardButton(L10n.get('profile.student.edit.employer.button'), callback_data='profile=edit&edit=employer'))
        markup.row(InlineKeyboardButton(L10n.get('profile.student.edit.future_plans.button'), callback_data='profile=edit&edit=future'))

        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))
    else:
        text = L10n.get('profile.student.edit.error')
        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))

    return text, markup


def cmd_profile_edit_email(message, call, bot, edit, client, student):
    text = L10n.get('profile.student.edit.email')
    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=edit&edit=cancel'))
    )

    return text, markup


def cmd_profile_edit_future_plans(message, call, bot, edit, client, student):
    if call:
        message = call.message
        bot.delete_message(message.chat.id, message.id)
    return L10n.get('profile.disabled'), get_menu_markup()

    markup = InlineKeyboardMarkup()

    if edit in ('army_y', 'army_y_already', 'army_n', 'army_n_other'):
        old = {'future_plans_army': student.get('future_plans_army')}
        student['future_plans_army'] = edit
        new = {'future_plans_army': student.get('future_plans_army')}

        future_plans_army_history = student.get('future_plans_army_history', [])
        if type(future_plans_army_history) != list:
            future_plans_army_history = []

        future_plans_army_history.append({
            'old': old,
            'new': new,
            'timestamp': datetime.datetime.now().timestamp()
        })

        student['future_plans_army_history'] = future_plans_army_history

        storage.save_student(student)

        if edit == 'army_y':
            text = L10n.get('profile.student.edit.future_plans.army_y.yes')
        else:
            text = L10n.get('profile.student.edit.future_plans.vuz')

        markup.row(
            InlineKeyboardButton(L10n.get('yes.button'), callback_data='profile=edit&edit=vuz_y'),
            InlineKeyboardButton(L10n.get('no.button'), callback_data='profile=edit&edit=vuz_n')
        )

        markup.row(InlineKeyboardButton(L10n.get('back.button'), callback_data='profile=edit'))
    elif edit == 'vuz_y':
        text = L10n.get('profile.student.edit.future_plans.vuz_y')

        markup.row(
            InlineKeyboardButton(L10n.get('profile.student.edit.future_plans.vuz_y.full_time.button'), callback_data='profile=edit&edit=vuz_y_fulltime'),
            InlineKeyboardButton(L10n.get('profile.student.edit.future_plans.vuz_y.part_time.button'), callback_data='profile=edit&edit=vuz_y_parttime')
        )

        markup.row(InlineKeyboardButton(L10n.get('back.button'), callback_data='profile=edit'))
    elif edit in ('vuz_n', 'vuz_y_fulltime', 'vuz_y_parttime'):
        old = {
            'future_plans_full_time_education_basis': student.get('future_plans_full_time_education_basis'),
            'future_plans_part_time_education_basis': student.get('future_plans_part_time_education_basis')
        }

        if edit == 'vuz_y_fulltime':
            student['future_plans_full_time_education_basis'] = 1
            student['future_plans_part_time_education_basis'] = 0
        elif edit == 'vuz_y_parttime':
            student['future_plans_full_time_education_basis'] = 0
            student['future_plans_part_time_education_basis'] = 1
        elif edit == 'vuz_n':
            student['future_plans_full_time_education_basis'] = 0
            student['future_plans_part_time_education_basis'] = 0

        new = {
            'future_plans_full_time_education_basis': student.get('future_plans_full_time_education_basis'),
            'future_plans_part_time_education_basis': student.get('future_plans_part_time_education_basis')
        }

        future_plans_education_history = student.get('future_plans_education_history', [])
        if type(future_plans_education_history) != list:
            future_plans_education_history = []

        future_plans_education_history.append({
            'old': old,
            'new': new,
            'timestamp': datetime.datetime.now().timestamp()
        })

        student['future_plans_education_history'] = future_plans_education_history

        storage.save_student(student)

        text = L10n.get('profile.student.edit.future_plans.saved')
        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=edit'))
    else:
        if student.get('sex') == 1:
            text = L10n.get('profile.student.edit.future_plans.army')

            markup.row(
                InlineKeyboardButton(L10n.get('yes.button'), callback_data='profile=edit&edit=army_y'),
                InlineKeyboardButton(L10n.get('profile.student.edit.future_plans.army_y_already'), callback_data='profile=edit&edit=army_y_already')
            )

            markup.row(
                InlineKeyboardButton(L10n.get('profile.student.edit.future_plans.army_n'), callback_data='profile=edit&edit=army_n'),
                InlineKeyboardButton(L10n.get('profile.student.edit.future_plans.army_n_other'), callback_data='profile=edit&edit=army_n_other')
            )
        else:
            text = L10n.get('profile.student.edit.future_plans.vuz')

            markup.row(
                InlineKeyboardButton('????', callback_data='profile=edit&edit=vuz_y'),
                InlineKeyboardButton('??????', callback_data='profile=edit&edit=vuz_n')
            )

        markup.row(InlineKeyboardButton(L10n.get('back.button'), callback_data='profile=edit'))

    return text, markup


def cmd_profile_edit_employer(message, call, bot, edit, client, student):
    if call:
        message = call.message
        bot.delete_message(message.chat.id, message.id)
    return L10n.get('profile.disabled'), get_menu_markup()

    text = ''
    markup = InlineKeyboardMarkup()

    if edit == 'employer':
        text = L10n.get('profile.student.edit.employer')

        markup.row(
            InlineKeyboardButton(L10n.get('profile.student.edit.employer.no.button'), callback_data='profile=edit&edit=bezdelnik'),
            InlineKeyboardButton(L10n.get('profile.student.edit.cancel.button'), callback_data='profile=edit&edit=cancel')
        )

        bot.register_next_step_handler(message, cmd_profile_edit, bot=bot, call=call, edit='employer_set')
    elif edit == 'employer_set':
        client['employer'] = message.text
        storage.save_client(message.from_user, client)

        bot.delete_message(message.chat.id, message.id)
        bot.delete_message(call.message.chat.id, call.message.id)

        text = L10n.get('profile.student.edit.employer.location')

        markup.row(
            InlineKeyboardButton(L10n.get('profile.student.edit.employer.location.moscow.button'), callback_data='profile=edit&edit=employer_l_moscow'),
            InlineKeyboardButton(L10n.get('profile.student.edit.employer.location.oblast.button'), callback_data='profile=edit&edit=employer_l_oblast'),
            InlineKeyboardButton(L10n.get('profile.student.edit.employer.location.other.button'), callback_data='profile=edit&edit=employer_l_other'),
        )

        markup.row(InlineKeyboardButton(L10n.get('profile.student.edit.cancel.button'), callback_data='profile=edit&edit=cancel'))

        bot.send_message(call.message.chat.id, text=text, reply_markup=markup)

        return None, None
    elif edit in ('employer_l_moscow', 'employer_l_oblast', 'employer_l_other'):
        if edit == 'employer_l_moscow':
            client['employer_l'] = L10n.get('profile.student.edit.employer.location.moscow')
        elif edit == 'employer_l_oblast':
            client['employer_l'] = L10n.get('profile.student.edit.employer.location.oblast')
        else:
            client['employer_l'] = L10n.get('profile.student.edit.employer.location.other')

        storage.save_client(call.from_user, client)

        text = L10n.get('profile.student.edit.employer.speciality')

        markup.row(
            InlineKeyboardButton(L10n.get('yes.button'), callback_data='profile=edit&edit=employer_1'),
            InlineKeyboardButton(L10n.get('no.button'), callback_data='profile=edit&edit=employer_2'),
        )

        markup.row(InlineKeyboardButton(L10n.get('profile.student.edit.cancel.button'), callback_data='profile=edit&edit=cancel'))
    elif edit in ('bezdelnik', 'employer_1', 'employer_2'):
        old = {
            'potential_employer_1': student.get('potential_employer_1'),
            'potential_employer_location_1': student.get('potential_employer_location_1'),
            'potential_employer_2': student.get('potential_employer_2'),
            'potential_employer_location_2': student.get('potential_employer_location_2')
        }

        if edit == 'bezdelnik':
            bot.clear_step_handler(call.message)

            client['employer'] = None
            client['employer_l'] = None

            student['potential_employer_1'] = None
            student['potential_employer_location_1'] = None
            student['potential_employer_2'] = None
            student['potential_employer_location_2'] = None
        else:
            student['potential_employer_1' if edit == 'employer_1' else 'potential_employer_2'] = client.get('employer')
            student['potential_employer_location_1' if edit == 'employer_1' else 'potential_employer_location_2'] = client.get('employer_l')
            student['potential_employer_2' if edit == 'employer_1' else 'potential_employer_1'] = None
            student['potential_employer_location_2' if edit == 'employer_1' else 'potential_employer_location_1'] = None

        new = {
            'potential_employer_1': student['potential_employer_1'],
            'potential_employer_location_1': student['potential_employer_location_1'],
            'potential_employer_2': student['potential_employer_2'],
            'potential_employer_location_2': student['potential_employer_location_2']
        }

        potential_employer_history = student.get('potential_employer_history', [])
        if type(potential_employer_history) != list:
            potential_employer_history = []

        potential_employer_history.append({
            'old': old,
            'new': new,
            'timestamp': datetime.datetime.now().timestamp()
        })

        student['potential_employer_history'] = potential_employer_history

        storage.save_student(student)

        text = L10n.get('profile.student.edit.employer.saved')
        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))

    return text, markup


def cmd_profile(bot, message=None, call=None):
    if call:
        message = call.message
        bot.delete_message(message.chat.id, message.id)
    return L10n.get('profile.disabled'), get_menu_markup()

    if call:
        client = call.client
        message = call.message
    else:
        client = message.client

    phone_number = client.get('phone_number')

    if not phone_number:
        bot.delete_message(message.chat.id, message.id)
        markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add(KeyboardButton(text=L10n.get('profile.auth.button'), request_contact=True))
        bot.send_message(message.chat.id, text=L10n.get('profile.auth'), reply_markup=markup)
        return None, None

    if client.get('sid'):
        student = storage.get_student_by_id(client.get('sid'))
    else:
        student = storage.get_student_data_by_phone_number(phone_number)
        if student:
            client['sid'] = student.get_id()
            storage.save_client(message.from_user, client)

    if not student:
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y')
        )
        return L10n.get('profile.auth.student_not_found'), markup

    gid = student.get('gid') or L10n.get('profile.student.group.empty')
    speciality = student.get('speciality_name') or L10n.get('profile.student.speciality.empty')

    text = L10n.get('profile.student').format(
        name=student.get_name(include_middle_name=True),
        group=gid,
        speciality=speciality
    )

    text += cmd_profile_employer(student)
    text += cmd_profile_future_plans(student)

    markup = InlineKeyboardMarkup()

    markup.row(
        InlineKeyboardButton(L10n.get('profile.edit.button'), callback_data='profile=edit')
    )

    markup.row(InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y'))

    return text, markup


def cmd_profile_employer(student):
    text = ''
    employer_1 = student.get('potential_employer_1')
    employer_2 = student.get('potential_employer_2')

    if employer_1:
        employer_l_1 = student.get('potential_employer_location_1')
        if not employer_l_1:
            employer_l_1 = L10n.get('profile.student.employer.l.1.empty')

        text += L10n.get('profile.student.employer.1').format(employer_1, employer_l_1)

    if employer_2:
        employer_l_2 = student.get('potential_employer_location_2')
        if not employer_l_2:
            employer_l_2 = L10n.get('profile.student.employer.l.2.empty')

        text += L10n.get('profile.student.employer.2').format(employer_2, employer_l_2)

    if text:
        text = '\n\n' + L10n.get('profile.student.employer') + '\n' + text
    else:
        text = '\n\n' + L10n.get('profile.student.employer.empty')

    return text


def cmd_profile_future_plans(student):
    sex = student.get('sex')
    army = True if sex == 1 and student.get('future_plans_army') in (1, "army_y") else False
    fp_e = student.get('future_plans_full_time_education_basis') or student.get('future_plans_part_time_education_basis')

    text = ''
    if army and not fp_e:
        text = L10n.get('profile.student.future.army')
    elif army and fp_e:
        text = L10n.get('profile.student.future.army_vuz')
    elif not army and fp_e:
        text = L10n.get('profile.student.future.vuz')
    elif not army and not fp_e:
        if sex == 1:
            text = L10n.get('profile.student.future.no_army_no_vuz')
        else:
            text = L10n.get('profile.student.future.no_vuz')

    text = '\n\n' + L10n.get('profile.student.future') + '\n' + text

    return text


def cmd_about_bot():
    text = L10n.get('about_bot')

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(L10n.get('about_bot.button'), url=L10n.get('about_bot.button.link')))
    markup.row(InlineKeyboardButton(L10n.get('chat.button'), url=L10n.get('chat.button.link')))
    markup.row(InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y'))

    return text, markup


def cmd_chat():
    text = L10n.get('chat')

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(L10n.get('chat.no.button'), callback_data='chat=n'),
        InlineKeyboardButton(L10n.get('chat.button'), url=L10n.get('chat.button.link'))
    )

    return text, markup
