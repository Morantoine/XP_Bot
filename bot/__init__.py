import logging
from dotenv import load_dotenv
import os

from .xp_bot import XP_Bot

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def start() :
    load_dotenv()
    TOKEN = os.environ.get("TOKEN")
    ERASE_NEW_YEAR = os.environ.get("ERASE_NEW_YEAR")
    ERASE_NEW_YEAR = True if ERASE_NEW_YEAR == "true" else False

    xp_bot = XP_Bot(TOKEN, ERASE_NEW_YEAR)
    xp_bot.run()
