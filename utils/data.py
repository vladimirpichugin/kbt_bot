# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>


class SDict(dict):
    def __init__(self, *args, **kwargs):
        self.changed = False
        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        return super().__getitem__(item)

    def __setitem__(self, item, value):
        try:
            if super().__getitem__(item) != value:
                self.changed = True
        except KeyError:
            self.changed = True

        return super().__setitem__(item, value)

    def __delitem__(self, item):
        self.changed = True
        super().__delitem__(item)

    def getraw(self, item, default=None):
        try:
            return super().__getitem__(item)
        except KeyError:
            return default

    def setraw(self, item, value):
        super().__setitem__(item, value)

    def delraw(self, item):
        super().__delitem__(item)


class Client(SDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.id = self.getraw('_id')
        self.is_admin = self.getraw('is_admin', False)
        self.is_staff = self.getraw('is_staff', False)

    def get_id(self) -> int:
        return self.id

    def get_name(self, include_middle_name=False) -> str:
        name = []

        if self.getraw('first_name'):
            name.append(self.getraw('first_name'))
        if self.getraw('middle_name') and include_middle_name:
            name.append(self.getraw('middle_name'))
        if self.getraw('last_name'):
            name.append(self.getraw('last_name'))

        if name:
            return ' '.join(name)

        return ''

    @staticmethod
    def create(data):
        return Client(data)


class ScheduleArticle(SDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
