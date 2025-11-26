# Security Check Agent

## Overview

The Security Check Agent specializes in security analysis, vulnerability assessment, and compliance verification for the Construction Analysis AI System. This agent provides guidance on authentication, authorization, data protection, and security best practices across the entire technology stack.

## Capabilities

### 🔒 Security Assessment
- Authentication and authorization analysis
- Data encryption and protection strategies
- API security and input validation
- Database security and access control
- File upload and storage security

### 🛡️ Vulnerability Detection
- Code security scanning
- Dependency vulnerability analysis
- Configuration security review
- Network security assessment
- Infrastructure security validation

### 📋 Compliance & Standards
- GDPR and data privacy compliance
- Industry security standards (SOC 2, ISO 27001)
- Construction industry specific regulations
- API security standards (OWASP)
- Cloud security best practices

## Core Responsibilities

### 1. Authentication & Authorization Framework

#### JWT Security Implementation
```python
# security/authentication.py
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, status
import secrets
import hashlib

class SecurityConfig:
    # Strong secret key (should be environment variable)
    JWT_SECRET_KEY = secrets.token_urlsafe(32)
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    # Password hashing
    PASSWORD_HASH_ALGORITHM = "bcrypt"
    PASSWORD_HASH_ROUNDS = 12

    # Rate limiting
    LOGIN_RATE_LIMIT = 5  # attempts per minute
    API_RATE_LIMIT = 100  # requests per minute

class SecureAuthenticationService:
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=SecurityConfig.PASSWORD_HASH_ROUNDS
        )

    def create_password_hash(self, password: str) -> str:
        """Create secure password hash"""
        # Validate password strength
        self._validate_password_strength(password)
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def _validate_password_strength(self, password: str):
        """Validate password meets security requirements"""
        if len(password) < 12:
            raise HTTPException(
                status_code=400,
                detail="Password must be at least 12 characters long"
            )

        if not any(c.isupper() for c in password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one uppercase letter"
            )

        if not any(c.islower() for c in password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one lowercase letter"
            )

        if not any(c.isdigit() for c in password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one number"
            )

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise HTTPException(
                status_code=400,
                detail="Password must contain at least one special character"
            )

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        return jwt.encode(
            to_encode,
            SecurityConfig.JWT_SECRET_KEY,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )

    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # Unique token ID
        }

        return jwt.encode(
            to_encode,
            SecurityConfig.JWT_SECRET_KEY,
            algorithm=SecurityConfig.JWT_ALGORITHM
        )

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                SecurityConfig.JWT_SECRET_KEY,
                algorithms=[SecurityConfig.JWT_ALGORITHM]
            )

            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid token type"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    def generate_csrf_token(self, user_id: str) -> str:
        """Generate CSRF token"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        data = f"{user_id}:{timestamp}:{SecurityConfig.JWT_SECRET_KEY}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_csrf_token(self, token: str, user_id: str) -> bool:
        """Verify CSRF token"""
        try:
            # Extract timestamp from token (assuming format user_id:timestamp:hash)
            current_time = int(datetime.utcnow().timestamp())
            # Token valid for 1 hour
            for timestamp in range(current_time - 3600, current_time + 1):
                expected_token = self.generate_csrf_token(user_id)
                if secrets.compare_digest(token, expected_token):
                    return True
            return False
        except Exception:
            return False
```

