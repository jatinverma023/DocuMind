from fastapi import APIRouter, HTTPException, status
from app.models.user import UserRegister, UserLogin, TokenResponse, UserOut
from app.db.mongodb import users_collection
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    existing = await users_collection.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "role": "user",  # hardcoded — never trust a client-supplied role
    }
    result = await users_collection.insert_one(user_doc)
    user_id = str(result.inserted_id)

    token = create_access_token({"sub": user_id, "role": "user"})
    user_out = UserOut(id=user_id, name=payload.name, email=payload.email, role="user")
    return TokenResponse(access_token=token, user=user_out)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    user = await users_collection.find_one({"email": payload.email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id, "role": user["role"]})
    user_out = UserOut(id=user_id, name=user["name"], email=user["email"], role=user["role"])
    return TokenResponse(access_token=token, user=user_out)
