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
2.  **Activate API**: Select the **'Try it out'** button on the right side.
3.  **Provide Inputs**:
    *   **`primary_keyword`** (string) -> The main keyword you want your content to rank for
    *   **`file`** (file upload) -> Upload your .docx manuscript
4.  **Execute**: Click the **'Execute'** button below.
5.  **Finish**: Wait a few seconds, and scroll down to view your AI-generated SEO data!

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
        "docExpansion": "full"
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
    .model-container { display: none !important; }

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

    /* Create visual separation for the output area - hidden by default */
    .responses-wrapper {
        display: none !important;
        margin-top: 40px !important;
        padding: 30px !important;
        background-color: #f8f9fa !important;
        border: 2px dashed #2d6a4f !important;
        border-radius: 12px !important;
        position: relative !important;
    }

    /* ONLY show when a live response exists */
    .responses-wrapper:has(.live-responses-table) {
        display: block !important;
    }

    /* Add a clear heading to the results area */
    .responses-wrapper::before {
        content: "✨ AI Generated SEO Results";
        display: block;
        font-size: 20px;
        font-weight: bold;
        color: #1a3c5e;
        margin-bottom: 15px;
        text-align: center;
    }
    """
    return Response(content=content, media_type="text/css")

# Overriding the default docs route with a custom CSS-injected version
@app.get("/docs", include_in_schema=False)
async def overhauled_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title,
        swagger_ui_parameters=app.swagger_ui_parameters,
        swagger_css_url="/swagger-custom.css?v=final-separation",
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
