# Service ID: PYL59
# Service Name: Python automation and task scheduling scripts
# سكريبت أتمتة المهام وجدولة العمليات بـ Python

import os
import sys
import time
import json
import logging
import schedule
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from pathlib import Path
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import psutil
import shutil
import zipfile
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging for automation operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== SECTION 1: Task Management and Scheduling ====================

class TaskStatus(Enum):
    """
    Status of automation tasks
    حالة مهام الأتمتة
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"

class TaskPriority(Enum):
    """
    Priority levels for tasks
    مستويات أولوية المهام
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class TriggerType(Enum):
    """
    Types of task triggers
    أنواع مشغلات المهام
    """
    SCHEDULE = "schedule"
    FILE_CHANGE = "file_change"
    SYSTEM_EVENT = "system_event"
    API_CALL = "api_call"
    MANUAL = "manual"

@dataclass
class AutomationTask:
    """
    Automation task definition
    تعريف مهمة الأتمتة
    """
    task_id: str
    name: str
    description: str
    script_path: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    trigger_type: TriggerType = TriggerType.MANUAL
    schedule_expression: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 300
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None

@dataclass
class TaskExecution:
    """
    Task execution record
    سجل تنفيذ المهمة
    """
    execution_id: str
    task_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.RUNNING
    exit_code: Optional[int] = None
    output: str = ""
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

