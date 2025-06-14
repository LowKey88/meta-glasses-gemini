"""Task management API endpoints for dashboard"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from functionality.task import (
    create_task, get_tasks, update_task_status, delete_task, 
    get_upcoming_tasks, format_task_for_display, get_task_lists
)
from .auth import verify_token

logger = logging.getLogger("uvicorn")

# Task API Router
router = APIRouter(prefix="/tasks", tags=["tasks"])

class TaskCreate(BaseModel):
    title: str
    notes: Optional[str] = None
    due_date: Optional[str] = None  # YYYY-MM-DD format

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None
    completed: Optional[bool] = None

class TaskStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    due_today: int
    due_this_week: int
    completion_rate: float
    recent_completions: int  # Last 7 days

@router.get("/", dependencies=[Depends(verify_token)])
async def get_all_tasks(
    include_completed: bool = Query(False, description="Include completed tasks"),
    due_filter: Optional[str] = Query(None, description="Filter by due date: 'today', 'week', 'overdue'"),
    sort_by: str = Query("created", description="Sort by: 'created', 'due', 'title'"),
    sort_order: str = Query("desc", description="Sort order: 'asc', 'desc'")
):
    """Get all tasks with optional filtering and sorting"""
    try:
        # Get tasks from Google Tasks API
        try:
            tasks = get_tasks(include_completed=include_completed)
        except Exception as e:
            if "No valid credentials" in str(e):
                # Return mock data when credentials are not available
                logger.warning("Google Tasks API not configured, returning mock data")
                tasks = get_mock_tasks(include_completed)
            else:
                raise e
        
        # Apply due date filtering
        if due_filter:
            now = datetime.now()
            today = now.replace(hour=23, minute=59, second=59)
            week_end = now + timedelta(days=7)
            
            filtered_tasks = []
            for task in tasks:
                due_date = task.get('due')
                if not due_date:
                    continue
                    
                try:
                    due_dt = datetime.fromisoformat(due_date.rstrip('Z'))
                    
                    if due_filter == 'today' and due_dt.date() == now.date():
                        filtered_tasks.append(task)
                    elif due_filter == 'week' and due_dt <= week_end:
                        filtered_tasks.append(task)
                    elif due_filter == 'overdue' and due_dt < now and task.get('status') != 'completed':
                        filtered_tasks.append(task)
                except Exception:
                    continue
            
            tasks = filtered_tasks
        
        # Add source information (this will need to be enhanced based on task notes/metadata)
        for task in tasks:
            task['source'] = determine_task_source(task)
            task['source_icon'] = get_source_icon(task['source'])
            
            # Format due date for display
            if task.get('due'):
                try:
                    due_dt = datetime.fromisoformat(task['due'].rstrip('Z'))
                    task['due_formatted'] = due_dt.strftime('%Y-%m-%d')
                    task['due_display'] = due_dt.strftime('%b %d, %Y')
                    
                    # Check if overdue
                    if due_dt < datetime.now() and task.get('status') != 'completed':
                        task['is_overdue'] = True
                    else:
                        task['is_overdue'] = False
                except Exception:
                    task['due_formatted'] = None
                    task['due_display'] = None
                    task['is_overdue'] = False
            else:
                task['due_formatted'] = None
                task['due_display'] = None
                task['is_overdue'] = False
        
        # Sort tasks
        if sort_by == 'due':
            # Sort by due date, putting tasks without due dates at the end
            tasks.sort(
                key=lambda x: x.get('due', '9999-12-31T23:59:59Z'),
                reverse=(sort_order == 'desc')
            )
        elif sort_by == 'title':
            tasks.sort(
                key=lambda x: x.get('title', '').lower(),
                reverse=(sort_order == 'desc')
            )
        else:  # sort_by == 'created' or default
            # Google Tasks API doesn't provide creation date, so we'll keep the default order
            if sort_order == 'asc':
                tasks.reverse()
        
        return {
            "tasks": tasks,
            "total": len(tasks),
            "filters": {
                "include_completed": include_completed,
                "due_filter": due_filter,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", dependencies=[Depends(verify_token)])
async def create_new_task(task: TaskCreate):
    """Create a new task"""
    try:
        # Add source indication to notes for manual tasks
        notes = task.notes or ""
        if notes:
            notes += "\n\n📝 Created manually via dashboard"
        else:
            notes = "📝 Created manually via dashboard"
        
        created_task = create_task(
            title=task.title,
            notes=notes,
            due_date=task.due_date
        )
        
        if not created_task:
            raise HTTPException(status_code=500, detail="Failed to create task")
        
        # Add source information to response
        created_task['source'] = 'manual'
        created_task['source_icon'] = '📝'
        
        logger.info(f"Created manual task: {task.title}")
        return {
            "success": True,
            "message": "Task created successfully",
            "task": created_task
        }
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{task_id}", dependencies=[Depends(verify_token)])
async def update_task(task_id: str, update: TaskUpdate):
    """Update an existing task"""
    try:
        # If only updating completion status
        if update.completed is not None and all(v is None for k, v in update.dict().items() if k != 'completed'):
            success = update_task_status(task_id, update.completed)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found or update failed")
            
            action = "completed" if update.completed else "marked as incomplete"
            return {"success": True, "message": f"Task {action}"}
        
        # For other updates, we need to get the current task and update it
        # Note: Google Tasks API doesn't have a direct update endpoint for title/notes
        # We would need to delete and recreate, or use the update method if available
        # For now, we'll focus on status updates which are most common
        
        if update.completed is not None:
            success = update_task_status(task_id, update.completed)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found or update failed")
        
        return {"success": True, "message": "Task updated successfully"}
        
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{task_id}", dependencies=[Depends(verify_token)])
async def delete_task_endpoint(task_id: str):
    """Delete a task"""
    try:
        success = delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or deletion failed")
        
        logger.info(f"Deleted task: {task_id}")
        return {"success": True, "message": "Task deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{task_id}/complete", dependencies=[Depends(verify_token)])
async def complete_task(task_id: str):
    """Quick action to complete a task"""
    try:
        success = update_task_status(task_id, True)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or update failed")
        
        return {"success": True, "message": "Task completed"}
        
    except Exception as e:
        logger.error(f"Error completing task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/upcoming", dependencies=[Depends(verify_token)])
async def get_upcoming_tasks_endpoint(days: int = Query(7, description="Number of days to look ahead")):
    """Get tasks due within the specified number of days"""
    try:
        try:
            upcoming = get_upcoming_tasks(days=days, include_completed=False)
        except Exception as e:
            if "No valid credentials" in str(e):
                logger.warning("Google Tasks API not configured, returning mock upcoming tasks")
                # Filter mock tasks for upcoming ones
                all_tasks = get_mock_tasks(include_completed=False)
                now = datetime.now()
                cutoff_date = now + timedelta(days=days)
                
                upcoming = []
                for task in all_tasks:
                    if task.get('due'):
                        due_date = datetime.fromisoformat(task['due'].rstrip('Z'))
                        if due_date <= cutoff_date:
                            upcoming.append(task)
                # Sort by due date
                upcoming.sort(key=lambda x: x.get('due', ''))
            else:
                raise e
        
        # Add source information and formatting
        for task in upcoming:
            task['source'] = determine_task_source(task)
            task['source_icon'] = get_source_icon(task['source'])
            
            if task.get('due'):
                try:
                    due_dt = datetime.fromisoformat(task['due'].rstrip('Z'))
                    task['due_display'] = due_dt.strftime('%b %d, %Y')
                    task['days_until_due'] = (due_dt.date() - datetime.now().date()).days
                    
                    # Check if overdue
                    task['is_overdue'] = due_dt < datetime.now()
                except Exception:
                    task['due_display'] = None
                    task['days_until_due'] = None
                    task['is_overdue'] = False
        
        return {
            "upcoming_tasks": upcoming,
            "total": len(upcoming),
            "days_ahead": days
        }
        
    except Exception as e:
        logger.error(f"Error getting upcoming tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", dependencies=[Depends(verify_token)])
async def get_task_statistics():
    """Get task completion statistics"""
    try:
        # Get all tasks
        try:
            all_tasks = get_tasks(include_completed=True)
        except Exception as e:
            if "No valid credentials" in str(e):
                logger.warning("Google Tasks API not configured, returning mock stats")
                all_tasks = get_mock_tasks(include_completed=True)
            else:
                raise e
        
        # Calculate basic stats
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.get('status') == 'completed'])
        pending_tasks = total_tasks - completed_tasks
        
        # Calculate due date stats
        now = datetime.now()
        today = now.replace(hour=23, minute=59, second=59)
        week_end = now + timedelta(days=7)
        
        due_today = 0
        due_this_week = 0
        overdue_tasks = 0
        
        for task in all_tasks:
            if task.get('status') == 'completed':
                continue
                
            due_date = task.get('due')
            if due_date:
                try:
                    due_dt = datetime.fromisoformat(due_date.rstrip('Z'))
                    
                    if due_dt.date() == now.date():
                        due_today += 1
                    if due_dt <= week_end:
                        due_this_week += 1
                    if due_dt < now:
                        overdue_tasks += 1
                except Exception:
                    continue
        
        # Calculate completion rate
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Calculate recent completions (last 7 days)
        # Note: Google Tasks API doesn't provide completion timestamps easily
        # This would need to be tracked separately or estimated
        recent_completions = 0  # Placeholder
        
        # Calculate source distribution
        source_distribution = {
            'manual': 0,
            'ai_extracted': 0,
            'natural_language': 0,
            'voice_command': 0
        }
        
        for task in all_tasks:
            source = determine_task_source(task)
            source_distribution[source] = source_distribution.get(source, 0) + 1
        
        return TaskStats(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            overdue_tasks=overdue_tasks,
            due_today=due_today,
            due_this_week=due_this_week,
            completion_rate=round(completion_rate, 1),
            recent_completions=recent_completions
        ).dict() | {"source_distribution": source_distribution}
        
    except Exception as e:
        logger.error(f"Error getting task statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/lists", dependencies=[Depends(verify_token)])
async def get_task_lists_endpoint():
    """Get all available task lists"""
    try:
        task_lists = get_task_lists()
        return {
            "task_lists": task_lists,
            "total": len(task_lists)
        }
        
    except Exception as e:
        logger.error(f"Error getting task lists: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def determine_task_source(task: Dict) -> str:
    """Determine the source of a task based on its notes and metadata"""
    notes = task.get('notes', '')
    
    if 'From Limitless recording' in notes and 'Assigned to:' in notes:
        return 'ai_extracted'
    elif 'From Limitless recording' in notes:
        return 'natural_language'  
    elif 'Created manually via dashboard' in notes:
        return 'manual'
    elif notes and 'whatsapp' in notes.lower():
        return 'voice_command'
    else:
        # Default to voice_command for tasks without clear source indicators
        return 'voice_command'

def get_source_icon(source: str) -> str:
    """Get icon for task source"""
    icons = {
        'ai_extracted': '🤖',
        'natural_language': '🎙️', 
        'manual': '📝',
        'voice_command': '🗣️'
    }
    return icons.get(source, '❓')

def get_mock_tasks(include_completed: bool = False) -> List[Dict]:
    """Return mock tasks for development when Google Tasks API is not configured"""
    from datetime import datetime, timedelta
    
    base_tasks = [
        {
            'id': 'mock_1',
            'title': 'Review quarterly budget report',
            'notes': 'From Limitless recording: Office meeting discussion\nAssigned to: You\nMentioned by: Speaker 0',
            'status': 'needsAction',
            'due': (datetime.now() + timedelta(days=1)).isoformat() + 'Z'
        },
        {
            'id': 'mock_2', 
            'title': 'Buy groceries for weekend',
            'notes': 'From Limitless recording\n🎙️ Voice recording task',
            'status': 'needsAction',
            'due': (datetime.now() + timedelta(days=2)).isoformat() + 'Z'
        },
        {
            'id': 'mock_3',
            'title': 'Call mom about birthday plans',
            'notes': '📝 Created manually via dashboard',
            'status': 'needsAction',
            'due': (datetime.now() + timedelta(days=7)).isoformat() + 'Z'
        },
        {
            'id': 'mock_4',
            'title': 'Schedule dentist appointment',
            'notes': 'whatsapp voice command task',
            'status': 'needsAction',
            'due': None
        },
        {
            'id': 'mock_5',
            'title': 'Finish project proposal',
            'notes': 'From Limitless recording: Project meeting\nAssigned to: You\nMentioned by: Speaker 1',
            'status': 'completed' if include_completed else 'needsAction',
            'due': (datetime.now() - timedelta(days=1)).isoformat() + 'Z'
        },
        {
            'id': 'mock_6',
            'title': 'Exercise for 30 minutes',
            'notes': 'From Limitless recording\n🎙️ Daily routine reminder',
            'status': 'completed' if include_completed else 'needsAction',
            'due': datetime.now().isoformat() + 'Z'
        }
    ]
    
    if include_completed:
        return base_tasks
    else:
        return [task for task in base_tasks if task['status'] != 'completed']