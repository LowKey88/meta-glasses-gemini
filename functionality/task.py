import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from utils.google_api import get_tasks_service

# Configure logging
logger = logging.getLogger("uvicorn")

def get_task_lists() -> List[Dict]:
    """Get all task lists for the user."""
    logger.info("Fetching task lists")
    service = get_tasks_service()
    if not service:
        logger.error("No valid credentials for Tasks API")
        raise Exception("No valid credentials")
    
    try:
        results = service.tasklists().list().execute()
        task_lists = results.get('items', [])
        logger.info(f"Found {len(task_lists)} task list(s)")
        return task_lists
    except Exception as e:
        logger.error(f"Error getting task lists: {str(e)}")
        return []

def get_default_task_list() -> Optional[str]:
    """Get the ID of the default task list (usually '@default')."""
    logger.info("Getting default task list")
    task_lists = get_task_lists()
    if not task_lists:
        logger.warning("No task lists found")
        return None
    
    # Try to find the default list first
    default_list = next((lst for lst in task_lists if lst['title'] == 'My Tasks'), None)
    if default_list:
        logger.info(f"Using default list: {default_list['title']}")
        return default_list['id']
    
    # If no default list found, return the first list's ID
    logger.info(f"Using first available list: {task_lists[0]['title']}")
    return task_lists[0]['id']

