import logging
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Enable logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["telebot_db"]
collection = db["shower"]

# FAQs
FAQS = {
    'test': 'This is a test FAQ.',
}

# Dictionary to store unanswered questions
unanswered_questions = {}

# List of admin IDs (replace with your actual numeric IDs)
# ADMIN_IDS = [1517694368, 1184047298, 692160074, 1121779599]  # Replace with your Telegram numeric user IDs
ADMIN_IDS = [1517694368]  # Testing environment
SHOWER_IDS = [1517694368]

# Function to handle incoming messages
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text.lower()
    user_id = update.message.chat_id

    # Check local time (UTC +8)
    tz = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(tz)
    if 23 <= current_time.hour or current_time.hour < 6:
        await update.message.reply_text("Please note that responses may be slower between 11 PM and 6 AM.")

    # Check if the message matches an FAQ
    for question, answer in FAQS.items():
        if question in user_message:
            await update.message.reply_text(answer)
            return

    # If question is not in FAQs, store it and notify the admins
    unanswered_questions[user_id] = user_message
    for admin_id in ADMIN_IDS:
        await context.bot.send_message(chat_id=admin_id, text=f"User {user_id} asked: {user_message}")
    await update.message.reply_text("I don't have an answer right now. The admin will reply soon!")

# Function to handle FAQ command
async def faq(update: Update, context: CallbackContext) -> None:
    faq_text = "\n".join([f"• *{question.capitalize()}* - {answer}" for question, answer in FAQS.items()])
    await update.message.reply_text(f"Here are some frequently asked questions:\n\n{faq_text}", parse_mode="Markdown")

# Function to allow admin to reply
async def reply(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id not in ADMIN_IDS:
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

# Function to show admin list
async def admin_list(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    admin_info = []
    for admin_id in ADMIN_IDS:
        user = await context.bot.get_chat(admin_id)
        admin_info.append(f"• {user.username} (ID: {admin_id})")

    admin_list_text = "\n".join(admin_info)
    await update.message.reply_text(f"Admin List:\n\n{admin_list_text}")
    
async def add_shower(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id not in SHOWER_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    keyboard = [
        [InlineKeyboardButton("Male Shower Left", callback_data='1')],
        [InlineKeyboardButton("Male Shower Right", callback_data='2')],
        [InlineKeyboardButton("Female Shower Left", callback_data='3')],
        [InlineKeyboardButton("Female Shower Right", callback_data='4')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select the shower room:", reply_markup=reply_markup)
    context.user_data['keyboard'] = keyboard  # Accessing context to store keyboard

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    room_id = query.data

    context.user_data['room_id'] = room_id
    await query.edit_message_text(text=f"Selected option: {room_id}. Now, please enter the number of people:")

async def handle_number_of_people(update: Update, context: CallbackContext) -> None:
    if 'room_id' not in context.user_data:
        await update.message.reply_text("Please select a shower room first using /add_shower.")
        return

    try:
        number_of_people = int(update.message.text)
    except ValueError:
        await update.message.reply_text("The number of people must be an integer.")
        return

    room_id = context.user_data['room_id']
    room_names = {
        '1': "Male Shower Left",
        '2': "Male Shower Right",
        '3': "Female Shower Left",
        '4': "Female Shower Right"
    }
    room_name = room_names.get(room_id)

    # Get current time in Singapore
    tz = pytz.timezone('Asia/Singapore')
    current_time = datetime.now(tz)
    formatted_time = current_time.strftime("%d/%m/%Y %H:%M")

    collection.insert_one({
        "room_id": room_name,
        "number_of_people": number_of_people,
        "timestamp": formatted_time,
        "ref_time": current_time
    })
    await update.message.reply_text(f"Shower record added successfully for {room_name} with {number_of_people} people at {formatted_time}.")
    del context.user_data['room_id']
async def shower_status(update: Update, context: CallbackContext) -> None:
    pipeline = [
        {"$sort": {"ref_time": -1}},
        {"$group": {
            "_id": "$room_id",
            "latest_record": {"$first": "$$ROOT"}
        }}
    ]
    results = list(collection.aggregate(pipeline))
    if results:
        latest_timestamp = max(result["latest_record"]["timestamp"] for result in results)
        response = f"Latest shower records:\n(Last updated: {latest_timestamp})\n"
        for result in results:
            room_id = result["latest_record"]["room_id"]
            number_of_people = result["latest_record"]["number_of_people"]
            response += f"\n{room_id}: {number_of_people} people on queue"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("No shower records found.")

def main():
    TOKEN = "8030276900:AAEeu4g2tirZjYyvxOQLhBUnFX0HAxwdwnY"

    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", faq))  # Start command
    app.add_handler(CommandHandler("faq", faq))  # FAQ command
    app.add_handler(CommandHandler("reply", reply))  # Admin replies
    app.add_handler(CommandHandler("admins", admin_list))  # Admin list command
    app.add_handler(CommandHandler("add_shower", add_shower))  # Add shower ID command
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Handle messages
    app.add_handler(CallbackQueryHandler(button))  # Handle button callbacks
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Handle messages

    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
