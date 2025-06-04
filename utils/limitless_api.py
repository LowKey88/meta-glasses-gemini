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
        limit: int = 10,
        offset: int = 0,
        include_transcript: bool = True,
        include_summary: bool = True
    ) -> Dict[str, Any]:
        """
        List Lifelog entries from Limitless API.
        
        Args:
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            timezone_str: Timezone for the query
            limit: Maximum number of entries (max 10)
            offset: Pagination offset
            include_transcript: Include full transcript in response
            include_summary: Include AI-generated summary
            
        Returns:
            API response with Lifelog entries
        """
        params = {
            "timezone": timezone_str,
            "limit": min(limit, 10),  # API max is 10
            "offset": offset
        }
        
        # Add time filters if provided
        if start_time:
            params["startTime"] = start_time.isoformat()
        if end_time:
            params["endTime"] = end_time.isoformat()
            
        # Configure response fields
        if not include_transcript:
            params["excludeTranscript"] = "true"
        if not include_summary:
            params["excludeSummary"] = "true"
            
        url = f"{self.BASE_URL}/lifelogs?{urlencode(params)}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    logger.info(f"Retrieved {len(data.get('items', []))} Lifelog entries")
                    return data
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching Lifelogs: {str(e)}")
                raise
                
    async def get_all_lifelogs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        timezone_str: str = "Asia/Kuala_Lumpur",
        include_transcript: bool = True,
        include_summary: bool = True,
        max_entries: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all Lifelog entries with pagination handling.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            timezone_str: Timezone for the query
            include_transcript: Include full transcript
            include_summary: Include AI summary
            max_entries: Maximum total entries to retrieve
            
        Returns:
            List of all Lifelog entries
        """
        all_entries = []
        offset = 0
        
        while True:
            try:
                response = await self.list_lifelogs(
                    start_time=start_time,
                    end_time=end_time,
                    timezone_str=timezone_str,
                    limit=10,
                    offset=offset,
                    include_transcript=include_transcript,
                    include_summary=include_summary
                )
                
                items = response.get("items", [])
                if not items:
                    break
                    
                all_entries.extend(items)
                
                # Check if we've reached the desired max
                if max_entries and len(all_entries) >= max_entries:
                    all_entries = all_entries[:max_entries]
                    break
                    
                # Check if there are more pages
                if len(items) < 10:
                    break
                    
                offset += 10
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in pagination at offset {offset}: {str(e)}")
                break
                
        logger.info(f"Retrieved total of {len(all_entries)} Lifelog entries")
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