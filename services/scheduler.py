from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
import logging
from typing import Optional, Callable, Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = BackgroundScheduler(
    jobstores={
        'default': MemoryJobStore()
    },
    executors={
        'default': ThreadPoolExecutor(20)
    },
    job_defaults={
        'coalesce': False,
        'max_instances': 3
    }
)

def start_scheduler():
    """Start the scheduler."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started successfully")

def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped successfully")

def add_job(func: Callable, trigger_type: str = 'interval', **kwargs) -> str:
    """
    Add a job to the scheduler.
    
    Args:
        func: Function to execute
        trigger_type: Type of trigger ('interval', 'cron', 'date')
        **kwargs: Trigger-specific arguments
        
    Returns:
        Job ID
    """
    try:
        if trigger_type == 'interval':
            job = scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(**kwargs),
                id=f"{func.__name__}_{datetime.utcnow().timestamp()}",
                replace_existing=True
            )
        elif trigger_type == 'cron':
            job = scheduler.add_job(
                func=func,
                trigger=CronTrigger(**kwargs),
                id=f"{func.__name__}_{datetime.utcnow().timestamp()}",
                replace_existing=True
            )
        elif trigger_type == 'date':
            job = scheduler.add_job(
                func=func,
                trigger=DateTrigger(**kwargs),
                id=f"{func.__name__}_{datetime.utcnow().timestamp()}",
                replace_existing=True
            )
        else:
            raise ValueError(f"Invalid trigger type: {trigger_type}")
        
        logger.info(f"Job added successfully: {job.id}")
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to add job: {str(e)}")
        raise

def remove_job(job_id: str) -> bool:
    """
    Remove a job from the scheduler.
    
    Args:
        job_id: ID of the job to remove
        
    Returns:
        True if job was removed, False otherwise
    """
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Job removed successfully: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to remove job {job_id}: {str(e)}")
        return False

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get job information.
    
    Args:
        job_id: ID of the job
        
    Returns:
        Job information dictionary or None if not found
    """
    try:
        job = scheduler.get_job(job_id)
        if job:
            return {
                'id': job.id,
                'name': job.name,
                'func': job.func.__name__,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {str(e)}")
        return None

def get_jobs() -> list:
    """
    Get all jobs.
    
    Returns:
        List of job information dictionaries
    """
    try:
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'func': job.func.__name__,
                'next_run_time': job.next_run_time,
                'trigger': str(job.trigger)
            })
        return jobs
    except Exception as e:
        logger.error(f"Failed to get jobs: {str(e)}")
        return []

def pause_job(job_id: str) -> bool:
    """
    Pause a job.
    
    Args:
        job_id: ID of the job to pause
        
    Returns:
        True if job was paused, False otherwise
    """
    try:
        scheduler.pause_job(job_id)
        logger.info(f"Job paused successfully: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to pause job {job_id}: {str(e)}")
        return False

def resume_job(job_id: str) -> bool:
    """
    Resume a job.
    
    Args:
        job_id: ID of the job to resume
        
    Returns:
        True if job was resumed, False otherwise
    """
    try:
        scheduler.resume_job(job_id)
        logger.info(f"Job resumed successfully: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to resume job {job_id}: {str(e)}")
        return False

def modify_job(job_id: str, **kwargs) -> bool:
    """
    Modify a job.
    
    Args:
        job_id: ID of the job to modify
        **kwargs: New job parameters
        
    Returns:
        True if job was modified, False otherwise
    """
    try:
        scheduler.modify_job(job_id, **kwargs)
        logger.info(f"Job modified successfully: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to modify job {job_id}: {str(e)}")
        return False

def load_and_start_jobs(mongo_db, db_session):
    """
    Load and start scheduled jobs.
    
    Args:
        mongo_db: MongoDB database instance
        db_session: Database session
    """
    try:
        # Start the scheduler
        start_scheduler()
        
        # Add default jobs here
        # Example: Clean up expired tokens every day at 2 AM
        add_job(
            func=cleanup_expired_tokens,
            trigger_type='cron',
            hour=2,
            minute=0,
            args=[db_session]
        )
        
        # Example: Process scheduled posts every 5 minutes
        add_job(
            func=process_scheduled_posts,
            trigger_type='interval',
            minutes=5,
            args=[mongo_db, db_session]
        )
        
        logger.info("Default jobs loaded and started successfully")
        
    except Exception as e:
        logger.error(f"Failed to load and start jobs: {str(e)}")
        raise

def cleanup_expired_tokens(db_session):
    """Clean up expired tokens from the database."""
    try:
        from models.models import ProdigalEntity
        from datetime import datetime
        
        # Clean up expired email verification tokens
        db_session.query(ProdigalEntity).filter(
            ProdigalEntity.email_verification_token_expiry < datetime.utcnow()
        ).update({
            'email_verification_token': None,
            'email_verification_token_expiry': None
        })
        
        # Clean up expired reset tokens
        db_session.query(ProdigalEntity).filter(
            ProdigalEntity.reset_token_expiry < datetime.utcnow()
        ).update({
            'reset_token': None,
            'reset_token_expiry': None
        })
        
        db_session.commit()
        logger.info("Expired tokens cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired tokens: {str(e)}")
        db_session.rollback()

def process_scheduled_posts(mongo_db, db_session):
    """Process scheduled posts from MongoDB."""
    try:
        from models.mongo_models import Post
        from datetime import datetime
        
        # Get posts that are scheduled for now or in the past
        current_time = datetime.utcnow()
        
        # This is a placeholder - implement actual post processing logic
        logger.info("Processing scheduled posts...")
        
    except Exception as e:
        logger.error(f"Failed to process scheduled posts: {str(e)}")

# Initialize scheduler when module is imported
if not scheduler.running:
    start_scheduler()
