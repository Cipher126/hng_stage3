from fastapi import FastAPI

from routes.a2a_route import router



app = FastAPI(
    title="PDF Summarizer Agent",
    version="1.0",
    description="A simple pdf summarizer agent for the hng internship stage 3 task which is to demonstrate "
                "a2a protocol with integration with telex.im and i built it using fastAPI and google"
                "gemini-2.5-pro"
)

@app.get('/')
async def root():
    return {
        "message": "welcome to the pdf summarizer agent",
        "API_docs": '/docs'
    }

app.include_router(router)