import asyncio
import io
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from PIL import Image

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Стани для покрокового створення персонажа
class CharacterStates(StatesGroup):
    choosing_hand = State()
    choosing_bottom = State()
    choosing_top = State()
    choosing_hat = State()

# Клавіатури для кожного кроку
def get_hand_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 None", callback_data="hand:none"),
         InlineKeyboardButton(text="🍷 Glass", callback_data="hand:glass")],
        [InlineKeyboardButton(text="💐 Flowers", callback_data="hand:flowers"),
         InlineKeyboardButton(text="⛏️ Pickaxe", callback_data="hand:pickaxe")],
        [InlineKeyboardButton(text="📱 Phone", callback_data="hand:phone"),
         InlineKeyboardButton(text="🎈 Balloons", callback_data="hand:balloons")],
        [InlineKeyboardButton(text="🪄 Wand", callback_data="hand:wand")]
    ])

def get_bottom_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 None", callback_data="bottom:none"),
         InlineKeyboardButton(text="👖 Jeans", callback_data="bottom:jeans")],
        [InlineKeyboardButton(text="🩳 Shorts", callback_data="bottom:shorts"),
         InlineKeyboardButton(text="🏃‍♂️ Sweatpants", callback_data="bottom:sport")],
        [InlineKeyboardButton(text="👖 Baggy Jeans", callback_data="bottom:baggy"),
         InlineKeyboardButton(text="🩳 Pajama", callback_data="bottom:pajama")]
    ])

def get_top_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 None", callback_data="top:none"),
         InlineKeyboardButton(text="👕 T-Shirt", callback_data="top:tshirt")],
        [InlineKeyboardButton(text="🧥 Longsleeve", callback_data="top:longsleeve"),
         InlineKeyboardButton(text="👕 Pajama Shirt", callback_data="top:pajama_top")]
    ])

def get_hat_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 None", callback_data="hat:none"),
         InlineKeyboardButton(text="💇‍♂️ Hair", callback_data="hat:hair")],
        [InlineKeyboardButton(text="🟠 Donald Hair", callback_data="hat:donald"),
         InlineKeyboardButton(text="👑 Crown", callback_data="hat:crown")],
        [InlineKeyboardButton(text="👒 Bucket Hat", callback_data="hat:panama"),
         InlineKeyboardButton(text="🧢 Cap", callback_data="hat:cap")],
        [InlineKeyboardButton(text="🪖 Hard Hat", callback_data="hat:helmet"),
         InlineKeyboardButton(text="🧑‍🚀 Spacesuit", callback_data="hat:spacesuit")]
    ])

# Функція склеювання шарів через Pillow
def build_character_image(data: dict) -> bytes:
    base = Image.open("assets/base.png").convert("RGBA")
    
    layers = [
        ("bottoms", data.get("bottom")),
        ("tops", data.get("top")),
        ("hats", data.get("hat")),
        ("hands", data.get("hand"))
    ]
    
    for folder, item in layers:
        if item and item != "none":
            layer_path = f"assets/{folder}/{item}.png"
            if os.path.exists(layer_path):
                layer_img = Image.open(layer_path).convert("RGBA")
                base.paste(layer_img, (0, 0), layer_img)
                
    output = io.BytesIO()
    base.save(output, format="PNG")
    output.seek(0)
    return output.getvalue()

@dp.message(CommandStart())
@dp.callback_query(F.data == "restart")
async def cmd_start_handler(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "▪ CHARACTER // BUILDER\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Create your unique custom stickman avatar!\n\n"
        "👉 **Step 1:** What will be in hand?"
    )
    await state.set_state(CharacterStates.choosing_hand)
    
    if isinstance(event, CallbackQuery):
        try:
            await event.message.answer(text, reply_markup=get_hand_keyboard(), parse_mode="Markdown")
            await event.message.delete()
        except Exception:
            await event.message.edit_text(text, reply_markup=get_hand_keyboard(), parse_mode="Markdown")
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_hand_keyboard(), parse_mode="Markdown")

@dp.callback_query(CharacterStates.choosing_hand, F.data.startswith("hand:"))
async def cb_choose_hand(callback: CallbackQuery, state: FSMContext):
    await state.update_data(hand=callback.data.split(":")[1])
    await state.set_state(CharacterStates.choosing_bottom)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "▪ CHARACTER // BUILDER\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👉 **Step 2:** Choose bottom clothing:",
        reply_markup=get_bottom_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(CharacterStates.choosing_bottom, F.data.startswith("bottom:"))
async def cb_choose_bottom(callback: CallbackQuery, state: FSMContext):
    await state.update_data(bottom=callback.data.split(":")[1])
    await state.set_state(CharacterStates.choosing_top)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "▪ CHARACTER // BUILDER\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👉 **Step 3:** Choose top clothing:",
        reply_markup=get_top_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(CharacterStates.choosing_top, F.data.startswith("top:"))
async def cb_choose_top(callback: CallbackQuery, state: FSMContext):
    await state.update_data(top=callback.data.split(":")[1])
    await state.set_state(CharacterStates.choosing_hat)
    await callback.message.edit_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "▪ CHARACTER // BUILDER\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👉 **Step 4:** Choose headwear / hat:",
        reply_markup=get_hat_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(CharacterStates.choosing_hat, F.data.startswith("hat:"))
async def cb_choose_hat(callback: CallbackQuery, state: FSMContext):
    await state.update_data(hat=callback.data.split(":")[1])
    data = await state.get_data()
    
    await callback.message.edit_text("⏳ Rendering your character...", parse_mode="Markdown")
    
    image_bytes = build_character_image(data)
    photo = BufferedInputFile(image_bytes, filename="character.png")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Create Another", callback_data="restart")]
    ])
    
    await callback.message.answer_photo(
        photo=photo,
        caption="✨ **Your custom character is ready!**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.message.delete()
    await state.clear()
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Character builder bot is running!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
      
