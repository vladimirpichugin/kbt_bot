from utils import logger
from utils import Json

from settings import Settings


logger.info("Initializing localization..")
L10n = Json(Settings.L10N_RU_FILE)