#### Role-Based Access Control (RBAC)
```python
# security/authorization.py
from enum import Enum
from typing import List, Dict, Set
from fastapi import HTTPException, Depends
from dataclasses import dataclass

class Permission(str, Enum):
    # Project permissions
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE = "project:manage"

    # Analysis permissions
    ANALYSIS_CREATE = "analysis:create"
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_DELETE = "analysis:delete"

    # File permissions
    FILE_UPLOAD = "file:upload"
    FILE_READ = "file:read"
    FILE_DELETE = "file:delete"

    # Admin permissions
    USER_MANAGE = "user:manage"
    SYSTEM_ADMIN = "system:admin"

class Role(str, Enum):
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"

@dataclass
class User:
    id: str
    email: str
    roles: List[Role]
    permissions: Set[Permission]

class RolePermissionMatrix:
    """Define permissions for each role"""

    ROLE_PERMISSIONS = {
        Role.ADMIN: {
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_DELETE,
            Permission.PROJECT_MANAGE,
            Permission.ANALYSIS_CREATE,
            Permission.ANALYSIS_READ,
            Permission.ANALYSIS_DELETE,
            Permission.FILE_UPLOAD,
            Permission.FILE_READ,
            Permission.FILE_DELETE,
            Permission.USER_MANAGE,
            Permission.SYSTEM_ADMIN,
        },
        Role.PROJECT_MANAGER: {
            Permission.PROJECT_CREATE,
            Permission.PROJECT_READ,
            Permission.PROJECT_UPDATE,
            Permission.PROJECT_MANAGE,
            Permission.ANALYSIS_CREATE,
            Permission.ANALYSIS_READ,
            Permission.FILE_UPLOAD,
            Permission.FILE_READ,
        },
        Role.ANALYST: {
            Permission.PROJECT_READ,
            Permission.ANALYSIS_CREATE,
            Permission.ANALYSIS_READ,
            Permission.FILE_UPLOAD,
            Permission.FILE_READ,
        },
        Role.VIEWER: {
            Permission.PROJECT_READ,
            Permission.ANALYSIS_READ,
            Permission.FILE_READ,
        },
        Role.GUEST: {
            Permission.PROJECT_READ,
        }
    }

    @classmethod
    def get_permissions_for_role(cls, role: Role) -> Set[Permission]:
        """Get all permissions for a specific role"""
        return cls.ROLE_PERMISSIONS.get(role, set())

    @classmethod
    def get_user_permissions(cls, roles: List[Role]) -> Set[Permission]:
        """Get combined permissions for multiple roles"""
        permissions = set()
        for role in roles:
            permissions.update(cls.get_permissions_for_role(role))
        return permissions

class AuthorizationService:
    """Handle authorization checks"""

    def __init__(self):
        self.role_matrix = RolePermissionMatrix()

    def check_permission(self, user: User, required_permission: Permission) -> bool:
        """Check if user has required permission"""
        return required_permission in user.permissions

    def check_resource_access(self, user: User, resource_type: str, resource_id: str, action: str) -> bool:
        """Check if user can perform action on specific resource"""

        # Admin has access to everything
        if Permission.SYSTEM_ADMIN in user.permissions:
            return True

        # Resource-specific logic
        if resource_type == "project":
            return self._check_project_access(user, resource_id, action)
        elif resource_type == "analysis":
            return self._check_analysis_access(user, resource_id, action)
        elif resource_type == "file":
            return self._check_file_access(user, resource_id, action)

        return False

    def _check_project_access(self, user: User, project_id: str, action: str) -> bool:
        """Check project-specific access"""
        # This would typically check if user owns the project or is a team member
        # For now, simplified check based on permissions

        permission_map = {
            "read": Permission.PROJECT_READ,
            "update": Permission.PROJECT_UPDATE,
            "delete": Permission.PROJECT_DELETE,
            "manage": Permission.PROJECT_MANAGE,
        }

        required_permission = permission_map.get(action)
        if not required_permission:
            return False

        return self.check_permission(user, required_permission)

    def _check_analysis_access(self, user: User, analysis_id: str, action: str) -> bool:
        """Check analysis-specific access"""
        permission_map = {
            "read": Permission.ANALYSIS_READ,
            "create": Permission.ANALYSIS_CREATE,
            "delete": Permission.ANALYSIS_DELETE,
        }

        required_permission = permission_map.get(action)
        if not required_permission:
            return False

        return self.check_permission(user, required_permission)

    def _check_file_access(self, user: User, file_id: str, action: str) -> bool:
        """Check file-specific access"""
        permission_map = {
            "read": Permission.FILE_READ,
            "upload": Permission.FILE_UPLOAD,
            "delete": Permission.FILE_DELETE,
        }

        required_permission = permission_map.get(action)
        if not required_permission:
            return False

        return self.check_permission(user, required_permission)

# FastAPI dependency for authorization
def require_permission(permission: Permission):
    """Decorator to require specific permission"""
    def dependency(current_user: User = Depends(get_current_user)):
        auth_service = AuthorizationService()
        if not auth_service.check_permission(current_user, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {permission.value}"
            )
        return current_user
    return dependency

def require_resource_access(resource_type: str, action: str):
    """Decorator to require access to specific resource"""
    def dependency(
        resource_id: str,
        current_user: User = Depends(get_current_user)
    ):
        auth_service = AuthorizationService()
        if not auth_service.check_resource_access(current_user, resource_type, resource_id, action):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to {resource_type} {resource_id} for action {action}"
            )
        return current_user
    return dependency
```

