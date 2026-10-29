# Service ID: WBF23
# Service Name: بناء واجهات خلفية متطورة لمواقع وتطبيقات الويب باستخدام Django

"""
Advanced Authentication Manager Module

This module provides comprehensive authentication and authorization services
for Django-based business applications with advanced security features.

Author: Professional Backend Developer
Version: 2.1.0
License: Commercial
"""

from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone
from django.conf import settings
import jwt
import hashlib
import secrets
import logging
import json
from dataclasses import dataclass
from enum import Enum
import redis
from cryptography.fernet import Fernet

# Configure logging for authentication events
logger = logging.getLogger('advanced_auth')

# ==================== SECTION 1: Core Authentication Models ====================

class UserRole(models.TextChoices):
    """
    Enumeration of user roles in the business system
    تعداد أدوار المستخدمين في النظام التجاري
    """
    SUPER_ADMIN = 'super_admin', 'Super Administrator'
    ADMIN = 'admin', 'Administrator'
    MANAGER = 'manager', 'Manager'
    EMPLOYEE = 'employee', 'Employee'
    GUEST = 'guest', 'Guest User'

class AuthenticationStatus(Enum):
    """Authentication status enumeration"""
    SUCCESS = "success"
    FAILED = "failed"
    LOCKED = "locked"
    EXPIRED = "expired"
    PENDING_2FA = "pending_2fa"

@dataclass
class AuthenticationResult:
    """
    Data class representing authentication result
    فئة البيانات التي تمثل نتيجة المصادقة
    """
    status: AuthenticationStatus
    user: Optional['BusinessUser']
    token: Optional[str]
    expires_at: Optional[datetime]
    message: str
    requires_2fa: bool = False
    session_id: Optional[str] = None

