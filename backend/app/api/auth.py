from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.auth import UserCreate, Token, LoginRequest
from app.services import auth as auth_service
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(deps.get_db)):
    existing = auth_service.get_user(db, email=user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = auth_service.create_user(db, email=user_in.email, password=user_in.password)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
def login(login_req: LoginRequest, db: Session = Depends(deps.get_db)):
    user = auth_service.get_user(db, email=login_req.email)
    if not user or not auth_service.verify_password(login_req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    return Token(access_token=access_token)


@router.get("/me")
def read_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()), db: Session = Depends(deps.get_db)):
    user = deps.get_current_user(credentials=credentials, db=db)
    return {"email": user.email}
