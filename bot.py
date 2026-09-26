import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, BufferedInputFile, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery, InputMediaPhoto, InputMediaDocument
)
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словник для тимчасового зберігання шляхів до файлів користувачів перед вибором режиму
user_pending_downloads = {}

@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "⚡ **MEDIA FETCH ENGINE**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "✨ *No ads. No watermarks. Pure content.*\n\n"
        "🔗 **Supported platforms:**\n"
        "• 🎵 TikTok (Videos, Photo Slides & Audio)\n"
        "• 📸 Instagram (Reels / Posts)\n"
        "• 🎬 YouTube (Shorts / Video)\n\n"
        "👉 *Just drop any link below and get your files!*"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Send a link", callback_data="ping")]
    ])
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "ping")
async def callback_ping(callback: CallbackQuery):
    await callback.answer("I'm ready! Just send me the URL 📥", show_alert=True)

@dp.message(F.text.startswith("http"))
async def download_media(message: Message):
    url = message.text.strip()
    status_msg = await message.answer("🔄 **Connecting to source...**", parse_mode="Markdown")
    
    file_prefix = f"downloads_{message.from_user.id}"
    
    ydl_opts = {
        'outtmpl': f'{file_prefix}_%(id)s_%(autonumber)s.%(ext)s',
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
    }
    
    try:
        await asyncio.sleep(0.3)
        await status_msg.edit_text("⚙️ **Analyzing stream & extracting media...**", parse_mode="Markdown")
        
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, download)
        
        downloaded_files = [f for f in os.listdir() if f.startswith(file_prefix)]
        
        if not downloaded_files:
            await status_msg.edit_text("❌ **Error:** Could not extract media from this link.")
            return

        photos = [f for f in downloaded_files if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        videos = [f for f in downloaded_files if f.endswith(('.mp4', '.mkv', '.webm'))]
        audio = [f for f in downloaded_files if f.endswith(('.mp3', '.m4a', '.aac', '.opus'))]

        # Якщо це TikTok-слайдшоу (кілька фото)
        if len(photos) > 1:
            await status_msg.delete()
            
            # Зберігаємо список файлів для цього користувача в пам'яті
            user_pending_downloads[message.from_user.id] = {
                'photos': photos,
                'audio': audio,
                'prefix': file_prefix
            }
            
            choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📁 Send as Slideshow (Album)", callback_data="mode_album")],
                [InlineKeyboardButton(text="📦 Send Separately + Audio Track", callback_data="mode_separate")]
            ])
            
            await message.answer(
                "✨ **TikTok Slideshow detected!**\n"
                "How would you like to receive the content?",
                reply_markup=choice_keyboard,
                parse_mode="Markdown"
            )
            return

        # Якщо це звичайне відео або одне фото
        await status_msg.edit_text("📤 **Preparing file for delivery...**", parse_mode="Markdown")
        done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
        ])

        if videos:
            with open(videos[0], "rb") as vf:
                input_file = BufferedInputFile(vf.read(), filename="media.mp4")
                await message.answer_video(
                    video=input_file,
                    caption="✅ **Successfully extracted!**",
                    reply_markup=done_keyboard,
                    parse_mode="Markdown"
                )
        elif photos:
            with open(photos[0], "rb") as pf:
                input_file = BufferedInputFile(pf.read(), filename="photo.jpg")
                await message.answer_photo(
                    photo=input_file,
                    caption="✅ **Successfully extracted!**",
                    reply_markup=done_keyboard,
                    parse_mode="Markdown"
                )
        else:
            await status_msg.edit_text("❌ **Error:** Unsupported media format.")

        # Очистка
        for file in downloaded_files:
            if os.path.exists(file):
                os.remove(file)
                
    except Exception as e:
        logging.error(f"Error: {e}")
        try:
            await status_msg.edit_text("⚠️ **Failed:** File might be too large or restricted.")
        except Exception:
            pass
        for file in os.listdir():
            if file.startswith(file_prefix):
                try: os.remove(file)
                except: pass

# Обробка вибору: Слайд-шоу (Альбом)
@dp.callback_query(F.data == "mode_album")
async def callback_mode_album(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_pending_downloads:
        await callback.answer("⚠️ Session expired. Please send the link again.", show_alert=True)
        return
        
    data = user_pending_downloads[user_id]
    photos = data['photos']
    
    await callback.message.edit_text("📤 **Sending as a slideshow album...**", parse_mode="Markdown")
    
    try:
        media_group = []
        for i, photo_file in enumerate(photos[:10]):
            if os.path.exists(photo_file):
                with open(photo_file, "rb") as pf:
                    input_file = BufferedInputFile(pf.read(), filename=f"slide_{i}.jpg")
                    caption = "✅ **Slideshow extracted!**" if i == 0 else None
                    media_group.append(InputMediaPhoto(media=input_file, caption=caption, parse_mode="Markdown"))
        
        if media_group:
            await callback.message.answer_media_group(media=media_group)
            
        done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
        ])
        await callback.message.answer("✨ *Done!*", reply_markup=done_keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Album error: {e}")
        await callback.message.answer("❌ Error sending album.")
    
    # Прибираємо файли і дані
    for file in os.listdir():
        if file.startswith(data['prefix']):
            try: os.remove(file)
            except: pass
    del user_pending_downloads[user_id]

# Обробка вибору: Все окремо + аудіо
@dp.callback_query(F.data == "mode_separate")
async def callback_mode_separate(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_pending_downloads:
        await callback.answer("⚠️ Session expired. Please send the link again.", show_alert=True)
        return
        
    data = user_pending_downloads[user_id]
    photos = data['photos']
    audio = data['audio']
    
    await callback.message.edit_text("📤 **Sending photos separately and audio track...**", parse_mode="Markdown")
    
    try:
        # Відправляємо кожну фотографію як окремий документ/фото (щоб не стискалося)
        for i, photo_file in enumerate(photos):
            if os.path.exists(photo_file):
                with open(photo_file, "rb") as pf:
                    input_file = BufferedInputFile(pf.read(), filename=f"photo_{i+1}.jpg")
                    await callback.message.answer_photo(
                        photo=input_file,
                        caption=f"🖼 Photo #{i+1}"
                    )
        
        # Якщо знайшовся аудіотрек треку
        if audio and os.path.exists(audio[0]):
            with open(audio[0], "r+b") as af:
                audio_file = BufferedInputFile(af.read(), filename="tiktok_sound.mp3")
                await callback.message.answer_audio(
                    audio=audio_file,
                    caption="🎵 **Original Audio Track**"
                )
        
        done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
        ])
        await callback.message.answer("✨ *All components extracted successfully!*", reply_markup=done_keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Separate mode error: {e}")
        await callback.message.answer("❌ Error sending files.")
        
    # Прибираємо файли і дані
    for file in os.listdir():
        if file.startswith(data['prefix']):
            try: os.remove(file)
            except: pass
    del user_pending_downloads[user_id]

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Advanced Media bot with choice mode is online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
        
