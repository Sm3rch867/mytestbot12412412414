import asyncio
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    FSInputFile, 
    ReplyKeyboardRemove
)

import config
from database import init_db, get_categories, get_products_by_category, get_product

# Состояния FSM для оформления заказа
class OrderState(StatesGroup):
    selecting_size = State()
    entering_fio = State()
    entering_phone = State()
    entering_city = State()
    entering_post = State()

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")]
    ])

# Клавиатура категорий
def get_categories_keyboard():
    categories = get_categories()
    builder = []
    for cat in categories:
        builder.append([InlineKeyboardButton(text=cat, callback_data=f"cat_{cat}")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

# Старт
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\nДобро пожаловать в наш магазин одежды.",
        reply_markup=get_main_keyboard()
    )

# Показ категорий
@dp.callback_query(F.data == "catalog")
async def show_categories(callback: types.CallbackQuery):
    await callback.message.edit_text("Выберите категорию товаров:", reply_markup=get_categories_keyboard())

# Показ товаров в категории
@dp.callback_query(F.data.startswith("cat_"))
async def show_products(callback: types.CallbackQuery):
    category = callback.data.split("_")[1]
    products = get_products_by_category(category)
    
    keyboard = []
    for prod_id, name, price in products:
        keyboard.append([InlineKeyboardButton(text=f"{name} — {price} ₴", callback_data=f"prod_{prod_id}")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад в каталог", callback_data="catalog")])
    
    await callback.message.edit_text(f"Категория: **{category}**\nВыберите товар:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

# Карточка товара
@dp.callback_query(F.data.startswith("prod_"))
async def show_product_card(callback: types.CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    product = get_product(prod_id)
    
    if not product:
        await callback.answer("Товар не найден.")
        return
        
    p_id, name, category, price, sizes, image_path, description = product
    
    text = (
        f"📌 **{name}**\n\n"
        f"📝 {description}\n\n"
        f"📏 **Доступные размеры:** {sizes}\n"
        f"💰 **Цена:** {price} ₴"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{p_id}")],
        [InlineKeyboardButton(text="⬅️ Назад к товарам", callback_data=f"cat_{category}")]
    ])
    
    # Удаляем предыдущее текстовое сообщение и отправляем фото
    await callback.message.delete()
    
    if os.path.exists(image_path):
        photo = FSInputFile(image_path)
        await callback.message.answer_photo(photo=photo, caption=text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

# Нажатие на "Купить" -> Выбор размера
# Нажатие на "Купить" -> Выбор размера
@dp.callback_query(F.data.startswith("buy_"))
async def start_buy_process(callback: types.CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.split("_")[1])
    product = get_product(prod_id)
    
    if not product:
        await callback.answer("Товар не найден.")
        return
        
    # ИСПРАВЛЕНИЕ: размеры находятся под индексом 4 (а под 3 была цена)
    sizes_list = [s.strip() for s in product[4].split(",")]
    
    keyboard = []
    row = []
    for s in sizes_list:
        row.append(InlineKeyboardButton(text=s, callback_data=f"size_{s}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    await state.update_data(product_id=prod_id, product_name=product[1], price=product[3])
    await state.set_state(OrderState.selecting_size)
    
    await callback.message.answer("Выберите ваш размер:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    
# Выбрали размер -> Просим ФИО
@dp.callback_query(OrderState.selecting_size, F.data.startswith("size_"))
async def process_size(callback: types.CallbackQuery, state: FSMContext):
    selected_size = callback.data.split("_")[1]
    await state.update_data(size=selected_size)
    
    await state.set_state(OrderState.entering_fio)
    await callback.message.answer("Введите ваше **ФИО** для отправки (например: Иванов Иван Иванович):", parse_mode="Markdown")

# Ввели ФИО -> Просим номер телефона
@dp.message(OrderState.entering_fio)
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await state.set_state(OrderState.entering_phone)
    await message.answer("Введите ваш **номер телефона** (например: +380971234567):", parse_mode="Markdown")

# Ввели номер -> Просим город
@dp.message(OrderState.entering_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(OrderState.entering_city)
    await message.answer("Укажите ваш **город**:", parse_mode="Markdown")

# Ввели город -> Просим отделение НП
@dp.message(OrderState.entering_city)
async def process_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(OrderState.entering_post)
    await message.answer("Укажите **номер отделения Новой Почты** (например: Отделение №5 или Поштомат №1234):", parse_mode="Markdown")

# Завершение заказа -> Уведомление клиенту и админу
@dp.message(OrderState.entering_post)
async def process_post(message: types.Message, state: FSMContext):
    await state.update_data(post_office=message.text)
    order_data = await state.get_data()
    
    # Сообщение покупателю
    await message.answer(
        "✅ **Спасибо! Ваш заказ принят.**\n"
        "Наш менеджер свяжется с вами для подтверждения оплаты и отправки.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    # Формируем отчёт для админа
    username = f"@{message.from_user.username}" if message.from_user.username else "Не указан"
    admin_message = (
        f"🚨 **НОВЫЙ ЗАКАЗ!**\n\n"
        f"📦 **Товар:** {order_data['product_name']}\n"
        f"📏 **Размер:** {order_data['size']}\n"
        f"💵 **Цена:** {order_data['price']} ₴\n\n"
        f"👤 **ФИО:** {order_data['fio']}\n"
        f"📞 **Тел:** {order_data['phone']}\n"
        f"🏙 **Город:** {order_data['city']}\n"
        f"📍 **НП:** {order_data['post_office']}\n"
        f"💬 **Профиль:** {username} (ID: `{message.from_user.id}`)"
    )
    
    # Отправляем админу
    try:
        await bot.send_message(chat_id=config.ADMIN_ID, text=admin_message, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка при отправке админу: {e}")
        
    await state.clear()

async def main():
    init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())