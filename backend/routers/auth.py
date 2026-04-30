"""
routers/auth.py
───────────────
Endpoints:
  POST /auth/register  - create a new user account
  POST /auth/login     - authenticate and receive JWT
  GET  /auth/me        - get current user info (requires token)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import hashed_password, verify_password, create_access_token
from backend.models.users import User, UserCreate, UserLogin, UserOut, TokenResponse
from backend.utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    - Username and email must be unique.
    - Password is hashed with bcrypt before storage.
    """
    # Check for duplicate username
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")

    # Check for duplicate email
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    # Create and save user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with username + password.
    Returns a JWT access token valid for ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    token = create_access_token(data={"sub": user.username})

    return TokenResponse(access_token=token, user=UserOut.from_orm(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user