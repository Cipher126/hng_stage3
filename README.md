# 🧠 Telex A2A PDF Summarizer Agent

An intelligent AI agent built with FastAPI that extracts and summarizes text from PDF files (both cloud-hosted and direct byte uploads). It integrates seamlessly with Telex.im using the A2A (Agent-to-Agent) protocol — allowing users to send documents and receive structured summaries inside Telex workflows.

## 🚀 Features

- 📄 Extracts text from both PDF URLs and base64-encoded file bytes
- 🧠 Generates clean, structured summaries of long documents  
- 🌐 Fully compatible with Telex A2A protocol
- ⚡ Built with FastAPI for async performance
- ☁️ Ready for deployment on Render, Railway, Fly.io, or any cloud hosting

## 🧩 Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- PyPDF2 / pdfminer.six (for text extraction) 
- OpenAI / Gemini / HuggingFace model (for text summarization)
- Telex A2A integration

## 📦 Installation

Clone this repository and install dependencies:

```bash
git clone https://github.com/cipher126/hng_stage3.git
cd hng_stage3
pip install -r requirements.txt
```

Run the development server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```bash
GEMINI_API_KEY=your_gemini_key_here
```

## 🧭 API Routes

### POST /a2a/summarize

Main entry point for Telex.

**Request Body Examples:**

For PDF URL:
```json
{
  "jsonrpc": "2.0",
  "id": "test-002",
  "method": "summarize",
  "params": {
    "url": "https://arxiv.org/pdf/2107.13586.pdf"
  }
}
```

For Base64 encoded PDF:
```json
{
  "jsonrpc": "2.0", 
  "id": "test-002",
  "method": "summarize",
  "params": {
    "file_bytes": "JVBERi0xLjQKJc..."
  }
}
```

**Response Example:**
```json
{
  "jsonrpc": "2.0",
  "id": "test-001", 
  "result": {
    "summary": "This document discusses a deep learning approach to..."
  }
}
```

## 🧩 Telex Integration

Connect the agent to your Telex workflow:

```json
{
  "nodes": [
    {
      "id": "summarizer_agent",
      "name": "Document Summarizer", 
      "type": "a2a/generic-a2a-node",
      "url": "https://your-deployed-domain.com/a2a/summarize"
    }
  ]
}
```

## 🪶 Example Output

**Input:**
Financial report (10 pages)

**Output (summarized):**
The company recorded $945 in net income for FY2021, distributed $500 in dividends, and grew retained earnings to $1,265. Assets totaled $13,060, with equipment ($10,700) as the largest asset...

## 📖 Project Structure
```
.
├── main.py
├── routes/
│   └── a2a_summarize.py
├── services/
│   ├── pdf_extractor.py
│   └── summarizer.py
├── schema/
│   ├── rpc_model.py
├── requirements.txt
├── Procfile
└── README.md
```

## 🔧 Procfile (for Render/Railway)

```
web: uvicorn main:app --host 0.0.0.0 --port 8001
```

## 🌍 Deployment

Deploy on Render, Railway, or Fly.io:

```bash
git add .
git commit -m "Deploy Telex A2A Summarizer Agent"
git push origin main
```

Add your deployment URL to your Telex workflow node to complete the integration.
