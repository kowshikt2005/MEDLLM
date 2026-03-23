"""
Authentication router — handles signup, login, and token verification.

How JWT auth works:
  1. User signs up → we hash their password and save it in the database
  2. User logs in → we verify password, create a JWT token, send it back
  3. For every future request, the browser sends the token in the header:
     Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
  4. Our server decodes the token to identify the user

The token contains: {"sub": "user-uuid", "exp": 1234567890}
  - "sub" (subject) = the user's ID
  - "exp" (expiration) = when the token expires (24h from creation)
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import User, get_db
from app.models.schemas import LoginRequest, SignupRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Password hashing ────────────────────────────────────
# bcrypt is a one-way hashing algorithm. You can turn a password INTO a hash,
# but you can never turn a hash BACK into a password. To verify a login,
# we hash the incoming password and compare it to the stored hash.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Turn a plain text password into an irreversible hash."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain text password matches a stored hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT token creation ──────────────────────────────────
def create_access_token(user_id: str) -> str:
    """
    Create a JWT token for a user.

    The token is a base64-encoded JSON string signed with our secret key.
    Anyone can DECODE it (it's not encrypted), but only our server can
    VERIFY it (because only we know the secret key). If someone tampers
    with the token, verification fails.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,     # "subject" — who this token belongs to
        "exp": expire,       # when it expires
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# ── JWT token verification (used as a FastAPI dependency) ─
async def get_current_user(
    # FastAPI's Depends() system will be wired up in main.py
    # For now, this function extracts the user from the token
    token: str = "",
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode a JWT token and return the corresponding User from the database.
    This is used as a dependency in protected routes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


# ── Routes ──────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.

    Steps:
      1. Check if email already exists
      2. Hash the password (never store plain text passwords!)
      3. Create the User row in the database
      4. Generate a JWT token
      5. Return the token + user info
    """
    # Check if email already taken
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create the user
    user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        phone_number=request.phone_number,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)  # Reload to get the generated ID

    # Generate token and return
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Log in an existing user.

    Steps:
      1. Find user by email
      2. Verify password against stored hash
      3. Generate a JWT token
      4. Return the token + user info
    """
    # Find user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # Verify password (check both "user exists" and "password matches")
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Generate token and return
    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserResponse(id=user.id, email=user.email, full_name=user.full_name),
    )
