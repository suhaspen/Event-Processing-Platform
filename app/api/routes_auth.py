"""
Authentication scaffolding: email/password signup, JWT login, API key issuance/rotation.

- JWT: Bearer token for dashboard and ``POST /auth/api-key``.
- API key: ``X-API-Key`` header for event and analytics routes (see ``get_current_api_user``).
"""
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DBSessionDep, auth_rate_limiter, get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import APIKeyOut, Token, TokenWithAPIKey, UserCreate, UserLogin, UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/signup",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limiter)],
)
def signup(user_in: UserCreate, db: DBSessionDep) -> UserOut:
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenWithAPIKey, dependencies=[Depends(auth_rate_limiter)])
def login(user_in: UserLogin, db: DBSessionDep) -> TokenWithAPIKey:
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Ensure the user has an API key; create one on first login for a smoother UX
    if not user.api_key:
        user.api_key = token_urlsafe(32)
        db.add(user)
        db.commit()
        db.refresh(user)

    access_token = create_access_token(subject=user.email)
    return TokenWithAPIKey(access_token=access_token, api_key=user.api_key)


@router.post("/api-key", response_model=APIKeyOut)
def create_or_rotate_api_key(
    db: DBSessionDep,
    current_user: User = Depends(get_current_user),
):
    api_key = token_urlsafe(32)
    current_user.api_key = api_key
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return APIKeyOut(api_key=api_key)

