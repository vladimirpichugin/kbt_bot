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
        pattern = re.compile(r'^(?P<f>([А-Я]{1,2}))(\s)?(?P<n>[0-9]{2})([\s\-])?(?P<y>[0-9]{2})\s(?P<r>.+)?', flags=re.IGNORECASE)
        link = self.domain + article_path

        schedule_content = requests.get(link)

        soup = BeautifulSoup(schedule_content.content, "html.parser")

        tables = soup.find("div", class_="kris-post-item-txt").find_all("table")

        schedule = []
        for table_index, table in enumerate(tables):
            g_s_c = table.find("tbody").find_all("tr")

            for column in g_s_c:
                column_rows = column.find_all("td")

                for c_r_i, rows in enumerate(column_rows):
                    _rows = rows.find_all("p")

                    for r_i, row in enumerate([_.text for _ in _rows]):
                        r = pattern.search(row)

                        if r:
                            lessons = []
                            for i in range(1, 5):
                                lessons.append(g_s_c[r_i + i].find_all("td")[c_r_i].text.replace(u'\xa0', ''))

                            lessons = CollegeScheduleAbc.parse_lessons(lessons)

                            room = r.group('r') or ''
                            room = room.lower().replace('\n', '').strip()

                            if room in ['ауд.']:
                                room = None

                            info = {
                                'room': room,
                                'group': {
                                    'name': r.group('f') + r.group('n') + '-' + r.group('y'),
                                    'f': r.group('f'),
                                    'n': r.group('n'),
                                    'y': r.group('y')
                                }
                            }

                            schedule.append({
                                'info': info,
                                'lessons': lessons
                            })

        return schedule


class CollegeScheduleAbc:
    @staticmethod
    def parse_lessons(lessons_raw: list):
        pattern = re.compile(r'(?P<name>[А-Яа-я\-\. ]+)\s(?P<teacher>(?P<last_name>[А-Яа-я\-]+)[ ]?(?P<first_name>[А-Яа-я]+)?(\.)?[ ]?((?P<middle_name>[А-Яа-я]+)(\.)?))\s(?P<info>[А-Яа-я0-9\-\.\s]+)',
                             flags=re.IGNORECASE)

        lessons = []
        for lesson_id, lesson_raw in enumerate(lessons_raw):
            r = re.search(pattern, lesson_raw)

            if not r:
                continue

            info = r.group('info') or ''
            info = info.lower().replace('\n', '').strip()

            if 'ауд' in info:
                info = None

            lesson = {
                "id": lesson_id+1,
                "name": r.group('name'),
                "teacher": {
                    "full_name": r.group('teacher'),
                    "last_name": r.group('last_name'),
                    "first_name": r.group('first_name'),
                    "middle_name": r.group('middle_name')
                },
                "info": info,
                "raw": lesson_raw
            }

            lessons.append(lesson)

        return lessons

    @staticmethod
    def get_articles(articles: list) -> list:
        pattern = re.compile('(?P<d>([0-9]{1,2}))\s+(?P<m>([а-я]{3}))', flags=re.IGNORECASE)
        months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

        parsed_articles = []
        for article_title, article_link in articles:
            try:
                article_date = re.search(pattern, article_title)

                if not article_date:
                    continue

                article_day, article_month = int(article_date.group('d')), str(article_date.group('m'))
                article_month_num = months.index(article_month)+1

                day = datetime.datetime(
                    day=article_day,
                    month=article_month_num,
                    year=datetime.datetime.today().year
                )

                parsed_articles.append(
                    ScheduleArticle(title=article_title, link=article_link, date=day)
                )
            except Exception:
                logger.error(f'Исключение при обработке страницы блога (articles), проверь результат регулярки', exc_info=True)
                logger.debug(article_title)
                logger.debug(article_link)
                logger.debug(article_date)

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
