from fastapi import APIRouter, BackgroundTasks
from datetime import datetime
import uuid
import logging
import re
import httpx

from schema.rpc_model import RPCRequest, RPCResponse
from services.pdf_extractor import extract_text
from services.summarizer import summarize_text

router = APIRouter()
logger = logging.getLogger("a2a_summarize")

PDF_URL_PATTERN = re.compile(r"https:\/\/media\.telex\.im\/[^\s'\"]+")


async def send_webhook_response(webhook_url: str, token: str, payload: dict):
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, headers=headers, timeout=30.0)
            logger.info(f"Webhook response: status={response.status_code}, body={response.text}")
    except Exception as e:
        logger.exception(f"Failed to send webhook response: {e}")


async def process_summarization(req_id: str, task_id: str, file_url: str, webhook_config: dict):
    try:
        logger.info(f"Background processing started for task {task_id}")

        logger.info(f"Extracting text from URL: {file_url}")
        text = await extract_text(file_url)

        logger.info(f"Summarizing text (length={len(text)})")
        summary = await summarize_text(text)

        message_id = f"msg-{uuid.uuid4()}"
        artifact_id = f"artifact-summary-{uuid.uuid4()}"
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

        webhook_payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }

        logger.info(f"Sending result to webhook for taskId={task_id}")
        await send_webhook_response(
            webhook_config["url"],
            webhook_config["token"],
            webhook_payload
        )

    except Exception as e:
        logger.exception(f"Error in background processing for task {task_id}")

        error_payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Processing failed: {str(e)}"
            }
        }

        await send_webhook_response(
            webhook_config["url"],
            webhook_config["token"],
            error_payload
        )


@router.post("/a2a/summarize", tags=["Agent"], description="Summarize PDF via A2A JSON-RPC")
async def a2a_summarize(req: RPCRequest, background_tasks: BackgroundTasks) -> RPCResponse:
    try:
        logger.info(f"Received request: method={req.method}, id={req.id}")

        if req.method not in ["summarize/pdf", "message/send"]:
            return RPCResponse(
                id=req.id,
                error={"message": f"Unknown method {req.method}"}
            )

        msg = req.params.message
        task_id = msg.taskId or f"task-{uuid.uuid4()}"
        msg.taskId = task_id

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

        is_blocking = req.params.configuration.blocking if hasattr(req.params, 'configuration') else True
        webhook_config = None

        if hasattr(req.params, 'configuration') and hasattr(req.params.configuration, 'pushNotificationConfig'):
            webhook_config = {
                "url": req.params.configuration.pushNotificationConfig.url,
                "token": req.params.configuration.pushNotificationConfig.token
            }

        if not is_blocking and webhook_config:
            logger.info(f"Non-blocking mode: scheduling background task for {task_id}")

            background_tasks.add_task(
                process_summarization,
                req.id,
                task_id,
                file_url,
                webhook_config
            )

            return RPCResponse(
                id=req.id,
                result={
                    "taskId": task_id,
                    "status": "processing",
                    "message": "PDF summarization in progress"
                }
            )

        logger.info("Blocking mode: processing synchronously")

        try:
            logger.info(f"Extracting text from URL: {file_url}")
            text = await extract_text(file_url)
        except Exception as e:
            logger.exception("Failed to extract text")
            return RPCResponse(
                id=req.id,
                error={"message": f"Failed to extract text: {str(e)}"}
            )

        try:
            logger.info(f"Summarizing text (length={len(text)})")
            summary = await summarize_text(text)
        except Exception as e:
            logger.exception("Failed to summarize text")
            return RPCResponse(
                id=req.id,
                error={"message": f"Failed to summarize text: {str(e)}"}
            )

        message_id = f"msg-{uuid.uuid4()}"
        artifact_id = f"artifact-summary-{uuid.uuid4()}"
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

        logger.info(f"Returning summarized response for taskId={task_id}")
        return RPCResponse(id=req.id, result=result)

    except Exception as e:
        logger.exception("Unhandled exception in a2a_summarize")
        return RPCResponse(
            id=req.id,
            error={"message": f"Internal server error: {str(e)}"}
        )