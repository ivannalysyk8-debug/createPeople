import asyncio
import logging
import os
import sys
import aiohttp
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
        "• 🎵 TikTok (Videos, Photo Slides & Audio)\n"
        "• 📸 Instagram Reels\n"
        "• 🎬 YouTube Shorts / Video\n\n"
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
    
    output_filename = f"downloads_{message.from_user.id}.mp4"
    
    # Налаштування yt-dlp з урахуванням сучасних обмежень TikTok та обходом блокувань
    ydl_opts = {
        'format': 'best[filesize<50M]/best',
        'outtmpl': output_filename,
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'tiktok': {
                'app_version': '35.1.1',
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.tiktok.com/',
        }
    }
    
    try:
        await asyncio.sleep(0.3)
        await status_msg.edit_text("⚙️ **Bypassing platform restrictions...**", parse_mode="Markdown")
        
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, download)
        
        # Перевіряємо, чи завантажилося відео або якісь файли
        downloaded_files = [f for f in os.listdir() if f.startswith(f"downloads_{message.from_user.id}")]
        
        if downloaded_files:
            # Шукаємо відео
            videos = [f for f in downloaded_files if f.endswith(('.mp4', '.mkv', '.webm', '.mov'))]
            photos = [f for f in downloaded_files if f.endswith(('.jpg', '.jpeg', '.png', '.webp'))]
            
            done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
            ])

            if videos:
                await status_msg.edit_text("📤 **Preparing media for delivery...**", parse_mode="Markdown")
                with open(videos[0], "rb") as vf:
                    input_file = BufferedInputFile(vf.read(), filename="media.mp4")
                    await message.answer_video(
                        video=input_file,
                        caption="✅ **Successfully extracted!**\n⚡ *Clean media without watermarks.*",
                        reply_markup=done_keyboard,
                        parse_mode="Markdown"
                    )
            elif len(photos) > 1:
                # Якщо це слайдшоу з фотографій
                await status_msg.edit_text("📤 **Preparing slideshow photos...**", parse_mode="Markdown")
                media_group = []
                for i, photo_file in enumerate(photos[:10]):
                    with open(photo_file, "rb") as pf:
                        input_file = BufferedInputFile(pf.read(), filename=f"slide_{i}.jpg")
                        caption = "✅ **TikTok Slideshow extracted!**" if i == 0 else None
                        media_group.append(InputMediaPhoto(media=input_file, caption=caption, parse_mode="Markdown"))
                await message.answer_media_group(media=media_group)
                await message.answer("✨ *All slides delivered successfully!*", reply_markup=done_keyboard, parse_mode="Markdown")
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
                await status_msg.edit_text("❌ **Error:** No media stream found in this link.")
                
            # Очищуємо тимчасові файли
            for f in downloaded_files:
                if os.path.exists(f):
                    os.remove(f)
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ **Error:** Could not process this link. Please check if it's public.")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        try:
            await status_msg.edit_text("⚠️ **Failed:** TikTok is currently blocking direct requests for this specific post. Try another link.")
        except Exception:
            pass
        for f in os.listdir():
            if f.startswith(f"downloads_{message.from_user.id}"):
                try: os.remove(f)
                except: pass

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Media bot is online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
            