def create_task(title: str, notes: Optional[str] = None, due_date: Optional[str] = None, list_id: Optional[str] = None) -> Optional[Dict]:
    """
    Create a new task.
    
    Args:
        title: Task title
        notes: Optional notes/description
        due_date: Optional due date in 'YYYY-MM-DD' format
        list_id: Optional task list ID (uses default if not provided)
    
    Returns:
        Created task dict if successful, None if failed
    """
    logger.info(f"Creating new task: {title}")
    service = get_tasks_service()
    if not service:
        logger.error("No valid credentials for Tasks API")
        raise Exception("No valid credentials")
    
    try:
        # Get default list ID if none provided
        if not list_id:
            list_id = get_default_task_list()
            if not list_id:
                logger.error("No task list available")
                raise Exception("No task list available")
            logger.info(f"Using task list ID: {list_id}")
        
        task = {
            'title': title,
            'notes': notes if notes else '',
            'status': 'needsAction'
        }
        
        # Add due date if provided
        if due_date:
            logger.info(f"Setting due date: {due_date}")
            # Convert YYYY-MM-DD to RFC 3339 timestamp
            due_datetime = datetime.strptime(due_date, '%Y-%m-%d')
            # Set due time to end of day
            due_datetime = due_datetime.replace(hour=23, minute=59, second=59)
            task['due'] = due_datetime.isoformat() + 'Z'
        
        result = service.tasks().insert(tasklist=list_id, body=task).execute()
        logger.info(f"Task created successfully with ID: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return None

def get_tasks(list_id: Optional[str] = None, include_completed: bool = False) -> List[Dict]:
    """
    Get tasks from a specified list or default list.
    
    Args:
        list_id: Optional task list ID (uses default if not provided)
        include_completed: Whether to include completed tasks
    
    Returns:
        List of task dictionaries
    """
    logger.info(f"Fetching tasks (include_completed={include_completed})")
    service = get_tasks_service()
    if not service:
        logger.error("No valid credentials for Tasks API")
        raise Exception("No valid credentials")
    
    try:
        if not list_id:
            list_id = get_default_task_list()
            if not list_id:
                logger.warning("No task list available")
                return []
            logger.info(f"Using task list ID: {list_id}")
        
        # Get all tasks
        results = service.tasks().list(
            tasklist=list_id,
            showCompleted=include_completed,
            showHidden=False
        ).execute()
        
        tasks = results.get('items', [])
        logger.info(f"Found {len(tasks)} tasks")
        
        # If not including completed tasks, filter them out
        if not include_completed:
            tasks = [task for task in tasks if task.get('status') != 'completed']
            logger.info(f"Filtered to {len(tasks)} incomplete tasks")
        
        return tasks
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        return []

def update_task_status(task_id: str, completed: bool, list_id: Optional[str] = None) -> bool:
    """
    Update task completion status.
    
    Args:
        task_id: ID of the task to update
        completed: True to mark as completed, False for incomplete
        list_id: Optional task list ID (uses default if not provided)
    
    Returns:
        True if successful, False if failed
    """
    logger.info(f"Updating task {task_id} status to {'completed' if completed else 'incomplete'}")
    service = get_tasks_service()
    if not service:
        logger.error("No valid credentials for Tasks API")
        raise Exception("No valid credentials")
    
    try:
        if not list_id:
            list_id = get_default_task_list()
            if not list_id:
                logger.error("No task list available")
                return False
            logger.info(f"Using task list ID: {list_id}")
        
        # Get current task to preserve other fields
        task = service.tasks().get(tasklist=list_id, task=task_id).execute()
        logger.info(f"Retrieved task: {task.get('title')}")
        
        # Update status
        task['status'] = 'completed' if completed else 'needsAction'
        if completed:
            task['completed'] = datetime.utcnow().isoformat() + 'Z'
            logger.info(f"Setting completion timestamp: {task['completed']}")
        elif 'completed' in task:
            del task['completed']
            logger.info("Removing completion timestamp")
        
        service.tasks().update(
            tasklist=list_id,
            task=task_id,
            body=task
        ).execute()
        logger.info("Task status updated successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating task status: {str(e)}")
        return False

def delete_task(task_id: str, list_id: Optional[str] = None) -> bool:
    """
    Delete a task.
    
    Args:
        task_id: ID of the task to delete
        list_id: Optional task list ID (uses default if not provided)
    
    Returns:
        True if successful, False if failed
    """
    logger.info(f"Deleting task {task_id}")
    service = get_tasks_service()
    if not service:
        logger.error("No valid credentials for Tasks API")
        raise Exception("No valid credentials")
    
    try:
        if not list_id:
            list_id = get_default_task_list()
            if not list_id:
                logger.error("No task list available")
                return False
            logger.info(f"Using task list ID: {list_id}")
        
        service.tasks().delete(tasklist=list_id, task=task_id).execute()
        logger.info("Task deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting task: {str(e)}")
        return False

def get_upcoming_tasks(days: int = 7, include_completed: bool = False) -> List[Dict]:
    """
    Get tasks due within the specified number of days.
    
    Args:
        days: Number of days to look ahead (default 7)
        include_completed: Whether to include completed tasks
    
    Returns:
        List of task dictionaries
    """
    logger.info(f"Getting upcoming tasks for next {days} days (include_completed={include_completed})")
    tasks = get_tasks(include_completed=include_completed)
    if not tasks:
        logger.info("No tasks found")
        return []
    
    # Calculate the cutoff date
    cutoff_date = datetime.utcnow() + timedelta(days=days)
    logger.info(f"Cutoff date: {cutoff_date.isoformat()}")
    
    # Filter tasks by due date
    upcoming_tasks = []
    for task in tasks:
        if 'due' in task:
            due_date = datetime.fromisoformat(task['due'].rstrip('Z'))
            if due_date <= cutoff_date:
                upcoming_tasks.append(task)
                logger.debug(f"Added upcoming task: {task.get('title')}")
    
    # Sort by due date
    upcoming_tasks.sort(key=lambda x: x.get('due', ''))
    logger.info(f"Found {len(upcoming_tasks)} upcoming tasks")
    return upcoming_tasks

def format_task_for_display(task: Dict) -> str:
    """Format a task into a readable string optimized for text-to-speech."""
    logger.debug(f"Formatting task for display: {task.get('title')}")
    title = task.get('title', 'Untitled task')
    
    # Format due date if present
    due_str = ""
    if 'due' in task:
        due_date = datetime.fromisoformat(task['due'].rstrip('Z'))
        due_str = f", due {due_date.strftime('%Y-%m-%d')}"
        logger.debug(f"Task due date: {due_str}")
    
    # Add completion status at the end if completed
    status_str = " [Done]" if task.get('status') == 'completed' else ""
    
    # Add notes if present
    notes = f"\n  Notes: {task['notes']}" if task.get('notes') else ""
    if notes:
        logger.debug("Task has additional notes")
    
    formatted_task = f"- {title}{due_str}{status_str}{notes}"
    logger.debug(f"Formatted task: {formatted_task}")
    return formatted_task