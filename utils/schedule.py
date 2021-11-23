# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import re
import datetime
import requests
from bs4 import BeautifulSoup

from .data import ScheduleArticle


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
            item = element.find("a")

            text = item.text
            href = item.get("href")

            articles.append((text, href))

        return articles

    def parse_article(self, article_path: str) -> list:
        pattern = re.compile(r'^(?P<c>([А-Я]{1,2}))(\s)?(?P<n>[0-9]{2})([\s\-])?(?P<y>[0-9]{2})\s(?P<r>.+)?', flags=re.IGNORECASE)
        link = self.domain + article_path

        schedule_content = requests.get(link)

        soup = BeautifulSoup(schedule_content.content, "html.parser")

        tables = soup.find("div", class_="kris-post-item-txt").find("div").find_all("table")

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

                            group_name = r.group('c') + r.group('n') + '-' + r.group('y')
                            room = r.group('r')

                            schedule.append({
                                'group': group_name,
                                'room': room,
                                'lessons': lessons,
                            })

        return schedule


class CollegeScheduleAbc:
    @staticmethod
    def parse_lessons(lessons: list):
        lessons_f = []

        for lesson in lessons:
            lessons_f.append([_ for _ in lesson.split('\n') if _ and _ not in ['\xa0']])

        lessons_f = list(map(tuple, lessons_f))

        return lessons_f

    @staticmethod
    def get_articles(articles: list) -> list:
        pattern = re.compile('(?P<d>([0-9]{2}))\s+(?P<m>([а-я]{3}))', flags=re.IGNORECASE)
        months = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

        parsed_articles = []
        for article_title, article_link in articles:
            article_date = re.search(pattern, article_title)

            if not article_date:
                continue

            article_day, article_month = int(article_date.group('d')), str(article_date.group('m'))
            article_month_num = months.index(article_month)+1

            day = datetime.datetime(
                day=article_day,
                month=article_month_num,
                year=datetime.datetime.now().year
            )

            parsed_articles.append(
                ScheduleArticle(title=article_title, link=article_link, date=day)
            )

        return parsed_articles

    @staticmethod
    def find_article(articles: list, date: datetime.datetime = None):
        for article in articles:
            if article.date == date:
                return article

        return None

    @staticmethod
    def get_weekday():
        dt = datetime.datetime.today()

        if dt.isoweekday() >= 6 or (dt.isoweekday() == 5 and dt.hour >= 5):
            return dt + datetime.timedelta(days=-dt.weekday(), weeks=1)

        if dt.hour >= 5:
            return dt + datetime.timedelta(days=1)

        return dt