class BusinessUser(AbstractUser):
    """
    Extended user model for business applications
    نموذج المستخدم الموسع للتطبيقات التجارية
    """
    
    # Basic user information
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.EMPLOYEE)
    
    # Security fields
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_password_change = models.DateTimeField(auto_now_add=True)
    password_expires_at = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    
    # Activity tracking
    last_activity = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Profile information
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language_preference = models.CharField(max_length=10, default='en')
    
    class Meta:
        db_table = 'business_users'
        verbose_name = 'Business User'
        verbose_name_plural = 'Business Users'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['role']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self) -> str:
        return f"{self.get_full_name()} ({self.employee_id})"

    @property
    def is_account_locked(self) -> bool:
        """Check if account is currently locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False

    @property
    def password_needs_change(self) -> bool:
        """Check if password needs to be changed"""
        if self.password_expires_at:
            return timezone.now() > self.password_expires_at
        return False

# ==================== SECTION 2: Session Management ====================

class UserSession(models.Model):
    """
    Enhanced session model for application security
    نموذج الجلسة المحسن لأمان التطبيق
    """
    
    user = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    device_fingerprint = models.CharField(max_length=64)
    
    # Session metadata
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Security flags
    is_suspicious = models.BooleanField(default=False)
    location_country = models.CharField(max_length=2, blank=True)
    location_city = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self) -> str:
        return f"Session for {self.user.username} from {self.ip_address}"

    @property
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return timezone.now() > self.expires_at

    def extend_session(self, minutes: int = 30) -> None:
        """
        Extend session expiration time
        تمديد وقت انتهاء الجلسة
        """
        self.expires_at = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=['expires_at'])

class SecurityAuditLog(models.Model):
    """
    Security audit logging model
    نموذج تسجيل تدقيق الأمان
    """
    
    class EventType(models.TextChoices):
        LOGIN_SUCCESS = 'login_success', 'Login Success'
        LOGIN_FAILED = 'login_failed', 'Login Failed'
        LOGOUT = 'logout', 'Logout'
        PASSWORD_CHANGE = 'password_change', 'Password Change'
        ACCOUNT_LOCKED = 'account_locked', 'Account Locked'
        PERMISSION_DENIED = 'permission_denied', 'Permission Denied'
        SUSPICIOUS_ACTIVITY = 'suspicious_activity', 'Suspicious Activity'
    
    user = models.ForeignKey(BusinessUser, on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict)
    severity = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='low')
    
    class Meta:
        db_table = 'security_audit_logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['event_type']),
            models.Index(fields=['severity']),
        ]
        
        
class AutDeManager:
    """
    Comprehensive authentication manager for business applications
    مدير المصادقة الشامل للتطبيقات التجارية
    """
    
    def __init__(self):
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL) if hasattr(settings, 'REDIS_URL') else None
        self.encryption_key = self._get_encryption_key()
        self.max_login_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        self.lockout_duration = getattr(settings, 'LOCKOUT_DURATION_MINUTES', 30)
        self.session_timeout = getattr(settings, 'SESSION_TIMEOUT_MINUTES', 120)
        
    def _get_encryption_key(self) -> Fernet:
        """
        Get or generate encryption key for sensitive data
        الحصول على أو إنشاء مفتاح التشفير للبيانات الحساسة
        """
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            key = Fernet.generate_key()
        return Fernet(key)
    
    def authenticate_user(self, username: str, password: str, ip_address: str, 
                         user_agent: str, device_fingerprint: str) -> AuthenticationResult:
        """
        Authenticate user with comprehensive security checks
        مصادقة المستخدم مع فحوصات أمنية شاملة
        """
        try:
            # Get user by username or email
            user = self._get_user_by_identifier(username)
            
            if not user:
                self._log_security_event(
                    None, SecurityAuditLog.EventType.LOGIN_FAILED,
                    ip_address, user_agent, {'reason': 'user_not_found'}
                )
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    user=None,
                    token=None,
                    expires_at=None,
                    message="Invalid credentials"
                )
            
            # Check if account is locked
            if user.is_account_locked:
                self._log_security_event(
                    user, SecurityAuditLog.EventType.LOGIN_FAILED,
                    ip_address, user_agent, {'reason': 'account_locked'}
                )
                return AuthenticationResult(
                    status=AuthenticationStatus.LOCKED,
                    user=user,
                    token=None,
                    expires_at=None,
                    message=f"Account locked until {user.account_locked_until}"
                )
            
            # Verify password
            if not user.check_password(password):
                user.failed_login_attempts += 1
                
                # Lock account if max attempts reached
                if user.failed_login_attempts >= self.max_login_attempts:
                    user.account_locked_until = timezone.now() + timedelta(minutes=self.lockout_duration)
                    self._log_security_event(
                        user, SecurityAuditLog.EventType.ACCOUNT_LOCKED,
                        ip_address, user_agent, {'attempts': user.failed_login_attempts}
                    )
                
                user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
                
                self._log_security_event(
                    user, SecurityAuditLog.EventType.LOGIN_FAILED,
                    ip_address, user_agent, {'reason': 'invalid_password', 'attempts': user.failed_login_attempts}
                )
                
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    user=user,
                    token=None,
                    expires_at=None,
                    message="Invalid credentials"
                )
            
            # Check if 2FA is required
            if user.two_factor_enabled:
                # Store pending authentication in cache
                pending_key = f"pending_2fa:{user.id}:{secrets.token_urlsafe(16)}"
                cache.set(pending_key, {
                    'user_id': user.id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'device_fingerprint': device_fingerprint
                }, timeout=300)  # 5 minutes
                
                return AuthenticationResult(
                    status=AuthenticationStatus.PENDING_2FA,
                    user=user,
                    token=pending_key,
                    expires_at=timezone.now() + timedelta(minutes=5),
                    message="Two-factor authentication required",
                    requires_2fa=True
                )
            
            # Successful authentication
            return self._complete_authentication(user, ip_address, user_agent, device_fingerprint)
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                user=None,
                token=None,
                expires_at=None,
                message="Authentication service temporarily unavailable"
            )

# ==================== SECTION 4: Two-Factor Authentication ====================

    def verify_two_factor_code(self, pending_token: str, verification_code: str) -> AuthenticationResult:
        """
        Verify two-factor authentication code
        التحقق من رمز المصادقة الثنائية
        """
        try:
            # Get pending authentication data from cache
            pending_data = cache.get(pending_token)
            if not pending_data:
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    user=None,
                    token=None,
                    expires_at=None,
                    message="Invalid or expired verification token"
                )
            
            user = BusinessUser.objects.get(id=pending_data['user_id'])
            
            # Verify TOTP code
            if self._verify_totp_code(user.two_factor_secret, verification_code):
                # Clear pending authentication
                cache.delete(pending_token)
                
                # Complete authentication
                return self._complete_authentication(
                    user, 
                    pending_data['ip_address'],
                    pending_data['user_agent'],
                    pending_data['device_fingerprint']
                )
            else:
                self._log_security_event(
                    user, SecurityAuditLog.EventType.LOGIN_FAILED,
                    pending_data['ip_address'], pending_data['user_agent'],
                    {'reason': 'invalid_2fa_code'}
                )
                return AuthenticationResult(
                    status=AuthenticationStatus.FAILED,
                    user=user,
                    token=None,
                    expires_at=None,
                    message="Invalid verification code"
                )
                
        except BusinessUser.DoesNotExist:
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                user=None,
                token=None,
                expires_at=None,
                message="User not found"
            )
        except Exception as e:
            logger.error(f"2FA verification error: {str(e)}")
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                user=None,
                token=None,
                expires_at=None,
                message="Verification service temporarily unavailable"
            )

    def _verify_totp_code(self, secret: str, code: str) -> bool:
        """
        Verify Time-based One-Time Password (TOTP) code
        التحقق من رمز كلمة المرور لمرة واحدة القائم على الوقت
        """
        import pyotp
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)  # Allow 30 seconds window
        except Exception as e:
            logger.error(f"TOTP verification error: {str(e)}")
            return False

    def setup_two_factor_auth(self, user: BusinessUser) -> Dict[str, Any]:
        """
        Setup two-factor authentication for user
        إعداد المصادقة الثنائية للمستخدم
        """
        import pyotp
        import qrcode
        from io import BytesIO
        import base64
        
        try:
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret)
            
            # Generate QR code URI
            provisioning_uri = totp.provisioning_uri(
                name=user.email,
                issuer_name="SecureApp Authentication"
            )
            
            # Generate QR code image
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_code_image = base64.b64encode(buffer.getvalue()).decode()
            
            # Store secret temporarily (user needs to confirm setup)
            cache.set(f"2fa_setup:{user.id}", secret, timeout=600)  # 10 minutes
            
            return {
                'secret': secret,
                'qr_code': qr_code_image,
                'provisioning_uri': provisioning_uri,
                'backup_codes': self._generate_backup_codes(user)
            }
            
        except Exception as e:
            logger.error(f"2FA setup error: {str(e)}")
            raise

    def _generate_backup_codes(self, user: BusinessUser) -> List[str]:
        """
        Generate backup codes for 2FA recovery
        إنشاء رموز احتياطية لاستعادة المصادقة الثنائية
        """
        backup_codes = []
        for _ in range(10):
            code = secrets.token_hex(4).upper()
            backup_codes.append(f"{code[:4]}-{code[4:]}")
        
        # Store encrypted backup codes
        encrypted_codes = self.encryption_key.encrypt(
            ','.join(backup_codes).encode()
        )
        
        # Store in cache or database (implement as needed)
        cache.set(f"backup_codes:{user.id}", encrypted_codes.decode(), timeout=86400 * 30)  # 30 days
        
        return backup_codes

# ==================== SECTION 5: Session Management Advanced ====================

    def create_session(self, user: BusinessUser, ip_address: str, 
                      user_agent: str, device_fingerprint: str) -> UserSession:
        """
        Create new authenticated session
        إنشاء جلسة مصادقة جديدة
        """
        try:
            # Generate unique session key
            session_key = self._generate_session_key()
            
            # Create session record
            session = UserSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=device_fingerprint,
                expires_at=timezone.now() + timedelta(minutes=self.session_timeout)
            )
            
            # Store session in Redis for fast lookup
            if self.redis_client:
                session_data = {
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'created_at': session.created_at.isoformat(),
                    'expires_at': session.expires_at.isoformat()
                }
                self.redis_client.setex(
                    f"session:{session_key}",
                    self.session_timeout * 60,
                    json.dumps(session_data)
                )
            
            # Update user activity
            user.last_activity = timezone.now()
            user.login_count += 1
            user.save(update_fields=['last_activity', 'login_count'])
            
            return session
            
        except Exception as e:
            logger.error(f"Session creation error: {str(e)}")
            raise

    def validate_session(self, session_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate and retrieve session information
        التحقق من صحة واسترداد معلومات الجلسة
        """
        try:
            # Check Redis first for performance
            if self.redis_client:
                session_data = self.redis_client.get(f"session:{session_key}")
                if session_data:
                    data = json.loads(session_data)
                    # Check if session is still valid
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if timezone.now() < expires_at:
                        return data
                    else:
                        # Session expired, clean up
                        self.redis_client.delete(f"session:{session_key}")
                        return None
            
            # Fallback to database
            try:
                session = UserSession.objects.select_related('user').get(
                    session_key=session_key,
                    is_active=True
                )
                
                if session.is_expired:
                    session.is_active = False
                    session.save(update_fields=['is_active'])
                    return None
                
                # Update last activity
                session.last_activity = timezone.now()
                session.save(update_fields=['last_activity'])
                
                return {
                    'user_id': session.user.id,
                    'username': session.user.username,
                    'role': session.user.role,
                    'created_at': session.created_at.isoformat(),
                    'expires_at': session.expires_at.isoformat()
                }
                
            except UserSession.DoesNotExist:
                return None
                
        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            return None

    def invalidate_session(self, session_key: str) -> bool:
        """
        Invalidate user session (logout)
        إبطال جلسة المستخدم (تسجيل الخروج)
        """
        try:
            # Remove from Redis
            if self.redis_client:
                self.redis_client.delete(f"session:{session_key}")
            
            # Update database
            UserSession.objects.filter(session_key=session_key).update(
                is_active=False
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Session invalidation error: {str(e)}")
            return False

    def invalidate_all_user_sessions(self, user: BusinessUser) -> int:
        """
        Invalidate all sessions for a specific user
        إبطال جميع جلسات مستخدم معين
        """
        try:
            # Get all active sessions for user
            sessions = UserSession.objects.filter(user=user, is_active=True)
            session_keys = list(sessions.values_list('session_key', flat=True))
            
            # Remove from Redis
            if self.redis_client and session_keys:
                redis_keys = [f"session:{key}" for key in session_keys]
                self.redis_client.delete(*redis_keys)
            
            # Update database
            count = sessions.update(is_active=False)
            
            self._log_security_event(
                user, SecurityAuditLog.EventType.LOGOUT,
                '0.0.0.0', 'System',
                {'reason': 'all_sessions_invalidated', 'count': count}
            )
            
            return count
            
        except Exception as e:
            logger.error(f"Bulk session invalidation error: {str(e)}")
            return 0

# ==================== SECTION 6: Security Utilities ====================

    def _generate_session_key(self) -> str:
        """
        Generate cryptographically secure session key
        إنشاء مفتاح جلسة آمن تشفيرياً
        """
        return hashlib.sha256(
            f"{secrets.token_urlsafe(32)}{timezone.now().isoformat()}".encode()
        ).hexdigest()

    def _get_user_by_identifier(self, identifier: str) -> Optional[BusinessUser]:
        """
        Get user by username or email
        الحصول على المستخدم بواسطة اسم المستخدم أو البريد الإلكتروني
        """
        try:
            if '@' in identifier:
                return BusinessUser.objects.get(email=identifier, is_active=True)
            else:
                return BusinessUser.objects.get(username=identifier, is_active=True)
        except BusinessUser.DoesNotExist:
            return None

    def _complete_authentication(self, user: BusinessUser, ip_address: str,
                                user_agent: str, device_fingerprint: str) -> AuthenticationResult:
        """
        Complete successful authentication process
        إكمال عملية المصادقة الناجحة
        """
        try:
            # Reset failed login attempts
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
            
            # Create session
            session = self.create_session(user, ip_address, user_agent, device_fingerprint)
            
            # Generate JWT token
            token = self._generate_jwt_token(user, session.session_key)
            
            # Log successful authentication
            self._log_security_event(
                user, SecurityAuditLog.EventType.LOGIN_SUCCESS,
                ip_address, user_agent, {'session_id': session.session_key}
            )
            
            return AuthenticationResult(
                status=AuthenticationStatus.SUCCESS,
                user=user,
                token=token,
                expires_at=session.expires_at,
                message="Authentication successful",
                session_id=session.session_key
            )
            
        except Exception as e:
            logger.error(f"Authentication completion error: {str(e)}")
            return AuthenticationResult(
                status=AuthenticationStatus.FAILED,
                user=user,
                token=None,
                expires_at=None,
                message="Authentication completion failed"
            )

    def _generate_jwt_token(self, user: BusinessUser, session_key: str) -> str:
        """
        Generate JWT token for authenticated user
        إنشاء رمز JWT للمستخدم المصادق عليه
        """
        payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'session_key': session_key,
            'iat': timezone.now().timestamp(),
            'exp': (timezone.now() + timedelta(minutes=self.session_timeout)).timestamp()
        }
        
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    def _log_security_event(self, user: Optional[BusinessUser], event_type: str,
                           ip_address: str, user_agent: str, details: Dict[str, Any]) -> None:
        """
        Log security event for audit purposes
        تسجيل حدث أمني لأغراض التدقيق
        """
        try:
            # Determine severity based on event type
            severity_map = {
                SecurityAuditLog.EventType.LOGIN_SUCCESS: 'low',
                SecurityAuditLog.EventType.LOGIN_FAILED: 'medium',
                SecurityAuditLog.EventType.LOGOUT: 'low',
                SecurityAuditLog.EventType.PASSWORD_CHANGE: 'medium',
                SecurityAuditLog.EventType.ACCOUNT_LOCKED: 'high',
                SecurityAuditLog.EventType.PERMISSION_DENIED: 'medium',
                SecurityAuditLog.EventType.SUSPICIOUS_ACTIVITY: 'critical',
            }
            
            SecurityAuditLog.objects.create(
                user=user,
                event_type=event_type,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                severity=severity_map.get(event_type, 'low')
            )
            
        except Exception as e:
            logger.error(f"Security logging error: {str(e)}")

