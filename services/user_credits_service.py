#!/usr/bin/env python3
"""
User Credits Service for Content Crew Prodigal
MongoDB-based credit management system
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId
import asyncio

logger = logging.getLogger(__name__)

class UserCreditsService:
    """Service for managing user credits in MongoDB."""
    
    def __init__(self):
        self.mongo_url = os.getenv("MONGODB_URL", "mongodb+srv://ashwini:Ashwini1234@cluster0.lyeisj1.mongodb.net/Dhanur-AI")
        self.database_name = os.getenv("MONGODB_DATABASE", "Dhanur-AI")
        self.collection_name = "user_credits"
        
        try:
            self.client = MongoClient(self.mongo_url)
            self.db: Database = self.client[self.database_name]
            self.collection: Collection = self.db[self.collection_name]
            
            # Create indexes for better performance
            self.collection.create_index("user_id", unique=True)
            self.collection.create_index("created_at")
            self.collection.create_index("updated_at")
            
            logger.info(f"User Credits Service connected to MongoDB")
            
        except Exception as e:
            logger.error(f"User Credits Service connection failed: {str(e)}")
            self.client = None
            self.db = None
            self.collection = None
    
    def is_connected(self) -> bool:
        """Check if MongoDB is connected."""
        try:
            if self.client:
                self.client.admin.command('ping')
                return True
        except Exception:
            pass
        return False
    
    async def initialize_user_credits(self, user_id: str, initial_credits: int = 100) -> Dict[str, Any]:
        """
        Initialize credits for a new user.
        
        Args:
            user_id: User ID
            initial_credits: Initial credit amount (default: 100)
            
        Returns:
            Dictionary with success status and credit info
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            # Check if user already has credits
            existing = self.collection.find_one({"user_id": user_id})
            if existing:
                return {
                    "success": True,
                    "message": "User credits already exist",
                    "user_id": user_id,
                    "credits": existing["credits"],
                    "total_earned": existing["total_earned"],
                    "total_spent": existing["total_spent"]
                }
            
            # Create new user credits document
            credit_doc = {
                "user_id": user_id,
                "credits": initial_credits,
                "total_earned": initial_credits,
                "total_spent": 0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "credit_history": [
                    {
                        "type": "initial_bonus",
                        "amount": initial_credits,
                        "description": f"Welcome bonus - {initial_credits} credits",
                        "timestamp": datetime.now(timezone.utc)
                    }
                ]
            }
            
            result = self.collection.insert_one(credit_doc)
            credit_id = str(result.inserted_id)
            
            logger.info(f"Initialized credits for user {user_id}: {initial_credits} credits")
            
            return {
                "success": True,
                "message": f"User credits initialized with {initial_credits} credits",
                "user_id": user_id,
                "credits": initial_credits,
                "total_earned": initial_credits,
                "total_spent": 0,
                "credit_id": credit_id
            }
            
        except Exception as e:
            logger.error(f"Failed to initialize user credits: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to initialize user credits: {str(e)}"
            }
    
    async def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's current credits.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with user's credit information
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            user_credits = self.collection.find_one({"user_id": user_id})
            
            if not user_credits:
                # Initialize credits if user doesn't exist
                return await self.initialize_user_credits(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "credits": user_credits["credits"],
                "total_earned": user_credits["total_earned"],
                "total_spent": user_credits["total_spent"],
                "created_at": user_credits["created_at"].isoformat(),
                "updated_at": user_credits["updated_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user credits: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get user credits: {str(e)}"
            }
    
    async def add_credits(self, user_id: str, amount: int, reason: str = "bonus") -> Dict[str, Any]:
        """
        Add credits to user's account.
        
        Args:
            user_id: User ID
            amount: Amount of credits to add
            reason: Reason for adding credits
            
        Returns:
            Dictionary with success status and updated credits
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            if amount <= 0:
                return {
                    "success": False,
                    "error": "Credit amount must be positive"
                }
            
            # Update user credits
            result = self.collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        "credits": amount,
                        "total_earned": amount
                    },
                    "$set": {
                        "updated_at": datetime.now(timezone.utc)
                    },
                    "$push": {
                        "credit_history": {
                            "type": "credit_add",
                            "amount": amount,
                            "description": reason,
                            "timestamp": datetime.now(timezone.utc)
                        }
                    }
                }
            )
            
            if result.matched_count == 0:
                # User doesn't exist, initialize credits
                return await self.initialize_user_credits(user_id, amount)
            
            # Get updated credits
            updated_credits = self.collection.find_one({"user_id": user_id})
            
            logger.info(f"Added {amount} credits to user {user_id}. New balance: {updated_credits['credits']}")
            
            return {
                "success": True,
                "message": f"Added {amount} credits to user account",
                "user_id": user_id,
                "credits_added": amount,
                "new_balance": updated_credits["credits"],
                "total_earned": updated_credits["total_earned"],
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Failed to add credits: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to add credits: {str(e)}"
            }
    
    async def deduct_credits(self, user_id: str, amount: int, reason: str = "usage") -> Dict[str, Any]:
        """
        Deduct credits from user's account.
        
        Args:
            user_id: User ID
            amount: Amount of credits to deduct
            reason: Reason for deducting credits
            
        Returns:
            Dictionary with success status and updated credits
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            if amount <= 0:
                return {
                    "success": False,
                    "error": "Deduction amount must be positive"
                }
            
            # Get current credits
            user_credits = self.collection.find_one({"user_id": user_id})
            
            if not user_credits:
                return {
                    "success": False,
                    "error": "User credits not found. Please initialize credits first."
                }
            
            if user_credits["credits"] < amount:
                return {
                    "success": False,
                    "error": "Insufficient credits",
                    "current_credits": user_credits["credits"],
                    "required_credits": amount,
                    "shortfall": amount - user_credits["credits"]
                }
            
            # Update user credits
            result = self.collection.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        "credits": -amount,
                        "total_spent": amount
                    },
                    "$set": {
                        "updated_at": datetime.now(timezone.utc)
                    },
                    "$push": {
                        "credit_history": {
                            "type": "credit_deduct",
                            "amount": amount,
                            "description": reason,
                            "timestamp": datetime.now(timezone.utc)
                        }
                    }
                }
            )
            
            # Get updated credits
            updated_credits = self.collection.find_one({"user_id": user_id})
            
            logger.info(f"Deducted {amount} credits from user {user_id}. New balance: {updated_credits['credits']}")
            
            return {
                "success": True,
                "message": f"Deducted {amount} credits from user account",
                "user_id": user_id,
                "credits_deducted": amount,
                "new_balance": updated_credits["credits"],
                "total_spent": updated_credits["total_spent"],
                "reason": reason
            }
            
        except Exception as e:
            logger.error(f"Failed to deduct credits: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to deduct credits: {str(e)}"
            }
    
    async def get_credit_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Get user's credit history.
        
        Args:
            user_id: User ID
            limit: Maximum number of history entries
            
        Returns:
            Dictionary with credit history
        """
        try:
            if not self.is_connected():
                return {
                    "success": False,
                    "error": "MongoDB connection not available"
                }
            
            user_credits = self.collection.find_one({"user_id": user_id})
            
            if not user_credits:
                return {
                    "success": False,
                    "error": "User credits not found"
                }
            
            history = user_credits.get("credit_history", [])
            # Sort by timestamp descending and limit
            history = sorted(history, key=lambda x: x["timestamp"], reverse=True)[:limit]
            
            return {
                "success": True,
                "user_id": user_id,
                "current_credits": user_credits["credits"],
                "total_earned": user_credits["total_earned"],
                "total_spent": user_credits["total_spent"],
                "history": history,
                "history_count": len(history)
            }
            
        except Exception as e:
            logger.error(f"Failed to get credit history: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get credit history: {str(e)}"
            }
    
    def close_connection(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("User Credits Service connection closed")

# Create singleton instance
user_credits_service = UserCreditsService()

