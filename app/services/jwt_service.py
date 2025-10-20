"""
JWT Service for QR token generation and validation
"""
import jwt
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.config import settings
from atams.exceptions import BadRequestException


class JwtService:
    def __init__(self) -> None:
        self.secret = settings.QR_JWT_SECRET
        self.algorithm = settings.QR_JWT_ALG
        self.rotation_seconds = settings.QR_ROTATION_SECONDS
        self.grace_seconds = settings.QR_EXPIRE_GRACE_SECONDS

    def generate_rolling_token(self, site_id: str) -> Dict[str, Any]:
        """
        Generate rolling JWT token for QR display
        
        Returns:
            dict: {token: str, slot: int, expires_in: int}
        """
        now = datetime.utcnow()
        slot = int(time.time())  # Current Unix timestamp as slot
        expires_in = self.rotation_seconds + self.grace_seconds
        exp = now + timedelta(seconds=expires_in)
        
        # Generate unique JTI for anti-replay
        jti = str(uuid.uuid4())
        
        payload = {
            "iss": "hris-attendance",
            "aud": f"site:{site_id}",
            "si_id": site_id,
            "slot": slot,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "mode": "AUTO"
        }
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        
        return {
            "token": token,
            "slot": slot,
            "expires_in": expires_in
        }

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token from QR scan
        
        Args:
            token: JWT string from QR code
            
        Returns:
            dict: Decoded payload
            
        Raises:
            BadRequestException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_exp": True, "verify_aud": False}  # We'll verify aud manually
            )
            
            # Validate required fields
            required_fields = ["iss", "aud", "si_id", "slot", "jti", "iat", "exp"]
            for field in required_fields:
                if field not in payload:
                    raise BadRequestException(f"Missing required field: {field}")
            
            # Validate issuer
            if payload["iss"] != "hris-attendance":
                raise BadRequestException("Invalid token issuer")
            
            # Validate audience format
            if not payload["aud"].startswith("site:"):
                raise BadRequestException("Invalid token audience")
            
            # Extract site_id from audience
            expected_site_id = payload["aud"].replace("site:", "")
            if expected_site_id != payload["si_id"]:
                raise BadRequestException("Site ID mismatch in token")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise BadRequestException("Token expired")
        except jwt.InvalidTokenError as e:
            raise BadRequestException(f"Invalid token: {str(e)}")

    def extract_site_id(self, token: str) -> str:
        """
        Extract site ID from token without full validation (for quick checks)
        
        Args:
            token: JWT string
            
        Returns:
            str: Site ID
            
        Raises:
            BadRequestException: If token format is invalid
        """
        try:
            # Decode without verification for quick extraction
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
            
            if "si_id" not in payload:
                raise BadRequestException("No site ID in token")
                
            return payload["si_id"]
            
        except jwt.InvalidTokenError:
            raise BadRequestException("Invalid token format")