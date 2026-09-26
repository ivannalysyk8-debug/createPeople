import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, BufferedInputFile, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery, InputMediaPhoto
)
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_pending_downloads = {}

@dp.message(CommandStart())
async def cmd_start(message: Message):
    welcome_text = (
        "⚡ **MEDIA FETCH ENGINE**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "✨ *No ads. No watermarks. Pure content.*\n\n"
        "🔗 **Supported platforms:**\n"
        "• 🎵 TikTok (Videos, Slides & Audio)\n"
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
    
    # Налаштування yt-dlp для максимального захоплення медіа та аудіо
    ydl_opts = {
        'outtmpl': f'{file_prefix}_%(id)s_%(autonumber)s.%(ext)s',
        'format': 'best/bestvideo+bestaudio/best',
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
        audios = [f for f in downloaded_files if f.endswith(('.mp3', '.m4a', '.aac', '.opus', '.wav'))]

        # Якщо це слайдшоу (кілька фото)
        if len(photos) > 1:
            await status_msg.delete()
            
            user_pending_downloads[message.from_user.id] = {
                'photos': photos,
                'audios': audios,
                'videos': videos,
                'prefix': file_prefix
            }
            
            choice_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎞️ Slideshow with Music (Video)", callback_data="mode_video")],
                [InlineKeyboardButton(text="📁 Slides Separately + 🎵 Audio", callback_data="mode_separate")]
            ])
            
            await message.answer(
                "✨ **TikTok Slideshow detected!**\n"
                "Choose how you want to receive it:",
                reply_markup=choice_keyboard,
                parse_mode="Markdown"
            )
            return

        # Звичайне відео чи одиночне фото
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

        for file in downloaded_files:
            if os.path.exists(file):
                os.remove(file)
                
    except Exception as e:
        logging.error(f"Error: {e}")
        try:
            await status_msg.edit_text("⚠️ **Failed:** Could not process this link. Try another one.")
        except Exception:
            pass
        for file in os.listdir():
            if file.startswith(file_prefix):
                try: os.remove(file)
                except: pass

# Варіант 1: Слайд-шоу як відео з музикою (або перший наявний відеопотік)
@dp.callback_query(F.data == "mode_video")
async def callback_mode_video(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_pending_downloads:
        await callback.answer("⚠️ Session expired. Please send the link again.", show_alert=True)
        return
        
    data = user_pending_downloads[user_id]
    videos = data['videos']
    photos = data['photos']
    
    await callback.message.edit_text("📤 **Preparing slideshow video...**", parse_mode="Markdown")
    
    try:
        done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
        ])
        
        if videos:
            with open(videos[0], "rb") as vf:
                input_file = BufferedInputFile(vf.read(), filename="slideshow.mp4")
                await callback.message.answer_video(
                    video=input_file,
                    caption="✅ **Slideshow video with music!**",
                    reply_markup=done_keyboard,
                    parse_mode="Markdown"
                )
        else:
            # Якщо відеоверсія не сформувалась автоматично, відправляємо як альбом із повідомленням про музику
            media_group = []
            for i, photo_file in enumerate(photos[:10]):
                if os.path.exists(photo_file):
                    with open(photo_file, "rb") as pf:
                        input_file = BufferedInputFile(pf.read(), filename=f"slide_{i}.jpg")
                        caption = "✅ **Slideshow album**" if i == 0 else None
                        media_group.append(InputMediaPhoto(media=input_file, caption=caption, parse_mode="Markdown"))
            if media_group:
                await callback.message.answer_media_group(media=media_group)
            await callback.message.answer("✨ *Done!*", reply_markup=done_keyboard, parse_mode="Markdown")
            
    except Exception as e:
        logging.error(f"Video mode error: {e}")
        await callback.message.answer("❌ Error sending file.")
    
    for file in os.listdir():
        if file.startswith(data['prefix']):
            try: os.remove(file)
            except: pass
    del user_pending_downloads[user_id]

# Варіант 2: Кожен слайд окремо + аудіо трек окремо
@dp.callback_query(F.data == "mode_separate")
async def callback_mode_separate(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_pending_downloads:
        await callback.answer("⚠️ Session expired. Please send the link again.", show_alert=True)
        return
        
    data = user_pending_downloads[user_id]
    photos = data['photos']
    audios = data['audios']
    
    await callback.message.edit_text("📤 **Sending photos separately and audio track...**", parse_mode="Markdown")
    
    try:
        # Надсилаємо кожне фото окремо
        for i, photo_file in enumerate(photos):
            if os.path.exists(photo_file):
                with open(photo_file, "rb") as pf:
                    input_file = BufferedInputFile(pf.read(), filename=f"photo_{i+1}.jpg")
                    await callback.message.answer_photo(
                        photo=input_file,
                        caption=f"🖼 Photo #{i+1}"
                    )
        
        # Надсилаємо аудіодоріжку, якщо вона є
        if audios and os.path.exists(audios[0]):
            with open(audios[0], "rb") as af:
                audio_file = BufferedInputFile(af.read(), filename="tiktok_audio.mp3")
                await callback.message.answer_audio(
                    audio=audio_file,
                    caption="🎵 **Original Audio Track**"
                )
        
        done_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Download another one", callback_data="ping")]
        ])
        await callback.message.answer("✨ *All components sent successfully!*", reply_markup=done_keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Separate mode error: {e}")
        await callback.message.answer("❌ Error sending files.")
        
    for file in os.listdir():
        if file.startswith(data['prefix']):
            try: os.remove(file)
            except: pass
    del user_pending_downloads[user_id]

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Media bot is online!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    
