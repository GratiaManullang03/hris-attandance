from atams import AtamsBaseSettings


class Settings(AtamsBaseSettings):
    """
    Application Settings

    Inherits from AtamsBaseSettings which includes:
    - DATABASE_URL (required)
    - ATLAS_SSO_URL, ATLAS_APP_CODE, ATLAS_ENCRYPTION_KEY, ATLAS_ENCRYPTION_IV
    - ENCRYPTION_ENABLED, ENCRYPTION_KEY, ENCRYPTION_IV (response encryption)
    - LOGGING_ENABLED, LOG_LEVEL, LOG_TO_FILE, LOG_FILE_PATH
    - CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS
    - RATE_LIMIT_ENABLED, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
    - DEBUG

    All settings can be overridden via .env file or by redefining them here.
    """
    APP_NAME: str
    APP_VERSION: str
    DEBUG: bool
    
    # QR JWT Settings
    QR_JWT_SECRET: str
    QR_JWT_ALG: str
    QR_ROTATION_SECONDS: int
    QR_EXPIRE_GRACE_SECONDS: int
    
    # Display Authentication
    DISPLAY_API_KEY: str
    
    # Auto-checkout settings
    AUTO_CHECKOUT_CRON: str
    AUTO_CHECKOUT_REASON: str
    
    # Geofence settings
    GEOFENCE_ENFORCED: bool
    DEFAULT_GEOFENCE_RADIUS_M: int
    
    # Rate limiting for scan endpoint
    RATE_LIMIT_SCAN_PER_MIN: int


settings = Settings()
