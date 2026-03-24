# SEO Metadata Generator API

A high-performance FastAPI service that uses AI (Groq + LangChain) to transform document content into SEO-optimized metadata.

## 🚀 Features

- **Document Parsing**: Automatically extracts text from uploaded `.docx` files and converts them into structured Markdown for easier AI analysis.
- **AI-Driven SEO**: Generates professional meta titles, descriptions, and URL slugs based on the provided content.
- **Targeted Optimization**: Accepts a `primary_keyword` in the request to ensure the metadata is focused on your target search term.
- **Structured Output**: Uses Pydantic for strict schema validation, ensuring consistent and predictable JSON results every time.
- **High Performance**: Powered by Groq's LPU inference engine for lightning-fast results.

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **AI Integration**: [LangChain](https://www.langchain.com/) + [Groq](https://groq.com/)
- **Document Processing**: `python-docx` and `docling`
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/latest/)

## 📦 Installation

1.  **Clone the repository** (if you haven't already).
2.  **Navigate to the backend directory**:
    ```bash
    cd backend
    ```
3.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Set up your environment**:
    Create an `.env` file in the `environment/` directory with your Groq API key:
    ```env
    GROQ_API_KEY=your_key_here
    ```

## 🏃 Running the Application

To start the development server, run:
```bash
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

## 📡 API Usage

### Generate SEO Metadata
**Endpoint**: `POST /api/v1/generate-metadata`

**Input (multipart/form-data)**:
- `file`: Your `.docx` document.
- `primary_keyword`: Your target search term.

**Example Response**:
```json
{
  "meta_title": "10 Remote Work Productivity Tips | Grow Your Business",
  "meta_description": "Are you struggling to stay productive while working from home? Learn the 10 most effective remote work strategies used by successful founders.",
  "meta_routes": [
    "remote-work-productivity-tips",
    "how-to-stay-productive-at-home",
    "work-from-home-strategies"
  ]
}
```

