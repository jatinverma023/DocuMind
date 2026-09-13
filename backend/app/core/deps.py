"""
Reusable FastAPI dependencies. Any route that needs a logged-in user adds
`current_user: dict = Depends(get_current_user)`. Any route that needs
admin-only access adds `_: dict = Depends(require_admin)`.

This is the SINGLE place RBAC logic lives — don't duplicate role checks
inside individual route handlers, or they'll drift out of sync.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from app.core.security import decode_access_token
from app.db.mongodb import users_collection

# HTTPBearer (not OAuth2PasswordBearer) because our /auth/login takes JSON
# {email, password}, not the OAuth2 form-encoded {username, password} spec.
# This makes Swagger's Authorize box a plain "paste your token" field.
bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception

    return user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user