# Prompt: Implementar Autenticação JWT Adequada

Start Here
- Leia AGENTS.md e agents/README.md para padrões do repositório e checklists.
- Consulte docs/README.md para visão geral e guias (backend, frontend, database, auth).
- Siga os guias: agents/backend-development.md, agents/security-check.md, docs/authentication.md.

Objetivo
- Implementar sistema robusto de autenticação JWT para WebSocket e REST APIs.
- Garantir segurança com refresh tokens, validação adequada e proteção contra ataques.
- Integrar autenticação com sessões de chat e rate limiting.

Escopo
- JWT Generation: criar e assinar tokens com claims adequados.
- Token Validation: middleware para validar tokens em requisições.
- Refresh Token: sistema de renovação automática de tokens.
- WebSocket Auth: autenticação durante handshake WebSocket.
- Security: proteção contra XSS, CSRF, replay attacks.

Requisitos de Configuração
- Variáveis de ambiente:
  - JWT_SECRET_KEY=<generated-secret-key>
  - JWT_REFRESH_SECRET_KEY=<generated-refresh-secret>
  - JWT_ALGORITHM=HS256
  - JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
  - JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
- Dependências: python-jose[cryptography], passlib[bcrypt]

Arquitetura de Alto Nível
- Token Service: geração e validação de tokens
- Auth Middleware: interceptação e validação de requisições
- User Service: gerenciamento de usuários e credenciais
- Session Manager: vinculação de tokens a sessões

Modelagem de Dados (MongoDB)
```python
# User Document
{
    "user_id": str,  # UUID
    "email": str,
    "username": str,
    "password_hash": str,
    "roles": ["user", "admin"],
    "created_at": datetime,
    "updated_at": datetime,
    "last_login": datetime,
    "is_active": bool,
    "email_verified": bool
}

# RefreshToken Document
{
    "token_id": str,  # UUID
    "user_id": str,
    "token_hash": str,
    "expires_at": datetime,
    "created_at": datetime,
    "revoked": bool,
    "device_info": str
}
```

Implementação do Auth Service
```python
# backend/src/infrastructure/auth/jwt_service.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class JWTService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=15)
        )
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(days=7)
        )
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        return jwt.encode(
            to_encode,
            self.refresh_secret_key,
            algorithm=self.algorithm
        )

    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
```

Auth Middleware
```python
# backend/src/infrastructure/auth/middleware.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    token = credentials.credentials
    jwt_service = JWTService(settings.JWT_SECRET_KEY)

    try:
        payload = jwt_service.verify_token(token)

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Get user from database
        user = await UserService.get_user(payload.get("sub"))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return user

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
```

WebSocket Authentication
```python
# backend/src/presentation/api/websocket.py update
async def authenticate_websocket(token: str) -> Dict:
    """Authenticate WebSocket connection."""
    if not token:
        return None

    try:
        jwt_service = JWTService(settings.JWT_SECRET_KEY)
        payload = jwt_service.verify_token(token)

        # Get user
        user = await UserService.get_user(payload.get("sub"))
        return user if user and user.is_active else None
    except:
        return None

@router.websocket("/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    # Authenticate
    user = await authenticate_websocket(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Continue with authenticated user...
```

API Endpoints
```python
# backend/src/presentation/api/auth.py
@router.post("/auth/login")
async def login(credentials: LoginSchema):
    user = await UserService.authenticate(
        credentials.email,
        credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    access_token = jwt_service.create_access_token(
        data={"sub": str(user.user_id), "email": user.email}
    )

    refresh_token = jwt_service.create_refresh_token(
        data={"sub": str(user.user_id)}
    )

    # Store refresh token
    await TokenService.store_refresh_token(
        user.user_id, refresh_token
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/auth/refresh")
async def refresh_token(refresh: RefreshSchema):
    payload = jwt_service.verify_refresh_token(refresh.refresh_token)

    # Verify token hasn't been revoked
    if await TokenService.is_revoked(refresh.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    # Generate new access token
    access_token = jwt_service.create_access_token(
        data={"sub": payload.get("sub")}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/auth/logout")
async def logout(
    current_user: Dict = Depends(get_current_user),
    refresh_token: Optional[str] = None
):
    if refresh_token:
        await TokenService.revoke_token(refresh_token)

    return {"message": "Logged out successfully"}
```

Frontend Integration
```javascript
// frontend/src/services/AuthService.js
class AuthService {
    constructor() {
        this.baseUrl = process.env.NEXT_PUBLIC_API_URL;
        this.accessToken = null;
        this.refreshToken = null;
        this.refreshTimer = null;
    }

    async login(email, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            this.setTokens(data.access_token, data.refresh_token);
            this.scheduleTokenRefresh();
            return data;
        }

        throw new Error('Login failed');
    }

    setTokens(accessToken, refreshToken) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;

        // Store securely (consider using httpOnly cookies in production)
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);
    }

    async refreshAccessToken() {
        if (!this.refreshToken) return null;

        const response = await fetch(`${this.baseUrl}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: this.refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            this.accessToken = data.access_token;
            localStorage.setItem('access_token', this.accessToken);
            return this.accessToken;
        }

        // Refresh failed, clear tokens
        this.logout();
        return null;
    }

    scheduleTokenRefresh() {
        // Refresh token 1 minute before expiry
        const refreshIn = 14 * 60 * 1000; // 14 minutes

        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }

        this.refreshTimer = setTimeout(async () => {
            await this.refreshAccessToken();
            this.scheduleTokenRefresh();
        }, refreshIn);
    }

    getAuthHeaders() {
        return this.accessToken
            ? { 'Authorization': `Bearer ${this.accessToken}` }
            : {};
    }

    logout() {
        this.accessToken = null;
        this.refreshToken = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }
    }
}

export default new AuthService();
```

Segurança Adicional
- Rate limiting por IP para tentativas de login
- Bloqueio de conta após falhas consecutivas
- Two-factor authentication (2FA) opcional
- Audit log de eventos de autenticação
- Token rotation após refresh
- Secure cookie storage (httpOnly, secure, sameSite)

Testes
```python
# backend/tests/test_auth.py
import pytest
from datetime import datetime, timedelta

def test_create_access_token():
    service = JWTService("test-secret")
    token = service.create_access_token({"sub": "user123"})
    assert token is not None

    payload = service.verify_token(token)
    assert payload["sub"] == "user123"
    assert payload["type"] == "access"

def test_token_expiration():
    service = JWTService("test-secret")
    token = service.create_access_token(
        {"sub": "user123"},
        expires_delta=timedelta(seconds=-1)
    )

    with pytest.raises(HTTPException) as exc:
        service.verify_token(token)
    assert exc.value.status_code == 401

def test_password_hashing():
    service = JWTService("test-secret")
    password = "SecurePassword123!"
    hashed = service.hash_password(password)

    assert service.verify_password(password, hashed)
    assert not service.verify_password("wrong", hashed)
```

Entregáveis do PR
- JWT Service implementation com refresh tokens
- Auth middleware para FastAPI
- WebSocket authentication handler
- API endpoints (login, refresh, logout)
- Frontend AuthService com auto-refresh
- Testes unitários e de integração
- Documentação de segurança

Checklists úteis
- Revisar agents/security-check.md para vulnerabilidades
- Seguir agents/backend-development.md para estrutura
- Validar com OWASP guidelines

Notas
- Usar secrets.token_urlsafe(32) para gerar secret keys
- Considerar usar Redis para blacklist de tokens revogados
- Implementar rate limiting específico para endpoints de auth
- Monitorar tentativas de login suspeitas
- Considerar implementar JWT fingerprinting para segurança adicional