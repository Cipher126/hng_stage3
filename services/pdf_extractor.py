import logging
import fitz
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(file_bytes: bytes):
    try:
        text = ""
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text")
        if not text.strip():
            raise ValueError("No readable text found in PDF.")
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to extract text from PDF")


async def extract_text_from_url(url: str):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to fetch PDF (status {response.status_code})")

        return extract_text_from_pdf_bytes(response.content)
    except httpx.RequestError as e:
        logger.error(f"Network error downloading PDF: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Error downloading PDF")
    except Exception as e:
        logger.error(f"Extraction from URL failed: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to extract text from remote PDF")


async def extract_text(source: str | bytes):
    if isinstance(source, bytes):
        return extract_text_from_pdf_bytes(source)
    elif isinstance(source, str) and source.startswith(("http://", "https://")):
        return await extract_text_from_url(source)
    else:
        raise HTTPException(status_code=400, detail="Invalid source type. Must be bytes or URL string.")
