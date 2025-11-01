from fastapi import APIRouter
from datetime import datetime
import base64
import uuid
import logging

from schema.rpc_model import RPCRequest, RPCResponse
from services.pdf_extractor import extract_text
from services.summarizer import summarize_text

router = APIRouter()
logger = logging.getLogger("a2a_summarize")


@router.post("/a2a/summarize", tags=["Agent"], description="Summarize PDF via A2A JSON-RPC")
async def a2a_summarize(req: RPCRequest) -> RPCResponse:
    try:
        logger.warning(req)
        logger.warning("Received request: method=%s id=%s", req.method, req.id)

        if req.method not in ["summarize/pdf", "message/send"]:
            logger.warning("Unknown method: %s", req.method)
            return RPCResponse(
                id=req.id,
                error={"message": f"Unknown method {req.method}"}
            )

        msg = req.params.message
        # Ensure taskId exists
        msg.taskId = msg.taskId or f"task-{uuid.uuid4()}"
        task_id = msg.taskId
        message_id = f"msg-{uuid.uuid4()}"
        artifact_id = f"artifact-summary-{uuid.uuid4()}"

        part = msg.parts[0] if msg.parts else None
        if not part:
            logger.error("No message parts provided")
            return RPCResponse(
                id=req.id,
                error={"message": "No message parts provided"}
            )

        # Extract text
        try:
            if part.file_url:
                logger.info("Extracting text from URL: %s", part.file_url)
                text = await extract_text(part.file_url)
            elif part.file_bytes:
                logger.info("Extracting text from uploaded bytes")
                file_bytes = base64.b64decode(part.file_bytes)
                text = await extract_text(file_bytes)
            else:
                logger.error("No file URL or bytes provided")
                return RPCResponse(
                    id=req.id,
                    error={"message": "No file URL or bytes provided"}
                )
        except Exception as e:
            logger.exception("Failed to extract text")
            return RPCResponse(
                id=req.id,
                error={"message": f"Failed to extract text: {str(e)}"}
            )

        # Summarize
        try:
            logger.info("Summarizing text (length=%d)", len(text))
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

        logger.info("Returning summarized response for taskId=%s", task_id)
        return RPCResponse(id=req.id, result=result)

    except Exception as e:
        logger.exception("Unhandled exception in a2a_summarize")
        return RPCResponse(
            id=req.id,
            error={"message": f"Internal server error: {str(e)}"}
        )
