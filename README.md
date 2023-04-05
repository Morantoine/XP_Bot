# XP_Bot

A rudimentary Telegram bot written in Python to keep track of people's XP based on trigger messages.

To make your own : 
- Fork this project.
- Change answer text for the different handlers in `xp_bot.py`, as well as the text which triggers the xp updates.
- Create your own bot by talking to [BotFather](https://telegram.me/BotFather).
- Create `.env` file containing the `TOKEN` environment variable, like this : `TOKEN=your_token` (without any quotes)
- If you use Docker :
  - Build the image with `docker build -t xp-bot .`.
  - Run the bot with `docker run -it xp-bot`.
- Otherwise, simply find a way to get all the dependencies installed and run `python main.py` on your own.
  - Talk to the bot in private to setup everything !
