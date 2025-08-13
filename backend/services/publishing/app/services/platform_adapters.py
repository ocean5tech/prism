"""
Platform Adapters for Different Publishing Platforms
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
import json
from datetime import datetime
import structlog

from ..models import PlatformConnection
from ..schemas import PlatformType

logger = structlog.get_logger()

class PlatformAdapter(ABC):
    """Abstract base class for platform adapters"""
    
    @abstractmethod
    async def publish_content(
        self,
        connection: PlatformConnection,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish content to the platform"""
        pass
    
    @abstractmethod
    async def get_engagement_metrics(
        self,
        connection: PlatformConnection,
        post_id: str
    ) -> Dict[str, Any]:
        """Get engagement metrics for a published post"""
        pass
    
    @abstractmethod
    async def validate_connection(self, connection: PlatformConnection) -> bool:
        """Validate platform connection"""
        pass

class LinkedInAdapter(PlatformAdapter):
    """LinkedIn publishing adapter"""
    
    def __init__(self):
        self.api_base = "https://api.linkedin.com/v2"
        self.http_client = httpx.AsyncClient()
    
    async def publish_content(
        self,
        connection: PlatformConnection,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish content to LinkedIn"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Prepare LinkedIn post data
        post_data = {
            "author": f"urn:li:person:{connection.account_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": f"{title}\n\n{content}"
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        try:
            response = await self.http_client.post(
                f"{self.api_base}/ugcPosts",
                headers=headers,
                json=post_data,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "post_id": result.get("id"),
                "url": f"https://linkedin.com/posts/{result.get('id')}",
                "platform_response": result,
                "success": True
            }
            
        except httpx.HTTPError as e:
            logger.error(f"LinkedIn publishing failed: {str(e)}")
            raise Exception(f"LinkedIn API error: {str(e)}")
    
    async def get_engagement_metrics(
        self,
        connection: PlatformConnection,
        post_id: str
    ) -> Dict[str, Any]:
        """Get LinkedIn engagement metrics"""
        
        # Note: LinkedIn metrics require special permissions
        # This is a simplified implementation
        return {
            "views": 0,
            "clicks": 0,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "platform_specific": {
                "impressions": 0,
                "unique_impressions": 0
            }
        }
    
    async def validate_connection(self, connection: PlatformConnection) -> bool:
        """Validate LinkedIn connection"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                f"{self.api_base}/people/~",
                headers=headers,
                timeout=10.0
            )
            return response.status_code == 200
        except:
            return False

class MediumAdapter(PlatformAdapter):
    """Medium publishing adapter"""
    
    def __init__(self):
        self.api_base = "https://api.medium.com/v1"
        self.http_client = httpx.AsyncClient()
    
    async def publish_content(
        self,
        connection: PlatformConnection,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish content to Medium"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Prepare Medium post data
        post_data = {
            "title": title,
            "contentFormat": "html",  # or "markdown"
            "content": content,
            "publishStatus": "public",  # or "draft", "unlisted"
            "tags": metadata.get("tags", [])[:5  # Medium allows max 5 tags
        }
        
        try:
            # First get user ID
            user_response = await self.http_client.get(
                f"{self.api_base}/me",
                headers=headers
            )
            user_response.raise_for_status()
            user_id = user_response.json()["data"]["id"]
            
            # Publish post
            response = await self.http_client.post(
                f"{self.api_base}/users/{user_id}/posts",
                headers=headers,
                json=post_data,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()["data"]
            
            return {
                "post_id": result.get("id"),
                "url": result.get("url"),
                "platform_response": result,
                "success": True
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Medium publishing failed: {str(e)}")
            raise Exception(f"Medium API error: {str(e)}")
    
    async def get_engagement_metrics(
        self,
        connection: PlatformConnection,
        post_id: str
    ) -> Dict[str, Any]:
        """Get Medium engagement metrics"""
        
        # Medium doesn't provide detailed metrics via API for most users
        return {
            "views": 0,
            "clicks": 0,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "platform_specific": {
                "claps": 0,
                "reading_time": 0
            }
        }
    
    async def validate_connection(self, connection: PlatformConnection) -> bool:
        """Validate Medium connection"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                f"{self.api_base}/me",
                headers=headers,
                timeout=10.0
            )
            return response.status_code == 200
        except:
            return False

class TwitterAdapter(PlatformAdapter):
    """Twitter publishing adapter"""
    
    def __init__(self):
        self.api_base = "https://api.twitter.com/2"
        self.http_client = httpx.AsyncClient()
    
    async def publish_content(
        self,
        connection: PlatformConnection,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish content to Twitter"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json"
        }
        
        # Combine title and content, respecting Twitter's character limit
        tweet_text = f"{title}\n\n{content}"
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
        
        post_data = {
            "text": tweet_text
        }
        
        try:
            response = await self.http_client.post(
                f"{self.api_base}/tweets",
                headers=headers,
                json=post_data,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()["data"]
            
            return {
                "post_id": result.get("id"),
                "url": f"https://twitter.com/i/status/{result.get('id')}",
                "platform_response": result,
                "success": True
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Twitter publishing failed: {str(e)}")
            raise Exception(f"Twitter API error: {str(e)}")
    
    async def get_engagement_metrics(
        self,
        connection: PlatformConnection,
        post_id: str
    ) -> Dict[str, Any]:
        """Get Twitter engagement metrics"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                f"{self.api_base}/tweets/{post_id}?tweet.fields=public_metrics",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                metrics = data.get("public_metrics", {})
                
                return {
                    "views": metrics.get("impression_count", 0),
                    "clicks": 0,  # Not available in basic metrics
                    "likes": metrics.get("like_count", 0),
                    "shares": metrics.get("retweet_count", 0),
                    "comments": metrics.get("reply_count", 0),
                    "platform_specific": {
                        "quotes": metrics.get("quote_count", 0),
                        "bookmarks": metrics.get("bookmark_count", 0)
                    }
                }
        except:
            pass
        
        # Return default metrics if API call fails
        return {
            "views": 0,
            "clicks": 0,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "platform_specific": {}
        }
    
    async def validate_connection(self, connection: PlatformConnection) -> bool:
        """Validate Twitter connection"""
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                f"{self.api_base}/users/me",
                headers=headers,
                timeout=10.0
            )
            return response.status_code == 200
        except:
            return False

class WordPressAdapter(PlatformAdapter):
    """WordPress publishing adapter"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient()
    
    async def publish_content(
        self,
        connection: PlatformConnection,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish content to WordPress"""
        
        # WordPress API endpoint from connection config
        api_endpoint = connection.api_endpoint or "https://public-api.wordpress.com/rest/v1.1"
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json"
        }
        
        post_data = {
            "title": title,
            "content": content,
            "status": "publish",
            "format": "standard"
        }
        
        # Add categories and tags if provided
        if metadata.get("category"):
            post_data["categories"] = [metadata["category"]]
        
        if metadata.get("tags"):
            post_data["tags"] = metadata["tags"]
        
        try:
            site_id = connection.account_id
            response = await self.http_client.post(
                f"{api_endpoint}/sites/{site_id}/posts/new",
                headers=headers,
                json=post_data,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "post_id": str(result.get("ID")),
                "url": result.get("URL"),
                "platform_response": result,
                "success": True
            }
            
        except httpx.HTTPError as e:
            logger.error(f"WordPress publishing failed: {str(e)}")
            raise Exception(f"WordPress API error: {str(e)}")
    
    async def get_engagement_metrics(
        self,
        connection: PlatformConnection,
        post_id: str
    ) -> Dict[str, Any]:
        """Get WordPress engagement metrics"""
        
        # WordPress.com stats API
        api_endpoint = connection.api_endpoint or "https://public-api.wordpress.com/rest/v1.1"
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            site_id = connection.account_id
            response = await self.http_client.get(
                f"{api_endpoint}/sites/{site_id}/stats/post/{post_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "views": data.get("views", 0),
                    "clicks": data.get("clicks", 0),
                    "likes": data.get("likes", 0),
                    "shares": 0,  # Not available in WordPress stats
                    "comments": data.get("comments", 0),
                    "platform_specific": {
                        "referrers": data.get("referrers", []),
                        "search_terms": data.get("search_terms", [])
                    }
                }
        except:
            pass
        
        return {
            "views": 0,
            "clicks": 0,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "platform_specific": {}
        }
    
    async def validate_connection(self, connection: PlatformConnection) -> bool:
        """Validate WordPress connection"""
        
        api_endpoint = connection.api_endpoint or "https://public-api.wordpress.com/rest/v1.1"
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                f"{api_endpoint}/me",
                headers=headers,
                timeout=10.0
            )
            return response.status_code == 200
        except:
            return False

class CustomAPIAdapter(PlatformAdapter):
    """Custom API publishing adapter"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient()
    
    async def publish_content(
        self,
        connection: PlatformConnection,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Publish content to custom API"""
        
        api_endpoint = connection.api_endpoint
        if not api_endpoint:
            raise Exception("Custom API endpoint not configured")
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json"
        }
        
        # Custom API payload format (configurable)
        connection_config = connection.connection_config or {}
        payload_format = connection_config.get("payload_format", "standard")
        
        if payload_format == "standard":
            post_data = {
                "title": title,
                "content": content,
                "metadata": metadata
            }
        else:
            # Custom payload format
            post_data = connection_config.get("custom_payload", {})
            post_data.update({
                "title": title,
                "content": content
            })
        
        try:
            response = await self.http_client.post(
                api_endpoint,
                headers=headers,
                json=post_data,
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "post_id": result.get("id") or result.get("post_id"),
                "url": result.get("url"),
                "platform_response": result,
                "success": True
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Custom API publishing failed: {str(e)}")
            raise Exception(f"Custom API error: {str(e)}")
    
    async def get_engagement_metrics(
        self,
        connection: PlatformConnection,
        post_id: str
    ) -> Dict[str, Any]:
        """Get custom API engagement metrics"""
        
        # Custom metrics endpoint (if configured)
        connection_config = connection.connection_config or {}
        metrics_endpoint = connection_config.get("metrics_endpoint")
        
        if not metrics_endpoint:
            return {
                "views": 0,
                "clicks": 0,
                "likes": 0,
                "shares": 0,
                "comments": 0,
                "platform_specific": {}
            }
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                f"{metrics_endpoint}/{post_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
        except:
            pass
        
        return {
            "views": 0,
            "clicks": 0,
            "likes": 0,
            "shares": 0,
            "comments": 0,
            "platform_specific": {}
        }
    
    async def validate_connection(self, connection: PlatformConnection) -> bool:
        """Validate custom API connection"""
        
        health_endpoint = connection.connection_config.get("health_endpoint")
        if not health_endpoint:
            health_endpoint = f"{connection.api_endpoint}/health"
        
        headers = {
            "Authorization": f"Bearer {connection.access_token}"
        }
        
        try:
            response = await self.http_client.get(
                health_endpoint,
                headers=headers,
                timeout=10.0
            )
            return response.status_code == 200
        except:
            return False

class PlatformAdapterFactory:
    """Factory for creating platform adapters"""
    
    _adapters = {
        PlatformType.LINKEDIN: LinkedInAdapter,
        PlatformType.MEDIUM: MediumAdapter,
        PlatformType.TWITTER: TwitterAdapter,
        PlatformType.WORDPRESS: WordPressAdapter,
        PlatformType.CUSTOM_API: CustomAPIAdapter
    }
    
    async def get_adapter(self, platform: PlatformType) -> PlatformAdapter:
        """Get adapter for specified platform"""
        
        adapter_class = self._adapters.get(platform)
        if not adapter_class:
            raise Exception(f"Adapter not available for platform: {platform}")
        
        return adapter_class()