class TaskScheduler:
    """
    Advanced task scheduler and automation manager
    مجدول المهام ومدير الأتمتة المتقدم
    """
    
    def __init__(self, workspace_path: str = "./automation_workspace"):
        """
        Initialize task scheduler
        تهيئة مجدول المهام
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.workspace_path / "scripts").mkdir(exist_ok=True)
        (self.workspace_path / "logs").mkdir(exist_ok=True)
        (self.workspace_path / "configs").mkdir(exist_ok=True)
        
        self.tasks: Dict[str, AutomationTask] = {}
        self.executions: Dict[str, TaskExecution] = {}
        self.running_tasks: Dict[str, subprocess.Popen] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.is_running = False
        
        logger.info(f"Task scheduler initialized with workspace: {workspace_path}")
    
    def add_task(self, task: AutomationTask) -> bool:
        """
        Add new automation task
        إضافة مهمة أتمتة جديدة
        """
        try:
            # Validate script path
            script_path = Path(task.script_path)
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {task.script_path}")
            
            # Set next run time if scheduled
            if task.trigger_type == TriggerType.SCHEDULE and task.schedule_expression:
                task.next_run = self._calculate_next_run(task.schedule_expression)
            
            self.tasks[task.task_id] = task
            logger.info(f"Task added: {task.name} ({task.task_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add task {task.task_id}: {str(e)}")
            return False
    
    def execute_task(self, task_id: str, force: bool = False) -> Optional[str]:
        """
        Execute automation task
        تنفيذ مهمة الأتمتة
        """
        if task_id not in self.tasks:
            logger.error(f"Task not found: {task_id}")
            return None
        
        task = self.tasks[task_id]
        
        # Check if task is already running
        if task_id in self.running_tasks and not force:
            logger.warning(f"Task already running: {task_id}")
            return None
        
        # Create execution record
        execution_id = f"{task_id}_{int(time.time())}"
        execution = TaskExecution(
            execution_id=execution_id,
            task_id=task_id,
            started_at=datetime.utcnow()
        )
        
        self.executions[execution_id] = execution
        
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.last_run = datetime.utcnow()
            task.run_count += 1
            
            # Prepare command
            cmd = [sys.executable, task.script_path]
            
            # Add parameters as command line arguments
            for key, value in task.parameters.items():
                cmd.extend([f"--{key}", str(value)])
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.workspace_path
            )
            
            self.running_tasks[task_id] = process
            
            # Monitor execution in separate thread
            monitor_thread = threading.Thread(
                target=self._monitor_task_execution,
                args=(task_id, execution_id, process)
            )
            monitor_thread.start()
            
            logger.info(f"Task started: {task.name} ({execution_id})")
            return execution_id
            
        except Exception as e:
            # Update execution record
            execution.status = TaskStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            
            # Update task
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            task.last_error = str(e)
            
            logger.error(f"Failed to start task {task_id}: {str(e)}")
            return None
    
    def _monitor_task_execution(self, task_id: str, execution_id: str, 
                              process: subprocess.Popen) -> None:
        """
        Monitor task execution in background
        مراقبة تنفيذ المهمة في الخلفية
        """
        task = self.tasks[task_id]
        execution = self.executions[execution_id]
        
        try:
            # Wait for process completion with timeout
            stdout, stderr = process.communicate(timeout=task.timeout_seconds)
            
            # Update execution record
            execution.completed_at = datetime.utcnow()
            execution.exit_code = process.returncode
            execution.output = stdout
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            
            # Update task status
            if process.returncode == 0:
                execution.status = TaskStatus.COMPLETED
                task.status = TaskStatus.COMPLETED
                task.success_count += 1
                task.last_error = None
            else:
                execution.status = TaskStatus.FAILED
                task.status = TaskStatus.FAILED
                task.failure_count += 1
                task.last_error = stderr
                execution.error_message = stderr
            
            # Schedule next run if applicable
            if task.trigger_type == TriggerType.SCHEDULE and task.schedule_expression:
                task.next_run = self._calculate_next_run(task.schedule_expression)
            
            # Clean up
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            logger.info(
                f"Task completed: {task.name} ({execution_id}) - "
                f"Status: {execution.status.value}, Duration: {execution.duration_seconds:.2f}s"
            )
            
        except subprocess.TimeoutExpired:
            # Handle timeout
            process.kill()
            execution.completed_at = datetime.utcnow()
            execution.status = TaskStatus.FAILED
            execution.error_message = f"Task timed out after {task.timeout_seconds} seconds"
            
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            task.last_error = execution.error_message
            
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            
            logger.error(f"Task timed out: {task.name} ({execution_id})")
    
    def start_scheduler(self) -> None:
        """
        Start the task scheduler
        بدء مجدول المهام
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Task scheduler started")
    
    def stop_scheduler(self) -> None:
        """
        Stop the task scheduler
        إيقاف مجدول المهام
        """
        self.is_running = False
        
        # Cancel all running tasks
        for task_id in list(self.running_tasks.keys()):
            self.cancel_task(task_id)
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Task scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """
        Main scheduler loop
        حلقة المجدول الرئيسية
        """
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Check for scheduled tasks
                for task in self.tasks.values():
                    if (task.trigger_type == TriggerType.SCHEDULE and 
                        task.next_run and 
                        current_time >= task.next_run and
                        task.task_id not in self.running_tasks):
                        
                        self.execute_task(task.task_id)
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {str(e)}")
                time.sleep(30)  # Wait longer on error
    
    def _calculate_next_run(self, schedule_expression: str) -> datetime:
        """
        Calculate next run time based on schedule expression
        حساب وقت التشغيل التالي بناءً على تعبير الجدولة
        """
        try:
            parts = schedule_expression.lower().split()
            if len(parts) >= 3 and parts[0] == "every":
                interval = int(parts[1])
                unit = parts[2].rstrip('s')  # Remove plural 's'
                
                if unit == "minute":
                    return datetime.utcnow() + timedelta(minutes=interval)
                elif unit == "hour":
                    return datetime.utcnow() + timedelta(hours=interval)
                elif unit == "day":
                    return datetime.utcnow() + timedelta(days=interval)
            
            # Default to 1 hour if parsing fails
            return datetime.utcnow() + timedelta(hours=1)
            
        except Exception as e:
            logger.error(f"Failed to parse schedule expression '{schedule_expression}': {str(e)}")
            return datetime.utcnow() + timedelta(hours=1)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel running task
        إلغاء المهمة قيد التشغيل
        """
        try:
            if task_id in self.running_tasks:
                process = self.running_tasks[task_id]
                process.terminate()
                
                # Wait for graceful termination
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                # Update task status
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.CANCELLED
                
                del self.running_tasks[task_id]
                logger.info(f"Task cancelled: {task_id}")
                return True
            else:
                logger.warning(f"Task not running: {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {str(e)}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed task status
        الحصول على حالة المهمة المفصلة
        """
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        
        return {
            'task_id': task.task_id,
            'name': task.name,
            'status': task.status.value,
            'priority': task.priority.value,
            'trigger_type': task.trigger_type.value,
            'schedule_expression': task.schedule_expression,
            'last_run': task.last_run.isoformat() if task.last_run else None,
            'next_run': task.next_run.isoformat() if task.next_run else None,
            'run_count': task.run_count,
            'success_count': task.success_count,
            'failure_count': task.failure_count,
            'success_rate': (task.success_count / task.run_count * 100) if task.run_count > 0 else 0,
            'last_error': task.last_error,
            'is_running': task_id in self.running_tasks
        }

