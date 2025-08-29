from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from .api.routers import classification_router, extraction_router, prompt_router
recent_filename = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    return HTMLResponse("""
    <h1>Welcome to the OCR Extraction and Classification API</h1>
    """)
    
app.include_router(extraction_router.router)
app.include_router(classification_router.router)
app.include_router(prompt_router.router)
    

