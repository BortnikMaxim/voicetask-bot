from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_kb = ReplyKeyboardMarkup(
keyboard=[
    [KeyboardButton(text="➕ Добавить"), KeyboardButton(text="📋 Список")],
    ],
    resize_keyboard=True
)