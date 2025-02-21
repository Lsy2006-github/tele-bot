import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# FAQs
FAQS = {
    "operating hours": "We are open from 9 AM to 10 PM daily.",
    "location": "We are located at 123 Main Street, City.",
    "menu": "Our menu includes coffee, tea, and snacks. Visit our website for more details.",
}

# Dictionary to store unanswered questions
unanswered_questions = {}

# Your Telegram ID (replace with your actual numeric ID)
ADMIN_ID = 1517694368  # Replace with your Telegram numeric user ID

# Function to handle incoming messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text.lower()
    user_id = update.message.chat_id

    # Check if the message matches an FAQ
    for question, answer in FAQS.items():
        if question in user_message:
            await update.message.reply_text(answer)
            return

    # If question is not in FAQs, store it and notify the admin
    unanswered_questions[user_id] = user_message
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"User {user_id} asked: {user_message}")

    await update.message.reply_text("I don't have an answer right now. The admin will reply soon!")

# Function to allow admin to reply
async def reply(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /reply <user_id> <message>")
        return

    user_id = int(args[0])  # Extract user ID
    response_message = " ".join(args[1:])  # Extract response

    if user_id in unanswered_questions:
        await context.bot.send_message(chat_id=user_id, text=f"Admin says: {response_message}")
        del unanswered_questions[user_id]  # Remove question after response
        await update.message.reply_text("Reply sent successfully!")
    else:
        await update.message.reply_text("No pending question from this user.")

# Main function to run the bot
def main():
    TOKEN = "8030276900:AAEeu4g2tirZjYyvxOQLhBUnFX0HAxwdwnY"

    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("reply", reply))  # Admin replies
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Handle messages

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
