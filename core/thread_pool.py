"""
Thread pool manager for running multiple browser instances concurrently
"""
import threading
import queue
import time
from typing import Callable, List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a task to be executed"""
    id: int
    data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    thread_id: int = None
    started_at: float = None
    completed_at: float = None
    
    @property
    def duration(self) -> float:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0


class ThreadPoolManager:
    """
    Manages a pool of worker threads for concurrent task execution.
    Each thread can run a browser instance independently.
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        task_handler: Callable[[Task, int], Any] = None,
        on_task_complete: Callable[[Task], None] = None,
        on_task_error: Callable[[Task, Exception], None] = None,
        on_log: Callable[[str], None] = None,
        delay_between_tasks: float = 2.0
    ):
        self.max_workers = max_workers
        self.task_handler = task_handler
        self.on_task_complete = on_task_complete
        self.on_task_error = on_task_error
        self.on_log = on_log or print
        self.delay_between_tasks = delay_between_tasks
        
        self._task_queue: queue.Queue = queue.Queue()
        self._workers: List[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        self._tasks: Dict[int, Task] = {}
        self._next_task_id = 1
        
    def log(self, message: str, thread_id: int = None):
        """Log a message"""
        prefix = f"[Thread #{thread_id}] " if thread_id else ""
        self.on_log(f"{prefix}{message}")
        
    def add_task(self, data: Dict[str, Any]) -> Task:
        """Add a task to the queue"""
        with self._lock:
            task = Task(id=self._next_task_id, data=data)
            self._tasks[task.id] = task
            self._next_task_id += 1
            
        self._task_queue.put(task)
        self.log(f"📋 Task #{task.id} added to queue")
        return task
        
    def add_tasks(self, data_list: List[Dict[str, Any]]) -> List[Task]:
        """Add multiple tasks"""
        return [self.add_task(data) for data in data_list]
        
    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        return self._tasks.get(task_id)
        
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        return list(self._tasks.values())
        
    def get_pending_count(self) -> int:
        """Get count of pending tasks"""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        
    def get_running_count(self) -> int:
        """Get count of running tasks"""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        
    def get_completed_count(self) -> int:
        """Get count of completed tasks"""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
    
    def get_failed_count(self) -> int:
        """Get count of failed tasks"""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        
    def _worker(self, thread_id: int):
        """Worker thread function"""
        self.log(f"🚀 Worker started", thread_id)
        
        while self._running:
            try:
                # Get task from queue with timeout
                try:
                    task = self._task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                    
                if task is None:  # Poison pill
                    break
                    
                # Execute task
                task.status = TaskStatus.RUNNING
                task.thread_id = thread_id
                task.started_at = time.time()
                
                self.log(f"▶️ Processing Task #{task.id}", thread_id)
                
                try:
                    if self.task_handler:
                        task.result = self.task_handler(task, thread_id)
                        
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = time.time()
                    
                    self.log(f"✅ Task #{task.id} completed in {task.duration:.1f}s", thread_id)
                    
                    if self.on_task_complete:
                        self.on_task_complete(task)
                        
                except Exception as e:
                    task.status = TaskStatus.FAILED
                    task.error = str(e)
                    task.completed_at = time.time()
                    
                    self.log(f"❌ Task #{task.id} failed: {e}", thread_id)
                    
                    if self.on_task_error:
                        self.on_task_error(task, e)
                        
                finally:
                    self._task_queue.task_done()
                    
                # Delay between tasks
                if self._running and self.delay_between_tasks > 0:
                    time.sleep(self.delay_between_tasks)
                    
            except Exception as e:
                self.log(f"⚠️ Worker error: {e}", thread_id)
                
        self.log(f"🛑 Worker stopped", thread_id)
        
    def start(self):
        """Start the thread pool"""
        if self._running:
            return
            
        self._running = True
        self._workers = []
        
        for i in range(self.max_workers):
            thread = threading.Thread(target=self._worker, args=(i + 1,), daemon=True)
            thread.start()
            self._workers.append(thread)
            
        self.log(f"🏃 Thread pool started with {self.max_workers} workers")
        
    def stop(self, wait: bool = True):
        """Stop the thread pool"""
        self._running = False
        
        # Send poison pills
        for _ in self._workers:
            self._task_queue.put(None)
            
        if wait:
            for worker in self._workers:
                worker.join(timeout=5.0)
                
        self._workers = []
        self.log("🛑 Thread pool stopped")
        
    def wait_completion(self, timeout: float = None):
        """Wait for all tasks to complete"""
        self._task_queue.join()
        
    def cancel_pending(self):
        """Cancel all pending tasks"""
        cancelled = 0
        with self._lock:
            for task in self._tasks.values():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    cancelled += 1
                    
        # Clear the queue
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
                self._task_queue.task_done()
            except queue.Empty:
                break
                
        self.log(f"🚫 Cancelled {cancelled} pending tasks")
        return cancelled
        
    def reset(self):
        """Reset the manager state"""
        self.stop()
        self._tasks.clear()
        self._next_task_id = 1
        self._task_queue = queue.Queue()
