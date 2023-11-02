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

    xp_bot = XP_Bot(TOKEN)
    xp_bot.run()
