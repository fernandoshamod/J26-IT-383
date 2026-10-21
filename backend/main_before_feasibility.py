from fastapi import FastAPI

app = FastAPI(
    title="PlanoVision Vendor Intelligence API",
    description="Vendor Intelligence and Smart Package Recommendation Engine",
    version="0.1.0"
)

@app.get("/")
def root():
    return {
        "application": "PlanoVision",
        "component": "Vendor Intelligence",
        "status": "running"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "vendor-intelligence-api"
    }