### 2. Input Validation & Sanitization

#### Comprehensive Input Validation
```python
# security/input_validation.py
import re
from typing import Any, Dict, List
from fastapi import HTTPException
import bleach
from pydantic import BaseModel, validator
import html

class SecurityValidator:
    """Comprehensive input validation and sanitization"""

    # Dangerous patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"('|(\\'))+.*(or|union|insert|delete|update|drop|create|alter|exec|execute)",
        r"(union|select|insert|delete|update|drop|create|alter)\s+",
        r"(exec|execute)\s*\(",
    ]

    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`]",
        r"\$\(",
        r"`.*`",
        r">(>|\s)",
    ]

    @classmethod
    def validate_sql_injection(cls, value: str) -> str:
        """Check for SQL injection patterns"""
        if not isinstance(value, str):
            return value

        value_lower = value.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                raise HTTPException(
                    status_code=400,
                    detail="Potentially malicious input detected"
                )
        return value

    @classmethod
    def validate_xss(cls, value: str) -> str:
        """Check for XSS patterns and sanitize"""
        if not isinstance(value, str):
            return value

        # Check for dangerous patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise HTTPException(
                    status_code=400,
                    detail="Potentially malicious script detected"
                )

        # Sanitize HTML
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
        allowed_attributes = {}

        sanitized = bleach.clean(
            value,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )

        # HTML escape any remaining content
        sanitized = html.escape(sanitized)

        return sanitized

    @classmethod
    def validate_command_injection(cls, value: str) -> str:
        """Check for command injection patterns"""
        if not isinstance(value, str):
            return value

        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                raise HTTPException(
                    status_code=400,
                    detail="Potentially dangerous characters detected"
                )
        return value

    @classmethod
    def validate_file_path(cls, file_path: str) -> str:
        """Validate file path for path traversal attacks"""
        if not isinstance(file_path, str):
            return file_path

        # Check for path traversal patterns
        dangerous_patterns = [
            r"\.\.",
            r"~",
            r"\/etc\/",
            r"\/proc\/",
            r"\/sys\/",
            r"c:\\",
            r"\\windows\\",
        ]

        file_path_lower = file_path.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, file_path_lower):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid file path"
                )

        return file_path

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise HTTPException(
                status_code=400,
                detail="Invalid email format"
            )
        return email.lower()

    @classmethod
    def validate_project_name(cls, name: str) -> str:
        """Validate project name"""
        if not name or len(name.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Project name cannot be empty"
            )

        if len(name) > 200:
            raise HTTPException(
                status_code=400,
                detail="Project name too long (max 200 characters)"
            )

        # Allow only alphanumeric, spaces, hyphens, underscores
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
            raise HTTPException(
                status_code=400,
                detail="Project name contains invalid characters"
            )

        return name.strip()

# Secure Pydantic models with validation
class SecureProjectCreate(BaseModel):
    name: str
    description: str
    project_type: str

    @validator('name')
    def validate_name(cls, v):
        return SecurityValidator.validate_project_name(v)

    @validator('description')
    def validate_description(cls, v):
        v = SecurityValidator.validate_xss(v)
        v = SecurityValidator.validate_sql_injection(v)
        if len(v) > 2000:
            raise ValueError("Description too long (max 2000 characters)")
        return v

    @validator('project_type')
    def validate_project_type(cls, v):
        allowed_types = ['residential', 'commercial', 'industrial', 'infrastructure', 'renovation']
        if v not in allowed_types:
            raise ValueError(f"Invalid project type. Must be one of: {allowed_types}")
        return v

class SecureUserCreate(BaseModel):
    email: str
    password: str
    name: str

    @validator('email')
    def validate_email(cls, v):
        return SecurityValidator.validate_email(v)

    @validator('name')
    def validate_name(cls, v):
        v = SecurityValidator.validate_xss(v)
        v = SecurityValidator.validate_sql_injection(v)
        if len(v) > 100:
            raise ValueError("Name too long (max 100 characters)")
        return v
