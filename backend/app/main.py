import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes.generate import router as generate_router
from app.core.config import settings

from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(
    title="SEO Metadata Generator",
    description="""
### ✨ AI-Powered SEO Metadata Generator
This tool automatically creates optimized SEO titles, descriptions, and URL routes for your content using AI.

---

### **How It Works**
1.  **Open Form**: Click the **green block** endpoint: `POST /api/v1/generate-metadata`
2.  **Click to Start**: Select the **'Try it out'** button on the right side.
3.  **Provide Details**:
    *   **`primary_keyword`** [Required] -> Enter your main keyword here.
    *   **`file`** [Required] -> Upload your **.docx** file.
4.  **Process**: Click the **'Execute'** button below.
5.  Wait a few seconds, and scroll down to view your results!
6.  **Result**: Your optimized SEO data will appear in the **Responses** area below for you to easily copy and use.

**Note: Both fields are mandatory for the AI to generate accurate results.**

---

### **Output Includes**
1.  SEO-optimized title
2.  Meta description
3.  URL-friendly slug
""",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "docExpansion": "full",
    },  # Auto-expands the form and hides schemas
)


@app.get("/swagger-custom.css", include_in_schema=False)
async def swagger_custom_css():
    from fastapi.responses import Response

    content = """
    /* Hide curl command, request URL, scheme container, models */
    .curl-command,
    .request-url,
    .scheme-container,
    .models,
    .model-container,
    .parameter__empty_value_recipient { display: none !important; }

    /* Hide the static "Responses" section (200/422 schema table) BEFORE execution */
    .responses-wrapper .responses-inner .responses-table { display: none !important; }
    .responses-wrapper .opblock-section-header { display: none !important; }

    /* Hide response code column and headers from live result */
    .live-responses-table .response-col_status { display: none !important; }
    .live-responses-table thead { display: none !important; }

    /* Hide "Response headers" block inside live result */
    .live-responses-table .response-col_description .response-headers-wrapper { display: none !important; }
    .live-responses-table .response-col_description > div > h5 { display: none !important; }

    /* Hide the "Download" link area label but keep the body */
    .live-responses-table .response-col_description .microlight + div { display: none !important; }

    /* Keep live response body visible and styled nicely */
    .live-responses-table { display: table !important; width: 100% !important; }
    .live-responses-table .response-col_description { display: table-cell !important; }
    .live-responses-table .microlight { 
        display: block !important; 
        background: #ffffff !important; 
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
    }

    /* ── Pure Cleanup ── */
    .responses-inner { padding: 0 !important; margin: 0 !important; }
    .responses-wrapper { padding: 0 !important; margin-top: 10px !important; }
    """
    return Response(content=content, media_type="text/css")


# Overriding the default docs route with a custom CSS-injected version
@app.get("/docs", include_in_schema=False)
async def overhauled_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title,
        swagger_ui_parameters=app.swagger_ui_parameters,
        swagger_css_url="/swagger-custom.css?v=final-cleanup",
    )


# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
