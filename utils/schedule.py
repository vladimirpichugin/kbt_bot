# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>

import re
import datetime
import requests
from bs4 import BeautifulSoup


class CollegeScheduleGrabber:
    def __init__(self, domain, blog_path):
        self.domain = domain
        self.blog_path = blog_path
        self.pattern = re.compile(r'^(?P<c>([А-Я]{1,2}))(\s)?(?P<n>[0-9]{2})([\s\-])?(?P<y>[0-9]{2})', flags=re.IGNORECASE)

    def get_blog(self):
        link = self.domain + self.blog_path

        blog_content = requests.get(link)

        soup = BeautifulSoup(blog_content.content, "html.parser")

        elements = soup.find("div", class_="kris-blogitem-all").find("ol").find_all("div", class_="item-body-h")

        articles = []
        for element in elements:
            item = element.find("a")

            text = item.text
            href = item.get("href")

            articles.append((text, href))

        return tuple(articles)

    def get_article(self, article_path: str):
        link = self.domain + article_path

        schedule_content = requests.get(link)

        soup = BeautifulSoup(schedule_content.content, "html.parser")

        tables = soup.find("div", class_="kris-post-item-txt").find("div").find_all("table")

        groups = {}
        for table_index, table in enumerate(tables):
            g_s_c = table.find("tbody").find_all("tr")

            for column in g_s_c:
                column_rows = column.find_all("td")

                for c_r_i, rows in enumerate(column_rows):
                    _rows = rows.find_all("p")

                    for r_i, row in enumerate([_.text for _ in _rows]):
                        r = self.pattern.search(row)

                        if r:
                            lessons = []
                            for i in range(1, 5):
                                lessons.append(g_s_c[r_i + i].find_all("td")[c_r_i].text.replace(u'\xa0', ''))
                            groups[r.group('c') + r.group('n') + '-' + r.group('y')] = lessons

        return groups


class CollegeScheduleAbc:
    @staticmethod
    def format_lessons(lessons: list):
        lessons_f = []

        for lesson in lessons:
            lessons_f.append([_ for _ in lesson.split('\n') if _ and _ not in ['\xa0']])

        lessons_f = list(map(tuple, lessons_f))

        return lessons_f

    @staticmethod
    def find_article(day_dt, articles: list):
        pattern = re.compile('(?P<d>([0-9]{2}))\s+(?P<m>([а-я]{3}))', flags=re.IGNORECASE)
        months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

        for title, link in articles:
            article_date = re.search(pattern, title)

            if not article_date:
                continue

            article_day, article_month = int(article_date.group('d')), str(article_date.group('m'))
            article_month_num = months.index(article_month)+1

            article_day_dt = datetime.datetime(day=article_day, month=article_month_num, year=datetime.datetime.now().year)

            if article_day_dt.month == day_dt.month and article_day_dt.day == day_dt.day:
                return link

        return None

    @staticmethod
    def get_day():
        today = datetime.datetime.today().date()

        if today.isoweekday() in [6, 7]:
            return today + datetime.timedelta(days=-today.weekday(), weeks=1)

        return today + datetime.timedelta(days=1)
