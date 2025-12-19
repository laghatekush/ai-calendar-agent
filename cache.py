"""Simple in-memory caching for LLM results"""

from cachetools import TTLCache
import hashlib
import json
from typing import Optional, Dict, Any


class AgentCache:
    """Cache for LLM parsing results"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize cache
        
        Args:
            max_size: Maximum number of items to cache
            ttl_seconds: Time to live in seconds (default 5 minutes)
        """
        # TTLCache automatically removes items after ttl_seconds
        self.cache = TTLCache(maxsize=max_size, ttl=ttl_seconds)
    
    def _generate_key(self, user_input: str) -> str:
        """Generate cache key from user input"""
        # Normalize input (lowercase, strip whitespace)
        normalized = user_input.lower().strip()
        # Create hash for consistent key
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        Get cached result for user input
        
        Args:
            user_input: User's meeting request
            
        Returns:
            Cached meeting details or None if not found
        """
        key = self._generate_key(user_input)
        result = self.cache.get(key)
        
        if result:
            print(f"🎯 Cache HIT for: '{user_input[:50]}...'")
        else:
            print(f"❌ Cache MISS for: '{user_input[:50]}...'")
        
        return result
    
    def set(self, user_input: str, meeting_details: Dict[str, Any]) -> None:
        """
        Store meeting details in cache
        
        Args:
            user_input: User's meeting request
            meeting_details: Parsed meeting details to cache
        """
        key = self._generate_key(user_input)
        self.cache[key] = meeting_details
        print(f"💾 Cached result for: '{user_input[:50]}...'")
    
    def clear(self) -> None:
        """Clear all cached items"""
        self.cache.clear()
        print("🗑️ Cache cleared")
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "size": len(self.cache),
            "max_size": self.cache.maxsize,
            "ttl_seconds": self.cache.ttl
        }