# ==================== SECTION 7: Advanced Security Features ====================

    def detect_suspicious_activity(self, user: BusinessUser, ip_address: str,
                                  user_agent: str) -> bool:
        """
        Detect potentially suspicious login activity
        اكتشاف نشاط تسجيل دخول مشبوه محتمل
        """
        try:
            # Check for multiple failed attempts from same IP
            recent_failures = SecurityAuditLog.objects.filter(
                event_type=SecurityAuditLog.EventType.LOGIN_FAILED,
                ip_address=ip_address,
                timestamp__gte=timezone.now() - timedelta(hours=1)
            ).count()
            
            if recent_failures >= 10:
                return True
            
            # Check for logins from new locations
            if user:
                recent_sessions = UserSession.objects.filter(
                    user=user,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).values_list('ip_address', flat=True).distinct()
                
                if ip_address not in recent_sessions and len(recent_sessions) > 0:
                    # New location detected
                    return True
            
            # Check for unusual user agent
            if user:
                common_agents = UserSession.objects.filter(
                    user=user,
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).values_list('user_agent', flat=True).distinct()
                
                if user_agent not in common_agents and len(common_agents) > 0:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Suspicious activity detection error: {str(e)}")
            return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from database and cache
        تنظيف الجلسات المنتهية الصلاحية من قاعدة البيانات والذاكرة التخزينية
        """
        try:
            # Get expired sessions
            expired_sessions = UserSession.objects.filter(
                expires_at__lt=timezone.now(),
                is_active=True
            )
            
            session_keys = list(expired_sessions.values_list('session_key', flat=True))
            
            # Remove from Redis
            if self.redis_client and session_keys:
                redis_keys = [f"session:{key}" for key in session_keys]
                self.redis_client.delete(*redis_keys)
            
            # Update database
            count = expired_sessions.update(is_active=False)
            
            logger.info(f"Cleaned up {count} expired sessions")
            return count
            
        except Exception as e:
            logger.error(f"Session cleanup error: {str(e)}")
            return 0

    def get_user_security_summary(self, user: BusinessUser) -> Dict[str, Any]:
        """
        Get comprehensive security summary for user
        الحصول على ملخص أمني شامل للمستخدم
        """
        try:
            # Get recent login attempts
            recent_logins = SecurityAuditLog.objects.filter(
                user=user,
                event_type__in=[
                    SecurityAuditLog.EventType.LOGIN_SUCCESS,
                    SecurityAuditLog.EventType.LOGIN_FAILED
                ],
                timestamp__gte=timezone.now() - timedelta(days=30)
            ).order_by('-timestamp')[:10]
            
            # Get active sessions
            active_sessions = UserSession.objects.filter(
                user=user,
                is_active=True,
                expires_at__gt=timezone.now()
            ).order_by('-created_at')
            
            # Calculate security score
            security_score = self._calculate_security_score(user)
            
            return {
                'user_id': user.id,
                'username': user.username,
                'security_score': security_score,
                'two_factor_enabled': user.two_factor_enabled,
                'last_password_change': user.last_password_change.isoformat() if user.last_password_change else None,
                'password_needs_change': user.password_needs_change,
                'account_locked': user.is_account_locked,
                'failed_attempts': user.failed_login_attempts,
                'active_sessions_count': active_sessions.count(),
                'recent_login_attempts': [
                    {
                        'event_type': log.event_type,
                        'timestamp': log.timestamp.isoformat(),
                        'ip_address': log.ip_address,
                        'success': log.event_type == SecurityAuditLog.EventType.LOGIN_SUCCESS
                    }
                    for log in recent_logins
                ],
                'active_sessions': [
                    {
                        'session_key': session.session_key[:8] + '...',  # Partial key for security
                        'ip_address': session.ip_address,
                        'created_at': session.created_at.isoformat(),
                        'last_activity': session.last_activity.isoformat(),
                        'expires_at': session.expires_at.isoformat()
                    }
                    for session in active_sessions
                ]
            }
            
        except Exception as e:
            logger.error(f"Security summary error: {str(e)}")
            return {'error': 'Unable to generate security summary'}

    def _calculate_security_score(self, user: BusinessUser) -> int:
        """
        Calculate security score for user (0-100)
        حساب نقاط الأمان للمستخدم (0-100)
        """
        score = 0
        
        # Two-factor authentication (+30 points)
        if user.two_factor_enabled:
            score += 30
        
        # Recent password change (+20 points)
        if user.last_password_change and user.last_password_change > timezone.now() - timedelta(days=90):
            score += 20
        
        # No recent failed attempts (+20 points)
        if user.failed_login_attempts == 0:
            score += 20
        
        # Account not locked (+10 points)
        if not user.is_account_locked:
            score += 10
        
        # Regular activity (+10 points)
        if user.last_activity and user.last_activity > timezone.now() - timedelta(days=7):
            score += 10
        
        # Strong password policy compliance (+10 points)
        # This would require additional password strength validation
        score += 10
        
        return min(score, 100)  # Cap at 100
