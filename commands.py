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

    markup.row(
        InlineKeyboardButton(L10n.get('start.button.profile'), callback_data='profile=y')
    )

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

    if edit == 'employer':
        text = 'Отправьте название компании, в которой вы сейчас работаете.'

        markup.row(InlineKeyboardButton('Не работаю', callback_data='profile=edit&edit=bezdelnik'))
        markup.row(InlineKeyboardButton('Отмена', callback_data='profile=edit&edit=cancel'))

        bot.register_next_step_handler(message, cmd_profile_edit, bot=bot, call=call, edit='employer_set')
    elif edit == 'employer_set':
        client['employer'] = message.text
        storage.save_client(message.from_user, client)

        bot.delete_message(message.chat.id, message.id)
        bot.delete_message(call.message.chat.id, call.message.id)

        text = 'Где расположена компания?\n\n<i>Нам нужно знать, в каком городе компания платит налоги.</i>'

        markup.row(
            InlineKeyboardButton('Москва', callback_data='profile=edit&edit=employer_l_moscow'),
            InlineKeyboardButton('МО', callback_data='profile=edit&edit=employer_l_oblast'),
            InlineKeyboardButton('Другой', callback_data='profile=edit&edit=employer_l_other'),
        )

        markup.row(InlineKeyboardButton('Отмена', callback_data='profile=edit&edit=cancel'))

        bot.send_message(call.message.chat.id, text=text, reply_markup=markup)

        return None, None
    elif edit in ('employer_l_moscow', 'employer_l_oblast', 'employer_l_other'):
        if edit == 'employer_l_moscow':
            client['employer_l'] = 'Москва'
        elif edit == 'employer_l_oblast':
            client['employer_l'] = 'Московская область'
        else:
            client['employer_l'] = 'Другое'

        storage.save_client(call.from_user, client)

        text = 'Вы работаете по специальности?'

        markup.row(
            InlineKeyboardButton('Да', callback_data='profile=edit&edit=employer_1'),
            InlineKeyboardButton('Нет', callback_data='profile=edit&edit=employer_2'),
        )

        markup.row(InlineKeyboardButton('Отмена', callback_data='profile=edit&edit=cancel'))
    elif edit in ('bezdelnik', 'employer_1', 'employer_2'):
        old = {
            'potential_employer_1': student['potential_employer_1'],
            'potential_employer_location_1': student['potential_employer_location_1'],
            'potential_employer_2': student['potential_employer_2'],
            'potential_employer_location_2': student['potential_employer_location_2']
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
            student['potential_employer_1' if edit == 'employer_1' else 'potential_employer_2'] = client['employer']
            student['potential_employer_location_1' if edit == 'employer_1' else 'potential_employer_location_2'] = client['employer_l']
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

        text = 'Изменения сохранены.'
        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))
    elif edit == 'email':
        text = 'Редактируем почту.'
    elif edit == 'cancel':
        bot.clear_step_handler(call.message)
        text = 'Редактирование отменено.'
        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))
    else:
        text = 'Для редактирования Профиля используйте клавиатуру.'

        markup.row(InlineKeyboardButton('Место трудоустройства', callback_data='profile=edit&edit=employer'))

        markup.row(InlineKeyboardButton(L10n.get('profile.button'), callback_data='profile=y'))

    return text, markup


def cmd_profile(bot, message=None, call=None):
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
    #markup.row(InlineKeyboardButton(L10n.get('profile.edit.button'), url=get_fast_auth_url(message.from_user.id, 'edit_profile')))

    markup.row(
        InlineKeyboardButton('Изменить профиль', callback_data='profile=edit')
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
    text = ''
    sex = student.get('sex')
    army = student.get('future_plans_army')
    fp_e_full_time = student.get('future_plans_full_time_education_basis')
    fp_e_part_time = student.get('future_plans_full_time_education_basis')

    text += '\n\n' + L10n.get('profile.student.future') + '\n'

    if fp_e_full_time and fp_e_part_time:
        text += L10n.get('profile.student.future.vuz')
    elif fp_e_full_time:
        text += L10n.get('profile.student.future.vuz.full_time')
    elif fp_e_part_time:
        text += L10n.get('profile.student.future.vuz.part_time')

    if sex == 1 and army == 1:
        if fp_e_full_time or fp_e_part_time:
            text += '\n'
        text += L10n.get('profile.student.future.army')

    return text


def cmd_about_bot():
    text = L10n.get('about_bot')

    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(L10n.get('about_bot.button'), url=L10n.get('about_bot.button.link')))
    markup.row(InlineKeyboardButton(L10n.get('menu.button'), callback_data='menu=y'))

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
