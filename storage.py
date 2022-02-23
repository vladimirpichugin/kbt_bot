# -*- coding: utf-8 -*-
# Author: Vladimir Pichugin <vladimir@pichug.in>
from utils import Storage
from utils import logger

from settings import Settings


try:
    logger.info("Initializing storage..")
    storage = Storage(Settings.MONGO, Settings.MONGO_DATABASE, Settings.COLLECTIONS)
    logger.debug(f"MongoDB Server version: {storage.mongo_client.server_info()['version']}")
except Exception as e:
    logger.error("Failed to establish a stable connection to MongoDB", exc_info=True)
    raise RuntimeError from e
