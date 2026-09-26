import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "⚡ **MEDIA FETCH ENGINE**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "✨ *No ads. No watermarks. Pure content.*\n\n"
        "🔗 **Supported platforms:**\n"
        "• 🎵 TikTok (Videos & Photo Slideshows)\n"
        "• 📸 Instagram (Reels / Posts)\n"
        "• 🎬 YouTube (Shorts / Video)\n\n"
        "👉 *Just drop any link below and get your file instantly!*"
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
    
    # Префікс для збереження файлів користувача
    file_prefix = f"downloads_{message.from_user.id}"
    
    # Налаштування yt-dlp для максимальної сумісності (включно з фото та відео)
    ydl_opts = {
        'outtmpl': f'{file_prefix}_%(id)s_%(autonumber)s.%(ext)s',
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
        'skip_download': False,
    }
    
    try:
        await asyncio.sleep(0.5)
        await status_msg.edit_text("⚙️ **Analyzing stream & extracting media...**", parse_mode="Markdown")
        
        loop = asyncio.get_running_loop()
        extracted_info = {}
        
        def download():
            nonlocal extracted_info
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                extracted_info = info
                
        await loop.run_in_executor(None, download)
        
        # Шукаємо всі файли, які завантажилися для цього користувача
        downloaded_files = [f for f in os.listdir() if f.startswith(file_prefix)]
        
        if not downloaded_files:
            await status_msg.edit_text("❌ **Error:** Could not extract media from this link.")
            return

        await status_msg.edit_text("📤 **Preparing files for delivery...**", parse_mode="Markdown")
        
        # Перевіряємо, чи це набір фотографій (slideshow) чи звичайне відео
        photos = [f for f in downloaded_files if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
        videos = [f for f in downloaded_files if f.endswith(('.mp4', '.mkv', '.webm'))]
        
        done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
        ])

        if photos and len(photos) > 1:
            # Якщо це слайдшоу з фотографій з TikTok
            media_group = []
            for i, photo_file in enumerate(photos[:10]): # Телеграм дозволяє до 10 фото в альбом
                with open(photo_file, "rb") as pf:
                    photo_bytes = pf.read()
                    input_file = BufferedInputFile(photo_bytes, filename=f"slide_{i}.jpg")
                    caption = "✅ **Successfully extracted slideshow!**\n⚡ *Powered by your personal bot.*" if i == 0 else None
                    media_group.append(InputMediaPhoto(media=input_file, caption=caption, parse_mode="Markdown"))
            
            await message.answer_media_group(media=media_group)
            await message.answer("✨ *All slides downloaded successfully!*", reply_markup=done_keyboard, parse_mode="Markdown")
            
        elif videos:
            # Якщо це звичайне відео
            video_file_path = videos[0]
            with open(video_file_path, "rb") as video_file:
                video_bytes = video_file.read()
                input_file = BufferedInputFile(video_bytes, filename="media.mp4")
                
                await message.answer_video(
                    video=input_file,
                    caption="✅ **Successfully extracted!**\n⚡ *Powered by your personal bot.*",
                    reply_markup=done_keyboard,
                    parse_mode="Markdown"
                )
        else:
            await status_msg.edit_text("❌ **Error:** Unsupported media format.")

        # Очищуємо всі тимчасові файли
        for file in downloaded_files:
            if os.path.exists(file):
                os.remove(file)
                
        await status_msg.delete()
            
    except Exception as e:
        logging.error(f"Error: {e}")
        try:
            await status_msg.edit_text("⚠️ **Failed:** The file might be too large (>50MB) or restricted.")
        except Exception:
            pass
        # Прибираємо сміття у разі помилки
        for file in os.listdir():
            if file.startswith(file_prefix):
                try:
                    os.remove(file)
                except:
                    pass

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Media bot with slideshow support is online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    
