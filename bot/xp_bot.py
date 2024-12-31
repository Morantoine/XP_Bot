from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram import Update
from database_queries import XPDatabase
import os 
import json
from collections import defaultdict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import shutil
from pytz import timezone

from datetime import datetime, timedelta

with open('./message_templates.json', 'r') as file:
    message_templates = json.load(file)

with open('./plus_minus.json', 'r') as file:
    plus_minus_triggers = json.load(file)

class XP_Bot:
    def __init__(self, TOKEN, ERASE_NEW_YEAR) -> None:
        # Start the app and start/load the database
        self.app = ApplicationBuilder().token(TOKEN).build()
        self.db = XPDatabase()
        self.groups = set()
        self.scheduler = BackgroundScheduler(timezone=timezone("Europe/Paris"))
        self.scheduler.start()
        self.erase_new_year = ERASE_NEW_YEAR

        # Initlialize the dictionnary to track the cooldown
        self.last_changed = {}
        self.last_top = {}
        self.DELAY_TIME = timedelta(seconds=30)

        # Initlialize the value of the last xp update and info messages to only keep one
        self.last_xp_update = {}
        self.last_xp_info = defaultdict(lambda: defaultdict(int))

        # Add all the functionnality handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(
            CommandHandler(
                "enable", self.enable, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.app.add_handler(
            CommandHandler(
                "disable", self.disable, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.app.add_handler(
            CommandHandler(
                "xp", self.check_xp, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.app.add_handler(
            CommandHandler(
                "top", self.top_users, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.app.add_handler(
            MessageHandler(
                filters.TEXT
                & (~filters.COMMAND)
                & (~filters.UpdateType.EDITED)
                & filters.ChatType.GROUPS,
                self.change_xp,
            )
        )
        self.app.add_handler(
            MessageHandler(
                filters.ChatType.GROUPS & filters.StatusUpdate.LEFT_CHAT_MEMBER,
                self.left_chat,
            )
        )
        self.app.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                self.added_to_group,
            )
        )

        self.schedule_new_year_message()

    def run(self) -> None:
        self.app.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt message when you start the bot"""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_templates["admin"]["greeting"]
        )

    async def added_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt message when you add the bot to a group"""
        chat_id = update.message.chat_id
        self.groups.add(chat_id)

        for member in update.message.new_chat_members:
            if member.is_bot and member.id == context.bot.id:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message_templates["admin"]["group_greeting"]
                )

    async def enable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command to enable the XP functionnality in a given group"""
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        member = await context.bot.get_chat_member(chat_id, user_id)

        # Do nothing if already ON
        if self.db.is_chat_enabled(chat_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_templates["admin"]["enabled_already"]
            )

        # Do nothing if user doesn't have the necessary rights
        elif member.status not in ["creator", "administrator"]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_templates["admin"]["enabled_no_rights"]
            )

        else:
            success = self.db.enable_chat(chat_id)
            if success:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.id,
                    text=message_templates["admin"]["enabled"]
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.id,
                    text=message_templates["admin"]["enabled_runtime_error"]
                )

    async def disable(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Command to disable the XP functionnality in a given group"""
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        member = await context.bot.get_chat_member(chat_id, user_id)

        # Do nothing if already OFF
        if not self.db.is_chat_enabled(chat_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_templates["admin"]["disabled_already"]
            )
            return

        # Do nothing if user doesn't have the necessary rights
        if member.status not in ["creator", "administrator"] :
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_templates["admin"]["disabled_no_rights"]
            )
            return

        success = self.db.disable_chat(chat_id)
        if success:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message_templates["admin"]["disabled"]
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message_templates["admin"]["disabled_runtime_error"]
            )

    async def check_xp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for the /xp command, to check your rating."""
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        username = update.message.from_user.username

        # Check if the chat is enabled for XP tracking
        if not self.db.is_chat_enabled(chat_id):
            answer = message_templates["admin"]["warn"]

        else:
            # Get the user's XP and level
            xp = self.db.get_user_xp(chat_id, user_id)
            answer = message_templates["xp"]["xp_status"].format(name=username, xp=xp)

        new_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text=answer,
        )

        await self.delete_refresh_xp_info(
            new_message.message_id, chat_id, user_id, context
        )

    async def change_xp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler to change the xp"""
        message = update.message

        message_text = message.text.lower()
        chat_id = message.chat_id

        self.groups.add(chat_id)

        simple_plus_triggers = plus_minus_triggers["simple_plus"]
        simple_minus_triggers = plus_minus_triggers["simple_minus"]
        double_minus_triggers = plus_minus_triggers["double_minus"]
        double_plus_triggers = plus_minus_triggers["double_plus"]

        plus_triggers = simple_plus_triggers + double_plus_triggers
        minus_triggers = simple_minus_triggers + double_minus_triggers
        menoses = ["-", "--", "mega-", "megamenos"]

        all_triggers = plus_triggers + minus_triggers

        # Only check messages that are exactly one of the accepted
        if not message_text in all_triggers:
            return

        # Do nothing if the chat is not enabled
        elif not self.db.is_chat_enabled(chat_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message_templates["warn"]
            )

        # Only take into account messages that answer others
        elif message.reply_to_message:
            # Get info from the sender
            sender_id = message.from_user.id
            sender_name = message.from_user.name

            # Get info from the reciever
            reciever_id = message.reply_to_message.from_user.id
            reciever_user = await update.effective_chat.get_member(reciever_id)
            reciever_status = reciever_user.status
            reciever_name = message.reply_to_message.from_user.name

            if reciever_id == sender_id or reciever_user.user.is_bot:
                # Don't allow people to change their own xp or any bot's xp
                return

            if reciever_status in ["left", "kicked"]:
                # Don't allow people to change xp of people who got banned or left
                return

            xp_amount = 0
            old_reciever_xp = self.db.get_user_xp(chat_id, reciever_id)
            sender_xp = self.db.get_user_xp(chat_id, sender_id)

            if message_text in simple_plus_triggers:
                xp_amount = 1
            elif message_text in double_plus_triggers:
                xp_amount = 2
            elif message_text in simple_minus_triggers:
                xp_amount = -1
            elif message_text in double_minus_triggers:
                xp_amount = -2
            if xp_amount != 0:

                # Check that delay is ok
                last_change_time = self.last_changed.get(
                    (sender_id, reciever_id), datetime.min
                )
                elapsed_time = datetime.now() - last_change_time
                if elapsed_time < self.DELAY_TIME:
                    new_message = await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        reply_to_message_id=update.message.id,
                        text=message_templates["xp"]["wait"].format(time=int((self.DELAY_TIME - elapsed_time).total_seconds()), name = reciever_name)
                    )
                    await self.delete_refresh_xp_update(
                        new_message.message_id, chat_id, context
                    )
                    return

                self.last_changed[(sender_id, reciever_id)] = datetime.now()

                self.db.update_user_xp(chat_id, reciever_id, xp_amount)
                sender_medal = self.db.get_medal(chat_id=chat_id, user_id=sender_id)
                reciever_medal = self.db.get_medal(chat_id=chat_id, user_id=reciever_id)

                new_message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.id,
                    text=message_templates["xp"]["change"].format(sender_medal=sender_medal, sender_name=sender_name, sender_xp=sender_xp,
                                                         reciever_medal=reciever_medal, reciever_name=reciever_name, reciever_xp=old_reciever_xp+xp_amount)
                )

                await self.delete_refresh_xp_update(
                    new_message.message_id, chat_id, context
                )

                # Update the full name of the reciever with the last known value
                self.db.refresh_username(
                    chat_id, reciever_id, reciever_user.user.full_name
                )

    async def delete_refresh_xp_update(self, new_msg_id, chat_id, context):
        if chat_id in self.last_xp_update:
            # Delete last sent xp update message
            await context.bot.delete_message(
                chat_id=chat_id, message_id=self.last_xp_update[chat_id]
            )
        # Keep in track the latest xp change message id
        self.last_xp_update[chat_id] = new_msg_id

    async def delete_refresh_top(self, new_msg_id, chat_id, context):
        if chat_id in self.last_top:
            # Delete last sent top message
            await context.bot.delete_message(
                chat_id=chat_id, message_id=self.last_top[chat_id]
            )
        # Keep in track the latest top message id
        self.last_top[chat_id] = new_msg_id

    async def delete_refresh_xp_info(self, new_msg_id, chat_id, user_id, context):
        if chat_id in self.last_xp_info:
            if user_id in self.last_xp_info[chat_id]:
                # Delete last sent top message
                await context.bot.delete_message(
                    chat_id=chat_id, message_id=self.last_xp_info[chat_id][user_id]
                )
        # Keep in track the latest top message id
        self.last_xp_info[chat_id][user_id] = new_msg_id

    async def top_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler to display top users and ratings"""
        chat_id = update.message.chat_id

        # Do nothing if the chat is not enabled
        if not self.db.is_chat_enabled(chat_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message_templates["warn"]
            )

        else:
            top_users = self.db.get_top_users(chat_id=chat_id, limit=10)
            message = message_templates["xp"]["popular"] + "\n"

            for i, (user_id, xp) in enumerate(top_users):
                # Format each line
                try:
                    # Try to talk directly to Telegram's API
                    member = await context.bot.get_chat_member(chat_id, user_id)
                    full_name = member.user.full_name
                except:
                    # If it fails, load the user full name from the stored db
                    full_name = self.db.get_stored_username_by_user_id(chat_id, user_id)
                if full_name is None:
                    pass
                medal = str(i + 1)
                if i == 0:
                    medal = "🥇"
                elif i == 1:
                    medal = "🥈"
                elif i == 2:
                    medal = "🥉"
                message += f"[{medal}] {full_name} ({xp:+})\n"

            if len(top_users) == 0:
                message += message_templates["xp"]["popular_empty"]

            new_message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message,
            )

            await self.delete_refresh_top(new_message.message_id, chat_id, context)

    async def send_new_year_message(self, context):
        current_year = datetime.now().year

        for chat_id in self.groups :
            await context.bot.send_message(
                chat_id=chat_id,
                text = message_templates["admin"]["new_year_greeting"].format(year=current_year)
            )

        if self.erase_new_year:
            for chat_id in self.groups :
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message_templates["admin"]["new_year_deletion"]
                )
            try:
                shutil.move("./xp_data.db", f"./xp_data_{current_year}.db")
                print("File moved successfully.")
                self.db = XPDatabase()
            except Exception as e:
                print(f"Error moving file: {e}") 

    # Wrapper function for APScheduler
    def send_new_year_message_job(self, app, loop):
        asyncio.run_coroutine_threadsafe(
            self.send_new_year_message(app),
            loop
        )


    def schedule_new_year_message(self):
        loop = asyncio.get_event_loop()
        self.scheduler.add_job(
            self.send_new_year_message_job, 
            CronTrigger(
                month=1, day=1, hour=0, minute=0, second=0,
                timezone=timezone("Europe/Paris")
            ),
            args=[self.app, loop],
            id="new_year_greeting",
            replace_existing=True
        )


    async def left_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler to reset the rating when someone leaves the chat"""
        user = update.message.left_chat_member
        chat_id = update.message.chat_id
        user_id = user.id
        user_name = user.name
        self.db.remove_user(user_id, chat_id)
        if user_id != context.bot.id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message_templates["admin"]["leave"].format(name=user_name)
            )