```

### 3. File Upload Security

#### Secure File Handling
```python
# security/file_security.py
import os
import hashlib
import magic
from typing import List, Optional, Tuple
from fastapi import UploadFile, HTTPException
import uuid
from pathlib import Path

class FileSecurityService:
    """Secure file upload and validation"""

    # Allowed file types and their MIME types
    ALLOWED_FILE_TYPES = {
        'image': {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'],
            'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'],
            'max_size': 10 * 1024 * 1024  # 10MB
        },
        'document': {
            'extensions': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
            'mime_types': ['application/pdf', 'application/msword',
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'text/plain', 'application/rtf'],
            'max_size': 50 * 1024 * 1024  # 50MB
        },
        'spreadsheet': {
            'extensions': ['.xls', '.xlsx', '.csv'],
            'mime_types': ['application/vnd.ms-excel',
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'text/csv'],
            'max_size': 25 * 1024 * 1024  # 25MB
        },
        'cad': {
            'extensions': ['.dwg', '.dxf', '.step', '.iges'],
            'mime_types': ['application/acad', 'image/vnd.dxf', 'application/step',
                          'application/iges'],
            'max_size': 100 * 1024 * 1024  # 100MB
        }
    }

    # Dangerous file extensions
    DANGEROUS_EXTENSIONS = [
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.zip', '.rar', '.7z', '.tar', '.gz', '.php', '.asp',
        '.jsp', '.pl', '.py', '.rb', '.sh', '.ps1'
    ]

    def __init__(self, upload_directory: str = "/tmp/claude/uploads"):
        self.upload_directory = Path(upload_directory)
        self.upload_directory.mkdir(parents=True, exist_ok=True)

    async def validate_file(self, file: UploadFile) -> Tuple[bool, str, Optional[str]]:
        """Comprehensive file validation"""

        # Check file exists and has content
        if not file or not file.filename:
            return False, "No file provided", None

        # Read file content for validation
        content = await file.read()
        await file.seek(0)  # Reset file pointer

        if len(content) == 0:
            return False, "Empty file not allowed", None

        # Get file extension
        file_extension = Path(file.filename).suffix.lower()

        # Check for dangerous extensions
        if file_extension in self.DANGEROUS_EXTENSIONS:
            return False, f"File type {file_extension} not allowed for security reasons", None

        # Validate file type
        file_type = self._detect_file_type(file_extension)
        if not file_type:
            return False, f"Unsupported file type: {file_extension}", None

        # Check file size
        file_size = len(content)
        max_size = self.ALLOWED_FILE_TYPES[file_type]['max_size']
        if file_size > max_size:
            return False, f"File size ({file_size} bytes) exceeds maximum allowed ({max_size} bytes)", None

        # Validate MIME type using python-magic
        try:
            detected_mime = magic.from_buffer(content, mime=True)
            allowed_mimes = self.ALLOWED_FILE_TYPES[file_type]['mime_types']

            if detected_mime not in allowed_mimes:
                return False, f"File content doesn't match expected type. Detected: {detected_mime}", None
        except Exception as e:
            return False, f"Could not validate file content: {str(e)}", None

        # Check for embedded threats (basic)
        if self._scan_for_threats(content):
            return False, "File contains potentially malicious content", None

        return True, "File validation passed", file_type

    def _detect_file_type(self, extension: str) -> Optional[str]:
        """Detect file type category from extension"""
        for file_type, config in self.ALLOWED_FILE_TYPES.items():
            if extension in config['extensions']:
                return file_type
        return None

    def _scan_for_threats(self, content: bytes) -> bool:
        """Basic threat scanning for file content"""

        # Convert to string for text-based scanning (if possible)
        try:
            text_content = content.decode('utf-8', errors='ignore').lower()

            # Check for suspicious patterns
            suspicious_patterns = [
                'eval(',
                'exec(',
                'system(',
                'shell_exec(',
                'base64_decode(',
                'javascript:',
                '<script',
                'vbscript:',
                'activexobject',
                'window.location',
                'document.cookie'
            ]

            for pattern in suspicious_patterns:
                if pattern in text_content:
                    return True

        except UnicodeDecodeError:
            pass  # Binary file, skip text-based scanning

        # Check for executable file signatures
        executable_signatures = [
            b'MZ',  # PE executable
            b'\x7fELF',  # ELF executable
            b'\xfe\xed\xfa',  # Mach-O executable
            b'\xcf\xfa\xed\xfe',  # Mach-O executable
        ]

        for signature in executable_signatures:
            if content.startswith(signature):
                return True

        return False

    async def save_file_securely(self, file: UploadFile, file_type: str) -> Dict[str, str]:
        """Save file with security measures"""

        # Generate secure filename
        file_id = str(uuid.uuid4())
        original_name = file.filename
        safe_filename = self._sanitize_filename(original_name)
        file_extension = Path(safe_filename).suffix.lower()

        # Create type-specific subdirectory
        type_directory = self.upload_directory / file_type
        type_directory.mkdir(exist_ok=True)

        # Generate final file path
        final_filename = f"{file_id}{file_extension}"
        file_path = type_directory / final_filename

        try:
            # Read and write file content
            content = await file.read()

            # Calculate file hash for integrity
            file_hash = hashlib.sha256(content).hexdigest()

            # Write file securely
            with open(file_path, 'wb') as f:
                f.write(content)

            # Set restrictive permissions (owner read/write only)
            os.chmod(file_path, 0o600)

            return {
                'file_id': file_id,
                'original_name': original_name,
                'safe_filename': safe_filename,
                'file_path': str(file_path),
                'file_type': file_type,
                'file_size': len(content),
                'file_hash': file_hash,
                'mime_type': file.content_type
            }

        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent security issues"""
        if not filename:
            return "unnamed_file"

        # Remove or replace dangerous characters
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        safe_filename = re.sub(r'\.+', '.', safe_filename)  # Multiple dots
        safe_filename = safe_filename.strip('. ')  # Leading/trailing dots and spaces

        # Limit length
        if len(safe_filename) > 255:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:250] + ext

        return safe_filename

    def delete_file_securely(self, file_path: str) -> bool:
        """Securely delete file"""
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                # Secure deletion (overwrite before delete)
                with open(path, 'r+b') as f:
                    length = f.seek(0, 2)  # Seek to end
                    f.seek(0)  # Seek to beginning
                    f.write(os.urandom(length))  # Overwrite with random data
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk

                path.unlink()  # Delete file
                return True
        except Exception as e:
            logging.error(f"Error securely deleting file {file_path}: {str(e)}")
        return False

# Usage in FastAPI endpoint
from fastapi import Depends

async def secure_file_upload(
    file: UploadFile,
    file_security: FileSecurityService = Depends()
) -> Dict[str, Any]:
    """Secure file upload endpoint"""

    # Validate file
    is_valid, message, file_type = await file_security.validate_file(file)

    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # Save file securely
    file_info = await file_security.save_file_securely(file, file_type)

    return {
        "success": True,
        "file_id": file_info['file_id'],
        "message": "File uploaded successfully",
        "file_info": file_info
    }
```

### 4. Database Security

#### MongoDB Security Configuration
```python
# security/database_security.py
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any, List
import logging
import hashlib

class DatabaseSecurityManager:
    """MongoDB security configuration and monitoring"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.logger = logging.getLogger(__name__)

    async def setup_security_configuration(self, client: AsyncIOMotorClient):
        """Setup database security configuration"""

        try:
            # Enable authentication (if not already enabled)
            await self._ensure_authentication_enabled(client)

            # Setup user roles and permissions
            await self._setup_database_users(client)

            # Configure security settings
            await self._configure_security_settings(client)

            # Setup audit logging
            await self._setup_audit_logging(client)

        except Exception as e:
            self.logger.error(f"Failed to setup database security: {str(e)}")
            raise

    async def _ensure_authentication_enabled(self, client: AsyncIOMotorClient):
        """Ensure authentication is enabled"""
        try:
            # Check if authentication is enabled
            server_status = await client.admin.command("serverStatus")
            security_info = server_status.get("security", {})

            if not security_info.get("authentication", {}).get("enabled"):
                self.logger.warning("Database authentication is not enabled")
                # Note: Enabling auth requires restart and admin privileges

        except Exception as e:
            self.logger.error(f"Could not check authentication status: {str(e)}")

    async def _setup_database_users(self, client: AsyncIOMotorClient):
        """Setup database users with appropriate roles"""

        # Database name
        db_name = "construction_analysis"
        db = client[db_name]

        # Define user roles
        users_config = [
            {
                "username": "app_user",
                "roles": [
                    {"role": "readWrite", "db": db_name},
                    {"role": "dbAdmin", "db": db_name}
                ],
                "description": "Application user with read/write access"
            },
            {
                "username": "readonly_user",
                "roles": [
                    {"role": "read", "db": db_name}
                ],
                "description": "Read-only user for reporting"
            },
            {
                "username": "backup_user",
                "roles": [
                    {"role": "backup", "db": "admin"},
                    {"role": "restore", "db": "admin"}
                ],
                "description": "Backup and restore user"
            }
        ]

        for user_config in users_config:
            try:
                # Check if user exists
                user_info = await db.command("usersInfo", user_config["username"])

                if not user_info.get("users"):
                    # User doesn't exist, create it
                    password = self._generate_secure_password()

                    await db.command(
                        "createUser",
                        user_config["username"],
                        pwd=password,
                        roles=user_config["roles"]
                    )

                    self.logger.info(f"Created database user: {user_config['username']}")

                    # Log password securely (in production, use secret management)
                    self.logger.info(f"Password for {user_config['username']}: {password}")

            except Exception as e:
                self.logger.error(f"Failed to create user {user_config['username']}: {str(e)}")

    def _generate_secure_password(self, length: int = 32) -> str:
        """Generate secure random password"""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    async def _configure_security_settings(self, client: AsyncIOMotorClient):
        """Configure additional security settings"""

        try:
            # Set security-related parameters
            security_params = {
                # Require SSL/TLS
                "net.ssl.mode": "requireSSL",

                # Set connection limits
                "net.maxIncomingConnections": 1000,

                # Enable query logging for security monitoring
                "operationProfiling.mode": "slowOp",
                "operationProfiling.slowOpThresholdMs": 100,

                # Set authentication settings
                "security.authorization": "enabled",
                "security.javascriptEnabled": False,  # Disable server-side JS
            }

            for param, value in security_params.items():
                try:
                    await client.admin.command("setParameter", {param: value})
                    self.logger.info(f"Set security parameter {param}: {value}")
                except Exception as e:
                    self.logger.warning(f"Could not set parameter {param}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Failed to configure security settings: {str(e)}")

    async def _setup_audit_logging(self, client: AsyncIOMotorClient):
        """Setup audit logging for security events"""

        try:
            # Configure audit logging (Enterprise feature)
            audit_config = {
                "auditLog.destination": "file",
                "auditLog.format": "JSON",
                "auditLog.path": "/var/log/mongodb/audit.log",
                "auditLog.filter": {
                    "atype": {
                        "$in": [
                            "authenticate", "authCheck", "logout",
                            "createUser", "dropUser", "createRole", "dropRole",
                            "createIndex", "dropIndex", "dropCollection"
                        ]
                    }
                }
            }

            await client.admin.command("setParameter", audit_config)
            self.logger.info("Audit logging configured")

        except Exception as e:
            self.logger.warning(f"Could not configure audit logging: {str(e)}")

    async def monitor_security_events(self, client: AsyncIOMotorClient) -> List[Dict[str, Any]]:
        """Monitor security-related events"""

        security_events = []

        try:
            # Check for failed authentication attempts
            failed_auths = await self._check_failed_authentications(client)
            security_events.extend(failed_auths)

            # Check for suspicious query patterns
            suspicious_queries = await self._check_suspicious_queries(client)
            security_events.extend(suspicious_queries)

            # Check for unusual connection patterns
            connection_anomalies = await self._check_connection_anomalies(client)
            security_events.extend(connection_anomalies)

        except Exception as e:
            self.logger.error(f"Error monitoring security events: {str(e)}")

        return security_events

    async def _check_failed_authentications(self, client: AsyncIOMotorClient) -> List[Dict[str, Any]]:
        """Check for failed authentication attempts"""
        events = []

        try:
            # Query profiler collection for authentication failures
            db = client.get_default_database()
            profiler_collection = db.system.profile

            # Look for failed auth events in last hour
            from datetime import datetime, timedelta
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)

            failed_auth_cursor = profiler_collection.find({
                "ts": {"$gte": one_hour_ago},
                "command.authenticate": {"$exists": True},
                "ok": 0  # Failed operations
            })

            async for event in failed_auth_cursor:
                events.append({
                    "type": "failed_authentication",
                    "timestamp": event.get("ts"),
                    "user": event.get("command", {}).get("user"),
                    "source": event.get("client"),
                    "severity": "medium"
                })

        except Exception as e:
            self.logger.error(f"Error checking failed authentications: {str(e)}")

        return events

    async def _check_suspicious_queries(self, client: AsyncIOMotorClient) -> List[Dict[str, Any]]:
        """Check for suspicious query patterns"""
        events = []

        try:
            db = client.get_default_database()
            profiler_collection = db.system.profile

            # Look for potentially malicious queries
            suspicious_patterns = [
                {"command.find": {"$regex": ".*\\$where.*"}},  # JavaScript execution
                {"command.find": {"$regex": ".*eval.*"}},     # Code evaluation
                {"command.mapReduce": {"$exists": True}},     # MapReduce operations
            ]

            for pattern in suspicious_patterns:
                cursor = profiler_collection.find(pattern).limit(10)
                async for event in cursor:
                    events.append({
                        "type": "suspicious_query",
                        "timestamp": event.get("ts"),
                        "pattern": str(pattern),
                        "command": event.get("command"),
                        "source": event.get("client"),
                        "severity": "high"
                    })

        except Exception as e:
            self.logger.error(f"Error checking suspicious queries: {str(e)}")

        return events

    async def _check_connection_anomalies(self, client: AsyncIOMotorClient) -> List[Dict[str, Any]]:
        """Check for unusual connection patterns"""
        events = []

        try:
            # Get current connections
            current_op = await client.admin.command("currentOp")
            connections = current_op.get("inprog", [])

            # Analyze connection patterns
            connection_sources = {}
            for conn in connections:
                client_info = conn.get("client", "unknown")
                if client_info != "unknown":
                    connection_sources[client_info] = connection_sources.get(client_info, 0) + 1

            # Flag unusual connection counts
            for source, count in connection_sources.items():
                if count > 10:  # More than 10 connections from same source
                    events.append({
                        "type": "connection_anomaly",
                        "timestamp": datetime.utcnow(),
                        "source": source,
                        "connection_count": count,
                        "severity": "medium"
                    })

        except Exception as e:
            self.logger.error(f"Error checking connection anomalies: {str(e)}")

        return events
