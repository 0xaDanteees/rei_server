from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..settings import settings

bearer_scheme = HTTPBearer(auto_error=False)

class AuthUser(Dict[str, Any]):
    @property
    def user_id(self) -> UUID:
        return UUID(self.get("sub"))

    @property
    def is_active(self) -> bool:
        return bool(self.get("is_active", True))


def get_current_user(token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> AuthUser:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = jwt.decode(token.credentials, settings.JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        # Basic claim checks
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing sub")
        # Issuer optional check
        iss = payload.get("iss")
        if iss and settings.JWT_ISSUER and iss != settings.JWT_ISSUER:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")
        # Expiry
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > float(exp):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        # Active flag
        if payload.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        return AuthUser(payload)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
