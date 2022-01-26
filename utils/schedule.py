# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import re
import datetime
import requests
from bs4 import BeautifulSoup

from .data import ScheduleArticle
from .helpers import init_logger

logger = init_logger()


class CollegeScheduleGrabber:
    def __init__(self, domain, blog_path):
        self.domain = domain
        self.blog_path = blog_path
        self.pattern_head = re.compile(r'^(?P<f>([А-Я]{1,2}))(\s)?(?P<n>[0-9]{2})([\s\-])?(?P<y>[0-9]{2})\s(?P<r>.+)?', flags=re.IGNORECASE)

    def parse_articles(self) -> list:
        link = self.domain + self.blog_path

        blog_content = requests.get(link)

        soup = BeautifulSoup(blog_content.content, "html.parser")

        elements = soup.find("div", class_="kris-blogitem-all").find("ol").find_all("div", class_="item-body-h")

        articles = []
        for element in elements:
            try:
                item = element.find("a")

                text = item.text
                href = item.get("href")

                articles.append((text, href))
            except Exception:
                logger.error(f'parse_articles: Исключение при обработке элемента из блога', exc_info=True)

        logger.debug(f'parse_articles: {articles}')

        return articles

    def parse_article(self, article_path: str) -> list:
        link = self.domain + article_path

        schedule_content = requests.get(link)

        soup = BeautifulSoup(schedule_content.content, "html.parser")

        table_all = soup.find("div", class_="kris-post-item-txt").find_all("table")

        times = []
        for table_id, table in enumerate(table_all):
            table_times = []
            table_tbody = table.find("tbody")
            tr_all = table_tbody.find_all("tr")

            for tr_id, tr in enumerate(tr_all):
                td_all = tr.find_all("td")

                for c_r_i, rows in enumerate(td_all):
                    if c_r_i == 0 and tr_id == 0:
                        for i in range(0, 5):
                            if len(tr_all) <= i:
                                continue

                            time_line_td = tr_all[i].find_all("td")
                            time_line = time_line_td[c_r_i]
                            time_line_text = time_line.text.replace(u'\xa0', '').replace('\n', '').strip()

                            if not time_line_text:
                                continue

                            if 'время' in time_line_text:
                                continue

                            table_times.append(time_line_text)
            times.append(table_times)

        schedule = []
        for table_id, table in enumerate(table_all):
            table_tbody = table.find("tbody")
            tr_all = table_tbody.find_all("tr")

            for tr_id, tr in enumerate(tr_all):
                td_all = tr.find_all("td")

                for c_r_i, rows in enumerate(td_all):
                    row_lines = rows.find_all("p")
                    row_lines = [_.text for _ in row_lines]

                    for line_id, line in enumerate(row_lines):
                        regex_head = self.pattern_head.search(line)

                        if regex_head:
                            lessons = []
                            for i in range(1, 5):
                                lesson = tr_all[line_id + i].find_all("td")[c_r_i].text
                                lesson = re.sub('[\n\r\xa0]', ' ', lesson)
                                lesson = lesson.strip()
                                lessons.append(lesson)

                            lessons = CollegeScheduleAbc.parse_lessons(lessons)

                            room = regex_head.group('r') or ''
                            if room:
                                room = CollegeScheduleAbc.find_room(room)

                            schedule_group = {
                                'info': {
                                    'room': room,
                                    'group': {
                                        'name': regex_head.group('f') + regex_head.group('n') + '-' + regex_head.group('y'),
                                        'f': regex_head.group('f'),
                                        'n': regex_head.group('n'),
                                        'y': regex_head.group('y')
                                    },
                                    'time': times[table_id]
                                },
                                'lessons': lessons
                            }

                            schedule.append(schedule_group)

        return schedule


class CollegeScheduleAbc:
    @staticmethod
    def parse_lessons(lessons_raw: list):
        pattern = re.compile(r'(?P<l>[А-Яа-яЁё]+) (?P<f>[А-Яа-яЁё])\. ?(?P<m>[А-Яа-яЁё])\.?')

        lessons = []
        for lesson_id, lesson_raw in enumerate(lessons_raw):
            r = pattern.search(lesson_raw)

            if not r:
                continue

            name = None
            info = None
            teacher = {}

            try:
                name = lesson_raw[:r.start()].strip()
                info = lesson_raw[r.end():].strip()

                info = CollegeScheduleAbc.find_room(info)

                teacher_last_name = r.group('l').lower().title()
                teacher_first_name = r.group('f').upper()
                teacher_middle_name = r.group('m').upper()

                teacher_full_name = '{} {}. {}.'.format(
                    teacher_last_name, teacher_first_name, teacher_middle_name
                )

                teacher = {
                    "full_name": teacher_full_name,
                    "last_name": teacher_last_name,
                    "first_name": teacher_first_name,
                    "middle_name": teacher_middle_name
                }
            except:
                logger.error(lesson_raw)
                logger.error('Parse lesson error:', exc_info=True)

            lesson = {
                "id": lesson_id+1,
                "name": name if name else lesson_raw,
                "teacher": teacher,
                "info": info,
                "raw": lesson_raw
            }

            lessons.append(lesson)

        return lessons

    @staticmethod
    def get_articles(articles: list) -> list:
        pattern = re.compile('(?P<d>[0-9]{1,2})\s?(?P<m>[а-я]+)\s?(?P<y>[0-9]{4})\s?[г]?', flags=re.IGNORECASE)
        months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

        parsed_articles = []
        for a_title, a_link in articles:
            try:
                a_regex_date = re.search(pattern, a_title)

                if not a_regex_date:
                    continue

                a_day = int(a_regex_date.group('d'))
                a_month_name = str(a_regex_date.group('m')).lower()
                a_year = int(a_regex_date.group('y')) or datetime.datetime.today().year

                a_month = months.index(a_month_name[:3])+1

                day = datetime.datetime(day=a_day, month=a_month, year=a_year)

                parsed_articles.append(
                    ScheduleArticle(title=a_title, link=a_link, date=day)
                )
            except Exception:
                logger.error(f'Исключение при обработке страницы блога (articles), проверь результат регулярки', exc_info=True)
                logger.debug(a_title)
                logger.debug(a_link)

        return parsed_articles

    @staticmethod
    def find_article(articles: list, date: datetime.datetime = None):
        for article in articles:
            if article.date == date:
                return article

        return None

    @staticmethod
    def get_weekday(next_day=False):
        dt = datetime.datetime.today()

        if dt.isoweekday() < 5 and (dt.hour >= 17 or next_day):
            return dt + datetime.timedelta(days=1)

        if dt.isoweekday() == 5 and (dt.hour >= 17 or next_day):
            return dt + datetime.timedelta(days=-dt.weekday(), weeks=1)

        if dt.isoweekday() > 5:
            return dt + datetime.timedelta(days=-dt.weekday(), weeks=1)

        return dt

    @staticmethod
    def find_room(info):
        info = info.lower()

        pattern_info = re.compile(r'[ауд]{3}(?:[\.]+)? ?(?P<room>[0-9а-я]+)?')
        info_r = pattern_info.search(info)

        if info and info_r:
            room = info_r.group('room')
            info = "Ауд. {}".format(room) if room else None
        elif 'спорт' in info:
            info = 'Спортивный зал'
        else:
            info = info.replace('.', '')
            info = info.title()

        return info
