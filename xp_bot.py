from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram import Update, constants
from xp_database import XPDatabase
import logging

from datetime import datetime, timedelta


class XP_Bot:
    def __init__(self, TOKEN) -> None:
        # Start the app and start/load the database
        self.bot = ApplicationBuilder().token(TOKEN).build()
        self.db = XPDatabase()

        # Initlialize the dictionnary to track the cooldown
        self.last_changed = {}
        self.DELAY_TIME = timedelta(seconds=30)

        # Add all the functionnality handlers
        self.bot.add_handler(CommandHandler("start", self.start))
        self.bot.add_handler(
            CommandHandler(
                "enable", self.enable, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.bot.add_handler(
            CommandHandler(
                "disable", self.disable, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.bot.add_handler(
            CommandHandler(
                "xp", self.check_xp, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.bot.add_handler(
            CommandHandler(
                "top", self.top_users, filters=filters.TEXT & filters.ChatType.GROUPS
            )
        )
        self.bot.add_handler(
            MessageHandler(
                filters.TEXT & (~filters.COMMAND) & filters.ChatType.GROUPS,
                self.change_xp,
            )
        )
        self.bot.add_handler(
            MessageHandler(
                filters.ChatType.GROUPS & filters.StatusUpdate.LEFT_CHAT_MEMBER,
                self.left_chat,
            )
        )
        self.bot.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                self.added_to_group,
            )
        )

    def run(self) -> None:
        self.bot.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt message when you start the bot"""
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Klk soy el bot de los mases, agregame a tu grupo y lanza el comando /enable desde ahí.",
        )

    async def added_to_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt message when you add the bot to a group"""
        for member in update.message.new_chat_members:
            if member.username == "LosMases_bot":
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Hola aquí estoy, lanza el comando /enable, y dale un megamás a Fransua para probar.",
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
                text="Ya puedes mandar mases y menoses en este grupo.",
            )

        # Do nothing if user doesn't have the necessary rights
        elif member.status not in ["creator", "administrator"]:
            bot_added_by = self.db.get_bot_added_by(chat_id)
            if bot_added_by != user_id:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Sólo los admins o el user que añadió el bot lo puede activar.",
                )
                return

        else:
            success = self.db.enable_chat(chat_id)
            if success:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.id,
                    text="Vamos podeis mandar mases siuuu.",
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.id,
                    text="Algo salió mal preguntale al Fransua.",
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
                text="A donde vas desactivando si no había nada.",
            )

        # Do nothing if user doesn't have the necessary rights
        if member.status not in ["creator", "administrator"]:
            bot_added_by = self.db.get_bot_added_by(chat_id)
            if bot_added_by != user_id:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Sólo los admins o el user que añadió el bot lo puede desactivar.",
                )
                return

        success = self.db.disable_chat(chat_id)
        if success:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="A tomar por saco el XP.",
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="Algo salió mal preguntale al Fransua.",
            )

    async def check_xp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for the /xp command, to check your rating."""
        user_id = update.message.from_user.id
        chat_id = update.message.chat_id
        username = update.message.from_user.username

        # Check if the chat is enabled for XP tracking
        if not self.db.is_chat_enabled(chat_id):
            answer = "Los mases no están activados en este grupo."

        else:
            # Get the user's XP and level
            xp = self.db.get_user_xp(chat_id, user_id)
            answer = f"{username}, tu reputación es de {xp}."

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text=answer,
        )

    async def change_xp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler to change the xp"""
        message = update.message
        message_text = message.text.lower()
        chat_id = message.chat_id

        mases = ["+", "++", "mega+", "megamas", "megamás"]
        menoses = ["-", "--", "mega-", "megamenos"]

        todo = mases + menoses

        # Only check messages that is exactly one of the accepted
        if not message_text in todo:
            return

        # Do nothing if the chat is not enabled
        elif not self.db.is_chat_enabled(chat_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="Activa el bot con /enable antes de venirte arriba.",
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

            if reciever_id == sender_id or reciever_id == self.bot.bot.id:
                # Don't allow people to change their own xp
                return

            if reciever_status in ["left", "kicked"]:
                # Don't allow people to change xp of people who got banned or left
                return

            xp_amount = 0
            old_xp = self.db.get_user_xp(chat_id, reciever_id)

            if message_text == "+":
                xp_amount = 1
            elif message_text in ["++", "mega+", "megamas", "megamás"]:
                xp_amount = 2
            elif message_text == "-":
                xp_amount = -1
            elif message_text in ["--", "mega-", "megamenos"]:
                xp_amount = -2
            if xp_amount != 0:

                # Check that delay is ok
                last_change_time = self.last_changed.get(
                    (sender_id, reciever_id), datetime.min
                )
                elapsed_time = datetime.now() - last_change_time
                if elapsed_time < self.DELAY_TIME:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        reply_to_message_id=update.message.id,
                        text=f"Espera {int((self.DELAY_TIME - elapsed_time).total_seconds())} segundos antes de volver a cambiar la reputación de {reciever_name}.",
                    )
                    return

                self.last_changed[(sender_id, reciever_id)] = datetime.now()

                self.db.update_user_xp(chat_id, reciever_id, xp_amount)
                sender_medal = self.db.get_medal(chat_id=chat_id, user_id=sender_id)
                reciever_medal = self.db.get_medal(chat_id=chat_id, user_id=reciever_id)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.id,
                    text=f"{sender_medal}{sender_name} ha cambiado la reputación de {reciever_medal}{reciever_name} a {old_xp+xp_amount:+}.",  # ({xp_amount:+}).",
                )

    async def top_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler to display top users and ratings"""
        chat_id = update.message.chat_id

        # Do nothing if the chat is not enabled
        if not self.db.is_chat_enabled(chat_id):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text="Activa el bot con /enable antes de venirte arriba.",
            )

        else:
            top_users = self.db.get_top_users(chat_id=chat_id)
            message = "Los más populares del patio :\n\n"

            for i, (user_id, xp) in enumerate(top_users):
                # Format each line
                member = await context.bot.get_chat_member(chat_id, user_id)
                member = member.user
                medal = str(i + 1)
                if i == 0:
                    medal = "🥇"
                elif i == 1:
                    medal = "🥈"
                elif i == 2:
                    medal = "🥉"
                message += f"[{medal}] {member.full_name} ({xp:+})\n"

            if len(top_users) == 0:
                message += "Por ahora nadie a parte del Nano."

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                reply_to_message_id=update.message.id,
                text=message,
            )

    async def left_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler to reset the rating when someone leaves the chat"""
        user = update.message.left_chat_member
        chat_id = update.message.chat_id
        user_id = user.id
        user_name = user.name
        self.db.remove_user(user_id, chat_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            reply_to_message_id=update.message.id,
            text=f"{user_name} borrado de la lista de mases.",
        )
