import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
import yt_dlp

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "// SYSTEM.READY\n\n"
        "Send target URL (TikTok, Instagram, YouTube).\n"
        "Extracting raw streams."
    )

@dp.message(F.text.startswith("http"))
async def download_media(message: Message):
    url = message.text.strip()
    
    status_msg = await message.answer(">[0%] Parsing link...")
    
    output_filename = f"downloads_{message.from_user.id}.mp4"
    
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'max_filesize': 50 * 1024 * 1024,
        'quiet': True,
    }
    
    try:
        loop = asyncio.get_running_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        await loop.run_in_executor(None, download)
        
        if os.path.exists(output_filename):
            await status_msg.edit_text(">[50%] Transmitting payload...")
            
            with open(output_filename, "rb") as video_file:
                video_bytes = video_file.read()
                input_file = BufferedInputFile(video_bytes, filename="media.mp4")
                
                await message.answer_video(
                    video=input_file,
                    caption="[OK]"
                )
            
            os.remove(output_filename)
            await status_msg.delete()
        else:
            await status_msg.edit_text("[ERROR]: Extraction failed.")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        try:
            await status_msg.edit_text("[ERROR]: Limit exceeded or restricted.")
        except Exception:
            pass
        if os.path.exists(output_filename):
            os.remove(output_filename)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Core system online.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
    
