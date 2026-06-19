from fastapi import APIRouter, HTTPException, status
from app.schemas import LoginRequest, TokenResponse
from app.api.deps import create_access_token
from app.config import settings

router = APIRouter()


@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if req.username != settings.DEMO_USERNAME or req.password != settings.DEMO_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": req.username})
    return TokenResponse(access_token=token)


@router.post("/auth/logout")
async def logout():
    return {"message": "Logged out"}