# ==================== SECTION 2: File System Automation ====================

class FileOperation(Enum):
    """
    File system operations
    عمليات نظام الملفات
    """
    COPY = "copy"
    MOVE = "move"
    DELETE = "delete"
    COMPRESS = "compress"
    EXTRACT = "extract"
    SYNC = "sync"

class FileWatcherHandler(FileSystemEventHandler):
    """
    File system event handler for automation
    معالج أحداث نظام الملفات للأتمتة
    """
    
    def __init__(self, automation_manager):
        self.automation_manager = automation_manager
        super().__init__()
    
    def on_modified(self, event):
        if not event.is_directory:
            self.automation_manager.handle_file_event('modified', event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self.automation_manager.handle_file_event('created', event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self.automation_manager.handle_file_event('deleted', event.src_path)

class FileAutomationManager:
    """
    File system automation and monitoring
    أتمتة ومراقبة نظام الملفات
    """
    
    def __init__(self, workspace_path: str = "./file_automation"):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        self.watched_directories: Dict[str, Observer] = {}
        self.file_rules: List[Dict[str, Any]] = []
        self.operation_history: List[Dict[str, Any]] = []
        
        logger.info(f"File automation manager initialized: {workspace_path}")
    
    def add_watch_directory(self, directory_path: str, recursive: bool = True) -> bool:
        """
        Add directory to file system monitoring
        إضافة دليل لمراقبة نظام الملفات
        """
        try:
            directory_path = Path(directory_path).resolve()
            
            if not directory_path.exists():
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            if str(directory_path) in self.watched_directories:
                logger.warning(f"Directory already being watched: {directory_path}")
                return False
            
            # Create observer
            observer = Observer()
            handler = FileWatcherHandler(self)
            observer.schedule(handler, str(directory_path), recursive=recursive)
            observer.start()
            
            self.watched_directories[str(directory_path)] = observer
            
            logger.info(f"Started watching directory: {directory_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add watch directory {directory_path}: {str(e)}")
            return False
    
    def add_file_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Add file automation rule
        إضافة قاعدة أتمتة الملفات
        """
        try:
            # Validate rule structure
            required_fields = ['name', 'trigger', 'action', 'conditions']
            for field in required_fields:
                if field not in rule:
                    raise ValueError(f"Missing required field: {field}")
            
            rule['created_at'] = datetime.utcnow().isoformat()
            rule['rule_id'] = hashlib.md5(
                f"{rule['name']}_{rule['created_at']}".encode()
            ).hexdigest()[:8]
            
            self.file_rules.append(rule)
            
            logger.info(f"File rule added: {rule['name']} ({rule['rule_id']})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add file rule: {str(e)}")
            return False
    
    def handle_file_event(self, event_type: str, file_path: str) -> None:
        """
        Handle file system events
        معالجة أحداث نظام الملفات
        """
        try:
            file_path = Path(file_path)
            
            # Check each rule
            for rule in self.file_rules:
                if self._matches_rule(rule, event_type, file_path):
                    self._execute_file_action(rule, file_path)
            
        except Exception as e:
            logger.error(f"Error handling file event: {str(e)}")
    
    def _matches_rule(self, rule: Dict[str, Any], event_type: str, 
                     file_path: Path) -> bool:
        """
        Check if file event matches rule conditions
        فحص ما إذا كان حدث الملف يطابق شروط القاعدة
        """
        try:
            # Check trigger type
            if rule['trigger'] != event_type:
                return False
            
            conditions = rule['conditions']
            
            # Check file extension
            if 'extensions' in conditions:
                extensions = conditions['extensions']
                if file_path.suffix.lower() not in [ext.lower() for ext in extensions]:
                    return False
            
            # Check file name pattern
            if 'name_pattern' in conditions:
                import re
                pattern = conditions['name_pattern']
                if not re.match(pattern, file_path.name):
                    return False
            
            # Check file size
            if 'min_size' in conditions or 'max_size' in conditions:
                try:
                    file_size = file_path.stat().st_size
                    if 'min_size' in conditions and file_size < conditions['min_size']:
                        return False
                    if 'max_size' in conditions and file_size > conditions['max_size']:
                        return False
                except:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error matching rule: {str(e)}")
            return False
    
    def _execute_file_action(self, rule: Dict[str, Any], file_path: Path) -> None:
        """
        Execute file automation action
        تنفيذ إجراء أتمتة الملف
        """
        try:
            action = rule['action']
            action_type = action['type']
            
            operation_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'rule_id': rule['rule_id'],
                'rule_name': rule['name'],
                'action_type': action_type,
                'source_path': str(file_path),
                'success': False,
                'error_message': None
            }
            
            if action_type == FileOperation.COPY.value:
                destination = Path(action['destination'])
                destination.mkdir(parents=True, exist_ok=True)
                dest_file = destination / file_path.name
                shutil.copy2(file_path, dest_file)
                operation_record['destination_path'] = str(dest_file)
                
            elif action_type == FileOperation.MOVE.value:
                destination = Path(action['destination'])
                destination.mkdir(parents=True, exist_ok=True)
                dest_file = destination / file_path.name
                shutil.move(file_path, dest_file)
                operation_record['destination_path'] = str(dest_file)
                
            elif action_type == FileOperation.DELETE.value:
                file_path.unlink()
                
            elif action_type == FileOperation.COMPRESS.value:
                archive_path = Path(action['archive_path'])
                archive_path.parent.mkdir(parents=True, exist_ok=True)
                
                with zipfile.ZipFile(archive_path, 'a') as zip_file:
                    zip_file.write(file_path, file_path.name)
                operation_record['destination_path'] = str(archive_path)
            
            operation_record['success'] = True
            self.operation_history.append(operation_record)
            
            logger.info(f"File operation completed: {action_type} on {file_path.name}")
            
        except Exception as e:
            operation_record['error_message'] = str(e)
            self.operation_history.append(operation_record)
            logger.error(f"File operation failed: {str(e)}")

# ==================== SECTION 3: System Monitoring and Alerts ====================

class SystemMonitor:
    """
    System resource monitoring and alerting
    مراقبة موارد النظام والتنبيهات
    """
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_percent': 90.0,
            'network_mbps': 100.0
        }
        self.alert_callbacks: List[Callable] = []
        self.monitoring_history: List[Dict[str, Any]] = []
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Add callback function for alerts
        إضافة دالة استدعاء للتنبيهات
        """
        self.alert_callbacks.append(callback)
    
    def set_threshold(self, metric: str, threshold: float) -> None:
        """
        Set alert threshold for metric
        تعيين عتبة التنبيه للمقياس
        """
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = threshold
            logger.info(f"Threshold set: {metric} = {threshold}")
    
    def start_monitoring(self) -> None:
        """
        Start system monitoring
        بدء مراقبة النظام
        """
        if self.monitoring:
            logger.warning("System monitoring already running")
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("System monitoring started")
    
    def stop_monitoring(self) -> None:
        """
        Stop system monitoring
        إيقاف مراقبة النظام
        """
        self.monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop
        حلقة المراقبة الرئيسية
        """
        while self.monitoring:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                
                # Check thresholds and trigger alerts
                self._check_thresholds(metrics)
                
                # Store metrics history
                self.monitoring_history.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'metrics': metrics
                })
                
                # Keep only last 1000 records
                if len(self.monitoring_history) > 1000:
                    self.monitoring_history = self.monitoring_history[-1000:]
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}")
                time.sleep(self.check_interval)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collect current system metrics
        جمع مقاييس النظام الحالية
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network usage
            network = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_total_gb': memory.total / (1024**3),
                'memory_used_gb': memory.used / (1024**3),
                'disk_percent': disk_percent,
                'disk_total_gb': disk.total / (1024**3),
                'disk_used_gb': disk.used / (1024**3),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'process_count': process_count,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
            return {}
    
    def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """
        Check metrics against thresholds and trigger alerts
        فحص المقاييس مقابل العتبات وتشغيل التنبيهات
        """
        try:
            alerts = []
            
            for metric, threshold in self.alert_thresholds.items():
                if metric in metrics and metrics[metric] > threshold:
                    alert = {
                        'metric': metric,
                        'current_value': metrics[metric],
                        'threshold': threshold,
                        'severity': self._calculate_severity(metrics[metric], threshold),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    alerts.append(alert)
            
            # Trigger alert callbacks
            for alert in alerts:
                for callback in self.alert_callbacks:
                    try:
                        callback(alert['metric'], alert)
                    except Exception as e:
                        logger.error(f"Alert callback error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error checking thresholds: {str(e)}")
    
    def _calculate_severity(self, current_value: float, threshold: float) -> str:
        """
        Calculate alert severity based on how much threshold is exceeded
        حساب شدة التنبيه بناءً على مقدار تجاوز العتبة
        """
        ratio = current_value / threshold
        
        if ratio >= 1.5:
            return "critical"
        elif ratio >= 1.2:
            return "high"
        elif ratio >= 1.1:
            return "medium"
        else:
            return "low"
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics
        الحصول على مقاييس النظام الحالية
        """
        return self._collect_system_metrics()
    
    def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get metrics history for specified hours
        الحصول على تاريخ المقاييس للساعات المحددة
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        filtered_history = []
        for record in self.monitoring_history:
            record_time = datetime.fromisoformat(record['timestamp'])
            if record_time >= cutoff_time:
                filtered_history.append(record)
        
        return filtered_history

# ==================== SECTION 4: Notification and Communication ====================

class NotificationManager:
    """
    Notification and communication management
    إدارة الإشعارات والاتصالات
    """
    
    def __init__(self):
        self.email_config: Optional[Dict[str, Any]] = None
        self.webhook_urls: List[str] = []
        self.notification_history: List[Dict[str, Any]] = []
    
    def configure_email(self, smtp_server: str, smtp_port: int, 
                       username: str, password: str, 
                       from_email: str) -> None:
        """
        Configure email notifications
        تكوين إشعارات البريد الإلكتروني
        """
        self.email_config = {
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'from_email': from_email
        }
        logger.info("Email configuration updated")
    
    def add_webhook_url(self, url: str) -> None:
        """
        Add webhook URL for notifications
        إضافة رابط webhook للإشعارات
        """
        if url not in self.webhook_urls:
            self.webhook_urls.append(url)
            logger.info(f"Webhook URL added: {url}")
    
    def send_email_notification(self, to_emails: List[str], subject: str, 
                              message: str, html_message: str = None) -> bool:
        """
        Send email notification
        إرسال إشعار بريد إلكتروني
        """
        if not self.email_config:
            logger.error("Email not configured")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config['from_email']
            msg['To'] = ', '.join(to_emails)
            
            # Add text part
            text_part = MIMEText(message, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_message:
                html_part = MIMEText(html_message, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], 
                            self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], 
                           self.email_config['password'])
                server.send_message(msg)
            
            # Record notification
            self.notification_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'email',
                'recipients': to_emails,
                'subject': subject,
                'success': True
            })
            
            logger.info(f"Email sent successfully to {len(to_emails)} recipients")
            return True
            
        except Exception as e:
            # Record failed notification
            self.notification_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'email',
                'recipients': to_emails,
                'subject': subject,
                'success': False,
                'error': str(e)
            })
            
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_webhook_notification(self, data: Dict[str, Any]) -> int:
        """
        Send webhook notifications
        إرسال إشعارات webhook
        """
        success_count = 0
        
        for webhook_url in self.webhook_urls:
            try:
                response = requests.post(
                    webhook_url,
                    json=data,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    success_count += 1
                    logger.info(f"Webhook notification sent successfully: {webhook_url}")
                else:
                    logger.warning(f"Webhook notification failed: {webhook_url} - {response.status_code}")
                
            except Exception as e:
                logger.error(f"Webhook notification error: {webhook_url} - {str(e)}")
        
        # Record notification
        self.notification_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'webhook',
            'webhook_count': len(self.webhook_urls),
            'success_count': success_count,
            'data': data
        })
        
        return success_count
    
    def create_alert_message(self, alert_type: str, details: Dict[str, Any]) -> str:
        """
        Create formatted alert message
        إنشاء رسالة تنبيه منسقة
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        if alert_type == 'system_threshold':
            return f"""
