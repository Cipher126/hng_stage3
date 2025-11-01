from fastapi import APIRouter, HTTPException
from datetime import datetime
import base64
import uuid

from schema.rpc_model import RPCRequest, RPCResponse
from services.pdf_extractor import extract_text
from services.summarizer import summarize_text

router = APIRouter()


@router.post("/a2a/summarize", tags=["Agent"], description="Summarize PDF via A2A JSON-RPC")
async def a2a_summarize(req: RPCRequest) -> RPCResponse:
    try:
        if req.method != "summarize/pdf":
            return RPCResponse(
                id=req.id,
                error={"message": f"Unknown method {req.method}"}
            )

        msg = req.params.message
        part = msg.parts[0] if msg.parts else None
        if not part:
            raise HTTPException(status_code=400, detail="No message parts provided")

        if part.file_url:
            text = await extract_text(part.file_url)
        elif part.file_bytes:
            file_bytes = base64.b64decode(part.file_bytes)
            text = await extract_text(file_bytes)
        else:
            raise HTTPException(status_code=400, detail="No file URL or bytes provided")

        summary = await summarize_text(text)

        now = datetime.utcnow().isoformat() + "Z"
        task_id = msg.taskId or f"task-{uuid.uuid4()}"
        message_id = f"msg-{uuid.uuid4()}"
        artifact_id = f"artifact-summary-{uuid.uuid4()}"

        result = {
            "id": task_id,
            "contextId": str(uuid.uuid4()),
            "status": {
                "state": "completed",
                "timestamp": now,
                "message": {
                    "messageId": message_id,
                    "role": "agent",
                    "parts": [
                        {
                            "kind": "text",
                            "text": summary
                        }
                    ],
                    "kind": "message",
                    "taskId": task_id
                }
            },
            "artifacts": [
                {
                    "artifactId": artifact_id,
                    "name": "summary",
                    "parts": [
                        {
                            "kind": "text",
                            "text": summary
                        }
                    ]
                }
            ],
            "kind": "task"
        }

        return RPCResponse(id=req.id, result=result)

    except HTTPException as he:
        return RPCResponse(id=req.id, error={"message": he.detail})
    except Exception as e:
        return RPCResponse(id=req.id, error={"message": str(e)})
