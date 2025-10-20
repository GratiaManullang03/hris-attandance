"""
API Dependencies
Provides authentication and authorization dependencies using ATAMS factory pattern
"""
from atams.sso import create_atlas_client, create_auth_dependencies
from app.core.config import settings

# Initialize Atlas SSO client using factory
atlas_client = create_atlas_client(settings)

# Create auth dependencies using factory
get_current_user, require_auth, require_min_role_level, require_role_level = create_auth_dependencies(atlas_client)

# Export for use in endpoints
__all__ = [
    "atlas_client",
    "get_current_user",
    "require_auth",
    "require_min_role_level",
    "require_role_level",
]