SYSTEM ALERT - {details.get('severity', 'UNKNOWN').upper()}

Metric: {details.get('metric', 'Unknown')}
Current Value: {details.get('current_value', 'N/A')}
Threshold: {details.get('threshold', 'N/A')}
Time: {timestamp}

Please check system resources and take appropriate action.
            """.strip()
        
        elif alert_type == 'task_failure':
            return f"""
TASK FAILURE ALERT

Task: {details.get('task_name', 'Unknown')}
Task ID: {details.get('task_id', 'Unknown')}
Error: {details.get('error_message', 'No error message')}
Time: {timestamp}

Please check task configuration and logs.
            """.strip()
        
        else:
            return f"""
AUTOMATION ALERT

Type: {alert_type}
Details: {json.dumps(details, indent=2)}
Time: {timestamp}
            """.strip()

# ==================== SECTION 5: Integration and Orchestration ====================

class AutomationOrchestrator:
    """
    Main orchestration class for all automation components
    فئة التنسيق الرئيسية لجميع مكونات الأتمتة
    """
    
    def __init__(self, workspace_path: str = "./automation_workspace"):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.task_scheduler = TaskScheduler(str(self.workspace_path / "tasks"))
        self.file_manager = FileAutomationManager(str(self.workspace_path / "files"))
        self.system_monitor = SystemMonitor()
        self.notification_manager = NotificationManager()
        
        # Setup system monitoring alerts
        self.system_monitor.add_alert_callback(self._handle_system_alert)
        
        logger.info(f"Automation orchestrator initialized: {workspace_path}")
    
    def start_all_services(self) -> None:
        """
        Start all automation services
        بدء جميع خدمات الأتمتة
        """
        try:
            self.task_scheduler.start_scheduler()
            self.system_monitor.start_monitoring()
            logger.info("All automation services started")
        except Exception as e:
            logger.error(f"Failed to start services: {str(e)}")
    
    def stop_all_services(self) -> None:
        """
        Stop all automation services
        إيقاف جميع خدمات الأتمتة
        """
        try:
            self.task_scheduler.stop_scheduler()
            self.system_monitor.stop_monitoring()
            
            # Stop file watchers
            for observer in self.file_manager.watched_directories.values():
                observer.stop()
                observer.join()
            
            logger.info("All automation services stopped")
        except Exception as e:
            logger.error(f"Failed to stop services: {str(e)}")
    
    def _handle_system_alert(self, metric: str, alert_data: Dict[str, Any]) -> None:
        """
        Handle system monitoring alerts
        معالجة تنبيهات مراقبة النظام
        """
        try:
            # Create alert message
            message = self.notification_manager.create_alert_message(
                'system_threshold', alert_data
            )
            
            # Send webhook notification
            webhook_data = {
                'alert_type': 'system_threshold',
                'metric': metric,
                'severity': alert_data.get('severity', 'unknown'),
                'current_value': alert_data.get('current_value'),
                'threshold': alert_data.get('threshold'),
                'timestamp': alert_data.get('timestamp'),
                'message': message
            }
            
            self.notification_manager.send_webhook_notification(webhook_data)
            
            logger.warning(f"System alert handled: {metric} = {alert_data.get('current_value')}")
            
        except Exception as e:
            logger.error(f"Error handling system alert: {str(e)}")
    
    def create_backup_task(self, source_path: str, backup_path: str, 
                          schedule: str = "every 1 day") -> str:
        """
        Create automated backup task
        إنشاء مهمة النسخ الاحتياطي التلقائي
        """
        task_id = f"backup_{hashlib.md5(source_path.encode()).hexdigest()[:8]}"
        
        # Create backup script
        script_content = f'''
import shutil
import os
from datetime import datetime
from pathlib import Path

source = r"{source_path}"
backup_base = r"{backup_path}"

# Create timestamped backup directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = Path(backup_base) / f"backup_{timestamp}"
backup_dir.mkdir(parents=True, exist_ok=True)

# Perform backup
if os.path.isfile(source):
    shutil.copy2(source, backup_dir)
    print(f"File backed up: {source}")
elif os.path.isdir(source):
    shutil.copytree(source, backup_dir / Path(source).name)
    print(f"Directory backed up: {source}")
else:
    print(f"Source not found: {source}")
    exit(1)

print(f"Backup completed: {backup_dir}")
        '''
        
        # Save script
        script_path = self.workspace_path / "scripts" / f"{task_id}.py"
        script_path.parent.mkdir(exist_ok=True)
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Create task
        task = AutomationTask(
            task_id=task_id,
            name=f"Backup {Path(source_path).name}",
            description=f"Automated backup of {source_path} to {backup_path}",
            script_path=str(script_path),
            trigger_type=TriggerType.SCHEDULE,
            schedule_expression=schedule,
            priority=TaskPriority.MEDIUM
        )
        
        if self.task_scheduler.add_task(task):
            logger.info(f"Backup task created: {task_id}")
            return task_id
        else:
            logger.error(f"Failed to create backup task: {task_id}")
            return ""
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status
        الحصول على حالة النظام الشاملة
        """
        try:
            # Task scheduler status
            total_tasks = len(self.task_scheduler.tasks)
            running_tasks = len(self.task_scheduler.running_tasks)
            
            # File automation status
            watched_dirs = len(self.file_manager.watched_directories)
            file_rules = len(self.file_manager.file_rules)
            
            # System metrics
            current_metrics = self.system_monitor.get_current_metrics()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'task_scheduler': {
                    'running': self.task_scheduler.is_running,
                    'total_tasks': total_tasks,
                    'running_tasks': running_tasks,
                    'idle_tasks': total_tasks - running_tasks
                },
                'file_automation': {
                    'watched_directories': watched_dirs,
                    'active_rules': file_rules,
                    'operations_today': len([
                        op for op in self.file_manager.operation_history
                        if datetime.fromisoformat(op['timestamp']).date() == datetime.utcnow().date()
                    ])
                },
                'system_monitoring': {
                    'active': self.system_monitor.monitoring,
                    'check_interval': self.system_monitor.check_interval,
                    'current_metrics': current_metrics
                },
                'notifications': {
                    'email_configured': self.notification_manager.email_config is not None,
                    'webhook_urls': len(self.notification_manager.webhook_urls),
                    'notifications_today': len([
                        notif for notif in self.notification_manager.notification_history
                        if datetime.fromisoformat(notif['timestamp']).date() == datetime.utcnow().date()
                    ])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {'error': str(e)}
