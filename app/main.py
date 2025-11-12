# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from .routes import (
    resume_routes,
    login_routes,
    interview_routes,
    answer_routes,
    profile_routes,
    analyze_routes,
    record_routes,
    candidate_que_ans_routes,
    generate_jd_routes,
    xray_search_routes
)

app = FastAPI(title="AI Interview Analysis API")

# ✅ Allow frontend calls (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Custom OpenAPI for optional JWT usage
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="AI Interview API",
        version="1.0.0",
        description="API for AI interview system",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }

    # 🔐 Only protect specific routes like /chat-store/
    secure_paths = ["/parse-resume/", "/submit-answer/", "/generate-questions/", "/upload-full-video/", "/upload-question-audio/","/get-candidate-answers/"]

    for path in openapi_schema["paths"]:
        if path in secure_paths:
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
        else:
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method].pop("security", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# ✅ Register routers
app.include_router(resume_routes.router)
app.include_router(answer_routes.router)
app.include_router(login_routes.router)
app.include_router(interview_routes.router)
app.include_router(profile_routes.router)
app.include_router(analyze_routes.router)
app.include_router(record_routes.router)
app.include_router(candidate_que_ans_routes.router)
app.include_router(generate_jd_routes.router)
app.include_router(xray_search_routes.router)