```

### 5. Security Monitoring & Logging

#### Comprehensive Security Logging
```python
# security/security_logging.py
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
import asyncio
from functools import wraps

class SecurityEventType(str, Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    FILE_UPLOAD = "file_upload"
    FILE_ACCESS = "file_access"
    SECURITY_VIOLATION = "security_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

class SecuritySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityLogger:
    """Centralized security event logging"""

    def __init__(self):
        # Setup security-specific logger
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)

        # Create security log handler
        handler = logging.FileHandler("/var/log/construction_analysis/security.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Also log to console in development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def log_security_event(self,
                          event_type: SecurityEventType,
                          severity: SecuritySeverity,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None,
                          resource: Optional[str] = None,
                          action: Optional[str] = None):
        """Log a security event"""

        event_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "severity": severity.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "resource": resource,
            "action": action,
            "details": details or {}
        }

        # Log at appropriate level based on severity
        log_level = {
            SecuritySeverity.LOW: logging.INFO,
            SecuritySeverity.MEDIUM: logging.WARNING,
            SecuritySeverity.HIGH: logging.ERROR,
            SecuritySeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.INFO)

        self.logger.log(log_level, json.dumps(event_data))

        # Send alerts for high severity events
        if severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
            asyncio.create_task(self._send_security_alert(event_data))

    async def _send_security_alert(self, event_data: Dict[str, Any]):
        """Send real-time security alerts"""
        try:
            # In a real implementation, this would send alerts via:
            # - Email
            # - Slack/Teams
            # - SMS
            # - Security incident management system

            print(f"🚨 SECURITY ALERT: {event_data['event_type']} - {event_data['severity']}")
            print(f"Details: {json.dumps(event_data, indent=2)}")

        except Exception as e:
            logging.error(f"Failed to send security alert: {str(e)}")

