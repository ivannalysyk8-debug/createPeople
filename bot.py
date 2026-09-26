import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
        "• 🎵 TikTok (Video streams)\n"
        "• 📸 Instagram Reels\n"
        "• 🎬 YouTube Shorts / Video\n\n"
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
    
    output_filename = f"downloads_{message.from_user.id}.mp4"
    
    # Жорсткі параметри, щоб качати виключно оптимальні за розміром відео (до 50мб)
    ydl_opts = {
        'format': 'best[filesize<50M]/best[ext=mp4]/best',
        'outtmpl': output_filename,
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        await asyncio.sleep(0.3)
        await status_msg.edit_text("⚙️ **Processing video stream...**", parse_mode="Markdown")
        
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, download)
        
        if os.path.exists(output_filename):
            file_size = os.path.getsize(output_filename)
            
            # Перевірка на обмеження Telegram (50 МБ)
            if file_size > 50 * 1024 * 1024:
                await status_msg.edit_text("⚠️ **Error:** Video file is larger than 50MB limit.")
                os.remove(output_filename)
                return

            await status_msg.edit_text("📤 **Preparing file for delivery...**", parse_mode="Markdown")
            
            with open(output_filename, "rb") as video_file:
                video_bytes = video_file.read()
                input_file = BufferedInputFile(video_bytes, filename="media.mp4")
                
                done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
                ])
                
                await message.answer_video(
                    video=input_file,
                    caption="✅ **Successfully extracted!**\n⚡ *Clean video without watermarks.*",
                    reply_markup=done_keyboard,
                    parse_mode="Markdown"
                )
            
            os.remove(output_filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ **Error:** Could not process this link. It might be a photo slideshow or a private post.")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        try:
            await status_msg.edit_text("⚠️ **Failed:** This link format is not supported or restricted.")
        except Exception:
            pass
        if os.path.exists(output_filename):
            os.remove(output_filename)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Stable Media bot is online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    
