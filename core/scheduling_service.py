import asyncio
import json
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.scheduled_post import ScheduledPost
from core.oauth_service import OAuthService
from providers.linkedin.v1.ops import create_post
from providers.youtube.v1.ops import videos_update
from core.crypto import decrypt_token_blob
import logging

logger = logging.getLogger(__name__)

class SchedulingService:
    def __init__(self, db: Session):
        self.db = db
        self.oauth_service = OAuthService(db)
    
    async def get_posts_ready_to_publish(self) -> List[ScheduledPost]:
        """Get all posts that are scheduled and ready to publish"""
        now = datetime.now(timezone.utc)
        
        posts = self.db.query(ScheduledPost).filter(
            and_(
                ScheduledPost.status == 'scheduled',
                ScheduledPost.scheduled_time <= now
            )
        ).all()
        
        return posts
    
    async def publish_linkedin_post(self, scheduled_post: ScheduledPost) -> bool:
        """Publish a scheduled LinkedIn post"""
        try:
            # Get the LinkedIn connection
            connection = self.oauth_service.get_linkedin_connection(scheduled_post.connection_id)
            if not connection:
                raise Exception("LinkedIn connection not found")
            
            # Decrypt the token
            if hasattr(connection, 'access_token_encrypted') and connection.access_token_encrypted:
                token_data = json.loads(connection.access_token_encrypted)
                token_blob = decrypt_token_blob(
                    token_data['access_token'],
                    token_data['iv'],
                    token_data['ct']
                )
            else:
                # Fallback to old format
                token_blob = decrypt_token_blob(
                    connection.access_token_encrypted,
                    connection.access_token_iv,
                    connection.access_token_ct
                )
            
            # Extract post data from platform_data
            platform_data = json.loads(scheduled_post.platform_data) if scheduled_post.platform_data else {}
            
            # Create the post using LinkedIn API
            post_data = {
                'text': platform_data.get('text', scheduled_post.content or ''),
                'visibility': platform_data.get('visibility', 'PUBLIC'),
                'profile_id': connection.profile_id,
                'media_files': []
            }
            result = create_post(token_blob, post_data)
            
            # Update post status
            scheduled_post.status = 'published'
            scheduled_post.published_at = datetime.now(timezone.utc)
            scheduled_post.platform_data = json.dumps({
                **json.loads(scheduled_post.platform_data or '{}'),
                'linkedin_post_id': result.get('id'),
                'linkedin_urn': result.get('urn')
            })
            
            self.db.commit()
            logger.info(f"Successfully published LinkedIn post {scheduled_post.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish LinkedIn post {scheduled_post.id}: {str(e)}")
            scheduled_post.status = 'failed'
            scheduled_post.error_message = str(e)
            scheduled_post.retry_count += 1
            self.db.commit()
            return False
    
    async def publish_youtube_post(self, scheduled_post: ScheduledPost) -> bool:
        """Publish a scheduled YouTube post (video update, thumbnail, etc.)"""
        try:
            # Get the YouTube connection
            connection = self.oauth_service.get_youtube_connection(scheduled_post.youtube_connection_id)
            if not connection:
                raise Exception("YouTube connection not found")
            
            # Decrypt the token
            if hasattr(connection, 'access_token_encrypted') and connection.access_token_encrypted:
                token_data = json.loads(connection.access_token_encrypted)
                token_blob = decrypt_token_blob(
                    token_data['access_token'],
                    token_data['iv'],
                    token_data['ct']
                )
            else:
                # Fallback to old format
                token_blob = decrypt_token_blob(
                    connection.token_wrapped_ct,
                    connection.token_wrapped_iv,
                    connection.token_fp
                )
            
            # Extract post data from platform_data
            platform_data = json.loads(scheduled_post.platform_data) if scheduled_post.platform_data else {}
            
            if scheduled_post.post_type == 'youtube_video_update':
                # Update video metadata
                video_id = platform_data.get('video_id')
                if not video_id:
                    raise Exception("Video ID not provided for video update")
                

                
                # Call YouTube API
                result = videos_update(
                    token_blob=token_blob,
                    video_id=video_id,
                    title=platform_data.get('title'),
                    description=platform_data.get('description'),
                    tags=platform_data.get('tags'),
                    privacy_status=platform_data.get('privacy_status'),
                    role="VIEWER"
                )
                
                # Update post status
                scheduled_post.status = 'published'
                scheduled_post.published_at = datetime.now(timezone.utc)
                scheduled_post.platform_data = json.dumps({
                    **json.loads(scheduled_post.platform_data or '{}'),
                    'youtube_result': result
                })
                
                self.db.commit()
                logger.info(f"Successfully published YouTube video update {scheduled_post.id}")
                return True
            
            else:
                raise Exception(f"Unsupported YouTube post type: {scheduled_post.post_type}")
                
        except Exception as e:
            logger.error(f"Failed to publish YouTube post {scheduled_post.id}: {str(e)}")
            scheduled_post.status = 'failed'
            scheduled_post.error_message = str(e)
            scheduled_post.retry_count += 1
            self.db.commit()
            return False
    
    async def process_scheduled_posts(self):
        """Main method to process all scheduled posts"""
        try:
            posts = await self.get_posts_ready_to_publish()
            
            for post in posts:
                logger.info(f"Processing scheduled post {post.id} ({post.platform})")
                
                if post.platform == 'linkedin':
                    await self.publish_linkedin_post(post)
                elif post.platform == 'youtube':
                    await self.publish_youtube_post(post)
                else:
                    logger.warning(f"Unknown platform: {post.platform}")
                    post.status = 'failed'
                    post.error_message = f"Unknown platform: {post.platform}"
                    self.db.commit()
                    
        except Exception as e:
            logger.error(f"Error processing scheduled posts: {str(e)}")
    
    async def retry_failed_posts(self):
        """Retry posts that failed but can be retried"""
        try:
            failed_posts = self.db.query(ScheduledPost).filter(
                and_(
                    ScheduledPost.status == 'failed',
                    ScheduledPost.retry_count < ScheduledPost.max_retries
                )
            ).all()
            
            for post in failed_posts:
                logger.info(f"Retrying failed post {post.id}")
                
                # Reset status to scheduled
                post.status = 'scheduled'
                post.error_message = None
                
                # Try to publish again
                if post.platform == 'linkedin':
                    await self.publish_linkedin_post(post)
                elif post.platform == 'youtube':
                    await self.publish_youtube_post(post)
                    
        except Exception as e:
            logger.error(f"Error retrying failed posts: {str(e)}")
    
    def get_user_scheduled_posts(self, user_id: str, brand_id: str, platform: Optional[str] = None) -> List[ScheduledPost]:
        """Get scheduled posts for a specific user and brand"""
        query = self.db.query(ScheduledPost).filter(
            and_(
                ScheduledPost.user_id == user_id,
                ScheduledPost.brand_id == brand_id
            )
        )
        
        if platform:
            query = query.filter(ScheduledPost.platform == platform)
        
        return query.order_by(ScheduledPost.scheduled_time.desc()).all()
    
    def cancel_scheduled_post(self, post_id: str, user_id: str, brand_id: str) -> bool:
        """Cancel a scheduled post"""
        post = self.db.query(ScheduledPost).filter(
            and_(
                ScheduledPost.id == post_id,
                ScheduledPost.user_id == user_id,
                ScheduledPost.brand_id == brand_id,
                ScheduledPost.status == 'scheduled'
            )
        ).first()
        
        if post:
            post.status = 'cancelled'
            self.db.commit()
            return True
        
        return False
