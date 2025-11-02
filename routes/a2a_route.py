from fastapi import APIRouter
from datetime import datetime
import base64
import uuid
import logging
import re

from schema.rpc_model import RPCRequest, RPCResponse
from services.pdf_extractor import extract_text
from services.summarizer import summarize_text

router = APIRouter()
logger = logging.getLogger("a2a_summarize")

PDF_URL_PATTERN = re.compile(r"https:\/\/media\.telex\.im\/[^\s'\"]+")


@router.post("/a2a/summarize", tags=["Agent"], description="Summarize PDF via A2A JSON-RPC",
             response_model=RPCResponse)
async def a2a_summarize(req: RPCRequest) -> RPCResponse:
    try:
        logger.warning(f"Received request: method={req.method}, id={req.id}")

        if req.method not in ["summarize/pdf", "message/send"]:
            return RPCResponse(
                id=req.id,
                error={"message": f"Unknown method {req.method}"}
            )

        msg = req.params.message
        msg.taskId = msg.taskId or f"task-{uuid.uuid4()}"
        task_id = msg.taskId
        message_id = f"msg-{uuid.uuid4()}"
        artifact_id = f"artifact-summary-{uuid.uuid4()}"

        if not msg.parts:
            logger.error("No message parts provided")
            return RPCResponse(id=req.id, error={"message": "No message parts provided"})

        file_url = None
        for part in msg.parts:
            if getattr(part, "text", None):
                match = PDF_URL_PATTERN.search(part.text)
                if match:
                    file_url = match.group(0)
                    break
            if getattr(part, "data", None):
                for d in part.data:
                    if isinstance(d, dict) and "text" in d:
                        match = PDF_URL_PATTERN.search(d["text"])
                        if match:
                            file_url = match.group(0)
                            break
                if file_url:
                    break

        if not file_url:
            logger.warning("No file URL found in message parts")
            return RPCResponse(
                id=req.id,
                error={"message": "No PDF URL found in message parts"}
            )

        logger.warning(f"Extracting text from URL: {file_url}")

        try:
            text = await extract_text(file_url)
        except Exception as e:
            logger.exception("Failed to extract text")
            return RPCResponse(
                id=req.id,
                error={"message": f"Failed to extract text: {str(e)}"}
            )

        try:
            logger.warning(f"Summarizing text (length={len(text)})")
            summary = await summarize_text(text)
        except Exception as e:
            logger.exception("Failed to summarize text")
            return RPCResponse(
                id=req.id,
                error={"message": f"Failed to summarize text: {str(e)}"}
            )

        now = datetime.utcnow().isoformat() + "Z"
        result = {
            "id": task_id,
            "contextId": str(uuid.uuid4()),
            "status": {
                "state": "completed",
                "timestamp": now,
                "message": {
                    "messageId": message_id,
                    "role": "agent",
                    "parts": [{"kind": "text", "text": summary}],
                    "kind": "message",
                    "taskId": task_id
                }
            },
            "artifacts": [
                {
                    "artifactId": artifact_id,
                    "name": "summary",
                    "parts": [{"kind": "text", "text": summary}]
                }
            ],
            "kind": "task"
        }

        logger.warning(f"Returning summarized response for taskId={task_id}")
        return RPCResponse(id=req.id, result=result)

    except Exception as e:
        logger.exception("Unhandled exception in a2a_summarize")
        return RPCResponse(
            id=req.id,
            error={"message": f"Internal server error: {str(e)}"}
        )
