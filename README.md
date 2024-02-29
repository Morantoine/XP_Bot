# XP_Bot

A Telegram bot written in Python to keep track of people's XP based on trigger messages.

To make your own : 
- Clone this project.
- Change text for the different messages in `/data/message_templates.json`.
- Create your own bot by talking to [BotFather](https://telegram.me/BotFather). Don't forget to turn off privacy mode to give it access to the messages ! Also keep its token for later.

Run the default bot with docker (recommended) :
- Load the image with `docker load < ./xp_bot_docker.tar.gz`.
- Run the bot with `docker run -it -e TOKEN="bot_token_goes_here" -v $(pwd)/data:/data xp-bot:latest`.
- Talk to the bot in private to setup everything !

Otherwise, if you want to modify the code, you can try to set up the poetry env (with the Nix flake it's easy) by your own.
To backup the scores, simply backup the database loacted at `/data/xp_data.db`.
