# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
import pathlib
import os
import logging
import inspect

from settings import Settings


def get_variable(name):
    stack = inspect.stack()
    try:
        for frames in stack:
            try:
                frame = frames[0]
                current_locals = frame.f_locals
                if name in current_locals:
                    return current_locals[name]
            finally:
                del frame
    finally:
        del stack


def init_logger():
    logger = logging.Logger('kbt_bot', level=logging.DEBUG if Settings.DEBUG else logging.INFO)

    file_handler = get_logger_file_handler()
    file_handler.setLevel(logging.DEBUG)

    stream_handler = get_logger_stream_handler()
    stream_handler.setLevel(level=logging.DEBUG if Settings.DEBUG else logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


def get_logger_formatter(format=u'%(pathname)s:%(lineno)d\n[%(asctime)s] %(levelname)-6s %(threadName)-14s: %(message)s'):
    return logging.Formatter(
        fmt=format,
        datefmt='%d.%m.%y %H:%M:%S')


def get_logger_file_handler():
    pathlib.Path('logs').mkdir(exist_ok=True)
    file_handler = logging.FileHandler(os.path.join('logs', 'log.txt'), encoding='utf-8')

    file_handler.setFormatter(get_logger_formatter())

    return file_handler


def get_logger_stream_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(get_logger_formatter(u'[%(asctime)s] %(levelname)-6s %(threadName)-14s: %(message)s'))

    return stream_handler
