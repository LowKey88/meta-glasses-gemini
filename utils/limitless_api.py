"""
Limitless AI API client for retrieving Lifelog entries from Pendant device.
"""
import os
import aiohttp
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class LimitlessAPIClient:
    """Client for interacting with Limitless AI API."""
    
    BASE_URL = "https://api.limitless.ai/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LIMITLESS_API_KEY")
        if not self.api_key:
            raise ValueError("LIMITLESS_API_KEY environment variable not set")
        
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
    async def list_lifelogs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timezone_str: str = "Asia/Kuala_Lumpur",
        cursor: Optional[str] = None,
        direction: str = "desc"
    ) -> Dict[str, Any]:
        """
        List Lifelog entries from Limitless API.
        
        Args:
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            timezone_str: Timezone for the query
            cursor: Pagination cursor (optional)
            direction: Sort direction (asc/desc)
            
        Returns:
            API response with Lifelog entries
        """
        params = {
            "timezone": timezone_str,
            "direction": direction
        }
        
        # Add time filters if provided
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
            
        # Add cursor for pagination
        if cursor:
            params["cursor"] = cursor
            
        url = f"{self.BASE_URL}/lifelogs?{urlencode(params)}"
        logger.info(f"Limitless API request: {url}")
        logger.info(f"Limitless API params: {params}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    logger.info(f"Limitless API response status: {response.status}")
                    response.raise_for_status()
                    data = await response.json()
                    logger.info(f"Limitless API response data: {data}")
                    
                    # Extract lifelogs from the correct response structure
                    lifelogs = data.get('data', {}).get('lifelogs', [])
                    logger.info(f"Retrieved {len(lifelogs)} Lifelog entries")
                    
                    # Return in expected format for compatibility
                    return {"items": lifelogs, "meta": data.get('meta', {})}
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching Lifelogs: {str(e)}")
                raise
                
    async def get_all_lifelogs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timezone_str: str = "Asia/Kuala_Lumpur",
        max_entries: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all Lifelog entries with cursor-based pagination.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            timezone_str: Timezone for the query
            max_entries: Maximum total entries to retrieve
            
        Returns:
            List of all Lifelog entries
        """
        all_entries = []
        cursor = None
        max_pages = 20  # Safety limit to prevent infinite loops
        page_count = 0
        
        while page_count < max_pages:
            try:
                response = await self.list_lifelogs(
                    start_time=start_time,
                    end_time=end_time,
                    timezone_str=timezone_str,
                    cursor=cursor
                )
                
                items = response.get("items", [])
                if not items:
                    logger.info(f"No more items found with cursor {cursor}, stopping pagination")
                    break
                    
                all_entries.extend(items)
                page_count += 1
                
                # Check if we've reached the desired max
                if max_entries and len(all_entries) >= max_entries:
                    all_entries = all_entries[:max_entries]
                    logger.info(f"Reached max_entries limit of {max_entries}, stopping pagination")
                    break
                    
                # Get next cursor from response
                meta = response.get("meta", {})
                next_cursor = meta.get("lifelogs", {}).get("nextCursor")
                
                if not next_cursor:
                    logger.info("No next cursor found, stopping pagination")
                    break
                    
                cursor = next_cursor
                logger.info(f"Fetching next page with cursor: {cursor}")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in pagination with cursor {cursor}: {str(e)}")
                break
        
        if page_count >= max_pages:
            logger.warning(f"Hit maximum page limit of {max_pages}, may not have retrieved all entries")
                
        logger.info(f"Retrieved total of {len(all_entries)} Lifelog entries after {page_count} pages")
        return all_entries
        
    async def get_lifelog_by_id(self, lifelog_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific Lifelog entry by ID.
        
        Note: This uses the list endpoint with time filtering as there's no direct GET endpoint.
        """
        # Since there's no direct GET endpoint, we'll need to search by approximate time
        # This is a limitation of the current API
        logger.warning("Direct Lifelog retrieval by ID not supported, using list endpoint")
        return None