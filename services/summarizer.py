import os
import asyncio

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai

from services.pdf_extractor import logger

load_dotenv()


async def summarize_text(text: str):
    try:
        prompt = (f"Summarize this text clearly, concisely and point out key points from it like "
                  f"notable sections:\n\n{text}")

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-pro",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"exception occurred in summarize text")
        raise HTTPException(status_code=500, detail=e)
