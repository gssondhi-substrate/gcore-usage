"""
Authentication and token management for Gcore API.
"""
import time
import logging
from typing import Optional
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages Gcore API token generation and caching."""
    
    def __init__(self, auth_url: str, username: str, password: str, cache_duration: int = 1800):
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.cache_duration = cache_duration
        self._token_cache = {"token": None, "expires_at": 0}
    
    async def get_token(self) -> str:
        """Get a valid Gcore API token, using cache if available."""
        current_time = time.time()
        
        # Check if we have a valid cached token
        if (self._token_cache["token"] and 
            self._token_cache["expires_at"] > current_time + 60):
            logger.info("Using cached Gcore token")
            return self._token_cache["token"]
        
        # Validate credentials
        if not self.username or not self.password:
            raise HTTPException(
                500, 
                "Gcore credentials not configured. Set GCORE_USERNAME and GCORE_PASSWORD environment variables."
            )
        
        # Generate new token
        logger.info("Generating new Gcore token")
        auth_payload = {
            "username": self.username,
            "password": self.password
        }
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            try:
                response = await client.post(
                    self.auth_url,
                    json=auth_payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                auth_response = response.json()
                
                # Extract access token
                access_token = auth_response.get("access") or auth_response.get("access_token")
                if not access_token:
                    logger.error(f"No access token in auth response: {auth_response}")
                    raise HTTPException(502, "Failed to get access token from Gcore auth API")
                
                # Cache the token
                expires_in = auth_response.get("expires_in", self.cache_duration)
                self._token_cache["token"] = access_token
                self._token_cache["expires_at"] = current_time + expires_in
                
                logger.info(f"Successfully generated and cached Gcore token (expires in {expires_in}s)")
                return access_token
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Gcore auth failed with status {e.response.status_code}: {e.response.text}")
                if e.response.status_code == 401:
                    raise HTTPException(401, "Invalid Gcore credentials")
                raise HTTPException(502, f"Gcore auth failed: {e.response.status_code}")
            except Exception as e:
                logger.error(f"Unexpected error during Gcore auth: {str(e)}")
                raise HTTPException(502, f"Failed to authenticate with Gcore: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear the token cache."""
        self._token_cache = {"token": None, "expires_at": 0}
        logger.info("Token cache cleared")