# Decorator for automatic security logging
def log_security_event(event_type: SecurityEventType,
                      severity: SecuritySeverity = SecuritySeverity.LOW):
    """Decorator to automatically log security events"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            security_logger = SecurityLogger()

            try:
                result = await func(*args, **kwargs)

                # Log successful execution
                security_logger.log_security_event(
                    event_type=event_type,
                    severity=severity,
                    details={"function": func.__name__, "success": True}
                )

                return result

            except Exception as e:
                # Log failed execution
                security_logger.log_security_event(
                    event_type=SecurityEventType.SECURITY_VIOLATION,
                    severity=SecuritySeverity.HIGH,
                    details={
                        "function": func.__name__,
                        "error": str(e),
                        "success": False
                    }
                )
                raise

        return wrapper
    return decorator

# Security monitoring service
class SecurityMonitoringService:
    """Real-time security monitoring and analysis"""

    def __init__(self):
        self.security_logger = SecurityLogger()
        self.alert_thresholds = {
            "failed_logins_per_minute": 10,
            "unauthorized_access_per_hour": 5,
            "suspicious_activity_per_hour": 3
        }
        self.event_counters = {}

    def track_event(self, event_type: SecurityEventType, user_id: str = None, ip_address: str = None):
        """Track security events for pattern analysis"""
        current_time = datetime.utcnow()

        # Create tracking key
        if user_id:
            key = f"{event_type.value}:{user_id}"
        elif ip_address:
            key = f"{event_type.value}:{ip_address}"
        else:
            key = event_type.value

        # Initialize counter if doesn't exist
        if key not in self.event_counters:
            self.event_counters[key] = []

        # Add current event
        self.event_counters[key].append(current_time)

        # Clean old events (older than 1 hour)
        one_hour_ago = current_time - timedelta(hours=1)
        self.event_counters[key] = [
            event_time for event_time in self.event_counters[key]
            if event_time > one_hour_ago
        ]

        # Check for threshold violations
        self._check_thresholds(event_type, key, user_id, ip_address)

    def _check_thresholds(self, event_type: SecurityEventType, key: str,
                         user_id: str = None, ip_address: str = None):
        """Check if event counts exceed security thresholds"""

        current_count = len(self.event_counters[key])

        # Check specific thresholds
        if event_type == SecurityEventType.LOGIN_FAILURE:
            if current_count >= self.alert_thresholds["failed_logins_per_minute"]:
                self.security_logger.log_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    severity=SecuritySeverity.HIGH,
                    user_id=user_id,
                    ip_address=ip_address,
                    details={
                        "reason": "Excessive failed login attempts",
                        "count": current_count,
                        "threshold": self.alert_thresholds["failed_logins_per_minute"]
                    }
                )

        elif event_type == SecurityEventType.UNAUTHORIZED_ACCESS:
            if current_count >= self.alert_thresholds["unauthorized_access_per_hour"]:
                self.security_logger.log_security_event(
                    event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                    severity=SecuritySeverity.CRITICAL,
                    user_id=user_id,
                    ip_address=ip_address,
                    details={
                        "reason": "Repeated unauthorized access attempts",
                        "count": current_count,
                        "threshold": self.alert_thresholds["unauthorized_access_per_hour"]
                    }
                )

# Usage examples
security_logger = SecurityLogger()
security_monitor = SecurityMonitoringService()

# Example: Log successful login
security_logger.log_security_event(
    event_type=SecurityEventType.LOGIN_SUCCESS,
    severity=SecuritySeverity.LOW,
    user_id="user123",
    ip_address="192.168.1.100",
    details={"method": "password"}
)

# Example: Log unauthorized access attempt
security_logger.log_security_event(
    event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
    severity=SecuritySeverity.HIGH,
    ip_address="suspicious.ip.address",
    resource="/admin/users",
    action="GET",
    details={"reason": "No valid authentication token"}
)
```

This Security Check Agent provides comprehensive security guidance and implementation for the Construction Analysis AI System, covering authentication, authorization, input validation, file security, database security, and monitoring.