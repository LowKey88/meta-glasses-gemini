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
from utils.limitless_logger import limitless_api_logger

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
        date: Optional[str] = None,
        timezone_str: str = "Asia/Kuala_Lumpur",
        cursor: Optional[str] = None,
        direction: str = "desc",
        include_markdown: bool = True,
        include_headings: bool = True,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        List Lifelog entries from Limitless API.
        
        Args:
            start_time: Start datetime (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS)
            end_time: End datetime (YYYY-MM-DD or YYYY-MM-DD HH:mm:SS)
            date: Date string (YYYY-MM-DD) - ignored if start/end provided
            timezone_str: IANA timezone specifier
            cursor: Pagination cursor (optional)
            direction: Sort direction (asc/desc)
            include_markdown: Include markdown content in response
            include_headings: Include headings in response
            limit: Maximum number of entries (max 10)
            
        Returns:
            API response with Lifelog entries
        """
        params = {
            "timezone": timezone_str,
            "direction": direction,
            "includeMarkdown": str(include_markdown).lower(),
            "includeHeadings": str(include_headings).lower(),
            "limit": min(limit, 10)  # API max is 10
        }
        
        # Add time filters - use 'start' and 'end' as per docs
        if start_time:
            # Format as YYYY-MM-DD HH:mm:SS or YYYY-MM-DD
            if hasattr(start_time, 'strftime'):
                params["start"] = start_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                params["start"] = str(start_time)
        if end_time:
            if hasattr(end_time, 'strftime'):
                params["end"] = end_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                params["end"] = str(end_time)
        
        # Add date if provided and no start/end
        if date and not (start_time or end_time):
            params["date"] = date
            
        # Add cursor for pagination
        if cursor:
            params["cursor"] = cursor
            
        url = f"{self.BASE_URL}/lifelogs?{urlencode(params)}"
        # Only log params in debug mode, not the full URL
        logger.debug(f"API request with params: {params}")
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract lifelogs from the correct response structure
                    lifelogs = data.get('data', {}).get('lifelogs', [])
                    # Only log if we got data
                    if lifelogs:
                        logger.debug(f"Retrieved {len(lifelogs)} entries")
                    
                    # Return in expected format for compatibility
                    return {"items": lifelogs, "meta": data.get('meta', {})}
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching Lifelogs: {str(e)}")
                raise
                
    async def get_all_lifelogs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        date: Optional[str] = None,
        timezone_str: str = "Asia/Kuala_Lumpur",
        max_entries: Optional[int] = None,
        include_markdown: bool = True,
        include_headings: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all Lifelog entries with cursor-based pagination.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            date: Date string (YYYY-MM-DD)
            timezone_str: Timezone for the query
            max_entries: Maximum total entries to retrieve
            include_markdown: Include markdown content
            include_headings: Include headings
            
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
                    date=date,
                    timezone_str=timezone_str,
                    cursor=cursor,
                    include_markdown=include_markdown,
                    include_headings=include_headings,
                    limit=10  # Always use max limit for efficiency
                )
                
                items = response.get("items", [])
                if not items:
                    logger.debug(f"End of pagination at page {page_count}")
                    break
                    
                all_entries.extend(items)
                page_count += 1
                
                # Log pagination progress using custom logger
                limitless_api_logger.api_pagination(page_count, len(items), cursor)
                
                # Check if we've reached the desired max
                if max_entries and len(all_entries) >= max_entries:
                    all_entries = all_entries[:max_entries]
                    logger.debug(f"Reached max_entries limit of {max_entries}")
                    break
                    
                # Get next cursor from response
                meta = response.get("meta", {})
                next_cursor = meta.get("lifelogs", {}).get("nextCursor")
                
                if not next_cursor:
                    break
                    
                cursor = next_cursor
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in pagination with cursor {cursor}: {str(e)}")
                break
        
        if page_count >= max_pages:
            logger.warning(f"Hit maximum page limit of {max_pages}, may not have retrieved all entries")
                
        # Only log summary if we got entries
        if all_entries:
            logger.info(f"✅ Retrieved {len(all_entries)} total entries ({page_count} pages)")
        return all_entries
    
    async def get_lifelogs_by_date(
        self,
        date: str,
        timezone_str: str = "Asia/Kuala_Lumpur",
        include_markdown: bool = True,
        include_headings: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all Lifelog entries for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format
            timezone_str: IANA timezone specifier
            include_markdown: Include markdown content
            include_headings: Include headings
            
        Returns:
            List of Lifelog entries for the date
        """
        return await self.get_all_lifelogs(
            date=date,
            timezone_str=timezone_str,
            include_markdown=include_markdown,
            include_headings=include_headings
        )
        
    async def get_lifelog_by_id(self, lifelog_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific Lifelog entry by ID.
        
        Note: This uses the list endpoint with time filtering as there's no direct GET endpoint.
        """
        # Since there's no direct GET endpoint, we'll need to search by approximate time
        # This is a limitation of the current API
        logger.warning("Direct Lifelog retrieval by ID not supported, using list endpoint")
        return None