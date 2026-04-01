#  Mata Information: AI-Powered SEO Metadata Generator



<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0055ff?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=langchain&logoColor=white" alt="LangChain">
  <img src="https://img.shields.io/badge/Groq-f55036?style=for-the-badge&logo=groq&logoColor=white" alt="Groq">
  <img src="https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="Python">
</p>

---

**Mata Information** is a high-performance, developer-first API that transforms raw documents into high-converting, keyword-rich SEO metadata. By combining **Groq's LPU inference engine** with advanced **token-optimization** and **context-cleaning**, it generates meta titles, descriptions, and URL slugs that increase CTR and boost search rankings.

## 🚀 Key Features

- **🧠 LLM Context Optimizer**: Automatically strips "fluff," disclaimers, and boilerplate from documents to optimize token usage and focus LLM attention on core value.
- **⚡ Lightning Fast Inference**: Integrated with **Groq** for sub-second metadata generation from documents of any size.
- **🎯 Keyword-Centric**: Accepts a `primary_keyword` to ensure every meta field is perfectly aligned with your target SEO strategy.
- **🛡️ Structured & Validated**: Every response is validated using **Pydantic v2**, ensuring your frontend always receives a clean, consistent JSON schema.
- **🏗️ Format Support**: Robust parsing for `.docx` documents using `docling` and `python-docx`.

## 🛠️ Tech Stack

- **Core**: FastAPI (Python 3.10+)
- **Inference**: LangChain + Groq (Llama 3 / Mixtral)
- **Parsing**: `docling`, `python-docx`
- **Validation**: Pydantic v2

## 📦 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/VivekChudasama/Meta-Information.git
cd Meta-Information/backend

# Create & activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create an `.env` file in the `environment/` directory:
```env
GROQ_API_KEY=gsk_your_key_here
```

### 3. Run the Server
```bash
uvicorn app.main:app --reload
```

## 📡 API Usage

### Generate Metadata
**Endpoint**: `POST /api/v1/generate-metadata`

| Field | Type | Description |
| :--- | :--- | :--- |
| `file` | `binary` | The document (`.docx`) to process. |
| `primary_keyword` | `string` | Your target keyword for SEO optimization. |

**Example Response**:
```json
{
    "meta_title": "n8n vs Relevance AI: Which Automation Tool is Right for You?",
    "meta_description": "Compare n8n and Relevance AI to choose the best automation tool for your business. Learn about their key features, pros, and cons, and make an informed decision.",
    "meta_routes": [
        "n8n-vs-relevance-ai",
        "what-is-n8n",
        "what-is-relevance-ai",
        "n8n-vs-relevance-ai-comparison",
        "choosing-the-right-automation-tool"
    ]
}
```