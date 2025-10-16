from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить задачу")],
        [KeyboardButton(text="📅 Мои задачи"), KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True
)

def task_inline_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{task_id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{task_id}")]
        ]
    )