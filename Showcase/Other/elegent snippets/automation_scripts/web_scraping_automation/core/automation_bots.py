# Service ID: ATS78
# Service Name: Task automation bots programming
# برمجة بوتات لأتمتة المهام

import asyncio
import time
import logging
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import schedule
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty
import subprocess
import psutil
import hashlib

# Configure logging for automation bots
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation_bots.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== SECTION 1: Bot Framework and Core Classes ====================

class BotStatus(Enum):
    """
    Bot execution status
    حالة تنفيذ البوت
    """
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"

class TaskPriority(Enum):
    """
    Task priority levels
    مستويات أولوية المهام
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class BotType(Enum):
    """
    Types of automation bots
    أنواع بوتات الأتمتة
    """
    WEB_AUTOMATION = "web_automation"
    FILE_PROCESSOR = "file_processor"
    DATA_COLLECTOR = "data_collector"
    NOTIFICATION_BOT = "notification_bot"
    SYSTEM_MONITOR = "system_monitor"
    SCHEDULER_BOT = "scheduler_bot"

@dataclass
class BotTask:
    """
    Individual bot task definition
    تعريف مهمة البوت الفردية
    """
    task_id: str
    name: str
    description: str
    bot_type: BotType
    priority: TaskPriority = TaskPriority.MEDIUM
    parameters: Dict[str, Any] = field(default_factory=dict)
    schedule_config: Optional[Dict[str, Any]] = None
    retry_count: int = 3
    timeout: int = 300
    dependencies: List[str] = field(default_factory=list)
    success_callback: Optional[Callable] = None
    failure_callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0

@dataclass
class BotExecution:
    """
    Bot task execution record
    سجل تنفيذ مهمة البوت
    """
    execution_id: str
    task_id: str
    bot_id: str
    status: BotStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)

class AutomationBot:
    """
    Base automation bot class
    فئة البوت الأساسية للأتمتة
    """
    
    def __init__(self, bot_id: str, name: str, bot_type: BotType, 
                 workspace_path: str = "./bot_workspace"):
        self.bot_id = bot_id
        self.name = name
        self.bot_type = bot_type
        self.status = BotStatus.IDLE
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Create bot-specific directories
        self.bot_dir = self.workspace_path / f"bot_{bot_id}"
        self.bot_dir.mkdir(exist_ok=True)
        (self.bot_dir / "logs").mkdir(exist_ok=True)
        (self.bot_dir / "data").mkdir(exist_ok=True)
        (self.bot_dir / "temp").mkdir(exist_ok=True)
        
        # Task management
        self.task_queue: Queue = Queue()
        self.active_tasks: Dict[str, BotTask] = {}
        self.execution_history: List[BotExecution] = []
        
        # Configuration
        self.config: Dict[str, Any] = {}
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Performance metrics
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_execution_time": 0.0,
            "uptime_start": datetime.utcnow()
        }
        
        logger.info(f"Bot initialized: {self.name} ({self.bot_id})")
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure bot settings
        تكوين إعدادات البوت
        """
        self.config.update(config)
        logger.info(f"Bot {self.bot_id} configured with {len(config)} settings")
    
    def add_task(self, task: BotTask) -> bool:
        """
        Add task to bot queue
        إضافة مهمة إلى طابور البوت
        """
        try:
            # Validate task dependencies
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in self.active_tasks:
                        logger.warning(f"Task {task.task_id} has unmet dependency: {dep_id}")
            
            self.task_queue.put(task)
            self.active_tasks[task.task_id] = task
            logger.info(f"Task added to bot {self.bot_id}: {task.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add task {task.task_id}: {str(e)}")
            return False
    
    def start(self) -> bool:
        """
        Start bot execution
        بدء تنفيذ البوت
        """
        if self.is_running:
            logger.warning(f"Bot {self.bot_id} is already running")
            return False
        
        try:
            self.is_running = True
            self.status = BotStatus.RUNNING
            
            # Start worker thread
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            
            logger.info(f"Bot {self.bot_id} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot {self.bot_id}: {str(e)}")
            self.is_running = False
            self.status = BotStatus.ERROR
            return False
    
    def stop(self) -> bool:
        """
        Stop bot execution
        إيقاف تنفيذ البوت
        """
        try:
            self.is_running = False
            self.status = BotStatus.STOPPED
            
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join(timeout=5)
            
            logger.info(f"Bot {self.bot_id} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop bot {self.bot_id}: {str(e)}")
            return False
    
    def pause(self) -> bool:
        """
        Pause bot execution
        إيقاف البوت مؤقتاً
        """
        if self.status == BotStatus.RUNNING:
            self.status = BotStatus.PAUSED
            logger.info(f"Bot {self.bot_id} paused")
            return True
        return False
    
    def resume(self) -> bool:
        """
        Resume bot execution
        استئناف تنفيذ البوت
        """
        if self.status == BotStatus.PAUSED:
            self.status = BotStatus.RUNNING
            logger.info(f"Bot {self.bot_id} resumed")
            return True
        return False
    
    def _worker_loop(self) -> None:
        """
        Main worker loop for task execution
        حلقة العمل الرئيسية لتنفيذ المهام
        """
        while self.is_running:
            try:
                if self.status == BotStatus.PAUSED:
                    time.sleep(1)
                    continue
                
                # Get next task
                try:
                    task = self.task_queue.get(timeout=1)
                except Empty:
                    continue
                
                # Execute task
                execution = self._execute_task(task)
                self.execution_history.append(execution)
                
                # Update metrics
                self.metrics["total_tasks"] += 1
                if execution.status == BotStatus.COMPLETED:
                    self.metrics["successful_tasks"] += 1
                    task.success_count += 1
                else:
                    self.metrics["failed_tasks"] += 1
                    task.failure_count += 1
                
                task.execution_count += 1
                task.last_executed = execution.completed_at
                
                # Calculate average execution time
                if execution.duration:
                    total_successful = self.metrics["successful_tasks"]
                    current_avg = self.metrics["average_execution_time"]
                    self.metrics["average_execution_time"] = (
                        (current_avg * (total_successful - 1) + execution.duration) / total_successful
                    )
                
            except Exception as e:
                logger.error(f"Worker loop error in bot {self.bot_id}: {str(e)}")
                time.sleep(5)  # Prevent tight error loop
    
    def _execute_task(self, task: BotTask) -> BotExecution:
        """
        Execute individual task
        تنفيذ مهمة فردية
        """
        execution_id = f"{task.task_id}_{int(time.time())}"
        execution = BotExecution(
            execution_id=execution_id,
            task_id=task.task_id,
            bot_id=self.bot_id,
            status=BotStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        try:
            logger.info(f"Executing task: {task.name} ({task.task_id})")
            
            # Check dependencies
            if not self._check_dependencies(task):
                raise Exception("Task dependencies not met")
            
            # Execute task based on type
            start_time = time.time()
            result = self._perform_task_action(task)
            execution_time = time.time() - start_time
            
            # Update execution record
            execution.status = BotStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration = execution_time
            execution.result = result
            
            # Call success callback
            if task.success_callback:
                try:
                    task.success_callback(task, execution)
                except Exception as callback_error:
                    logger.warning(f"Success callback failed: {str(callback_error)}")
            
            logger.info(f"Task completed: {task.name} in {execution_time:.2f}s")
            
        except Exception as e:
            execution.status = BotStatus.ERROR
            execution.completed_at = datetime.utcnow()
            execution.error_message = str(e)
            
            # Call failure callback
            if task.failure_callback:
                try:
                    task.failure_callback(task, execution)
                except Exception as callback_error:
                    logger.warning(f"Failure callback failed: {str(callback_error)}")
            
            logger.error(f"Task failed: {task.name} - {str(e)}")
        
        return execution
    
    def _check_dependencies(self, task: BotTask) -> bool:
        """
        Check if task dependencies are satisfied
        التحقق من استيفاء تبعيات المهمة
        """
        if not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            # Check if dependency task completed successfully
            dep_executions = [
                ex for ex in self.execution_history 
                if ex.task_id == dep_id and ex.status == BotStatus.COMPLETED
            ]
            
            if not dep_executions:
                logger.warning(f"Dependency {dep_id} not satisfied for task {task.task_id}")
                return False
        
        return True
    
    def _perform_task_action(self, task: BotTask) -> Dict[str, Any]:
        """
        Perform the actual task action (to be overridden by subclasses)
        تنفيذ الإجراء الفعلي للمهمة (يتم تجاوزه بواسطة الفئات الفرعية)
        """
        # Base implementation - subclasses should override this
        logger.info(f"Performing base task action for {task.name}")
        return {"status": "completed", "message": "Base task action completed"}
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive bot status
        الحصول على حالة البوت الشاملة
        """
        uptime = datetime.utcnow() - self.metrics["uptime_start"]
        
        return {
            "bot_id": self.bot_id,
            "name": self.name,
            "type": self.bot_type.value,
            "status": self.status.value,
            "is_running": self.is_running,
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "total_executions": len(self.execution_history),
            "metrics": self.metrics,
            "uptime_seconds": uptime.total_seconds(),
            "last_execution": self.execution_history[-1].started_at.isoformat() if self.execution_history else None
        }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get bot execution history
        الحصول على تاريخ تنفيذ البوت
        """
        recent_executions = self.execution_history[-limit:] if self.execution_history else []
        
        return [
            {
                "execution_id": ex.execution_id,
                "task_id": ex.task_id,
                "status": ex.status.value,
                "started_at": ex.started_at.isoformat(),
                "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                "duration": ex.duration,
                "error_message": ex.error_message
            }
            for ex in recent_executions
        ]

# ==================== SECTION 2: Specialized Bot Types ====================

class WebAutomationBot(AutomationBot):
    """
    Web automation bot using Selenium
    بوت أتمتة الويب باستخدام Selenium
    """
    
    def __init__(self, bot_id: str, name: str, workspace_path: str = "./bot_workspace"):
        super().__init__(bot_id, name, BotType.WEB_AUTOMATION, workspace_path)
        self.driver: Optional[webdriver.Chrome] = None
        self.driver_options = self._setup_driver_options()
    
    def _setup_driver_options(self):
        """
        Setup Chrome driver options
        إعداد خيارات تشغيل Chrome
        """
        from selenium.webdriver.chrome.options import Options
        options = Options()
        
        # Default options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Add headless mode if configured
        if self.config.get('headless', True):
            options.add_argument('--headless')
        
        return options
    
    def _get_driver(self) -> webdriver.Chrome:
        """
        Get or create Chrome driver
        الحصول على أو إنشاء تشغيل Chrome
        """
        if self.driver is None:
            try:
                self.driver = webdriver.Chrome(options=self.driver_options)
                self.driver.set_page_load_timeout(30)
                self.driver.implicitly_wait(10)
                logger.info(f"Chrome driver created for bot {self.bot_id}")
            except Exception as e:
                logger.error(f"Failed to create Chrome driver: {str(e)}")
                raise
        
        return self.driver
    
    def _perform_task_action(self, task: BotTask) -> Dict[str, Any]:
        """
        Perform web automation task
        تنفيذ مهمة أتمتة الويب
        """
        action_type = task.parameters.get('action_type')
        
        if action_type == 'navigate':
            return self._navigate_action(task.parameters)
        elif action_type == 'fill_form':
            return self._fill_form_action(task.parameters)
        elif action_type == 'click_element':
            return self._click_element_action(task.parameters)
        elif action_type == 'extract_data':
            return self._extract_data_action(task.parameters)
        elif action_type == 'screenshot':
            return self._screenshot_action(task.parameters)
        else:
            raise ValueError(f"Unknown web automation action: {action_type}")
    
    def _navigate_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Navigate to URL
        التنقل إلى رابط
        """
        url = params.get('url')
        if not url:
            raise ValueError("URL parameter required for navigate action")
        
        driver = self._get_driver()
        driver.get(url)
        
        # Wait for page load
        wait_time = params.get('wait_time', 3)
        time.sleep(wait_time)
        
        return {
            "action": "navigate",
            "url": url,
            "current_url": driver.current_url,
            "title": driver.title
        }
    
    def _fill_form_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill form fields
        ملء حقول النموذج
        """
        form_data = params.get('form_data', {})
        if not form_data:
            raise ValueError("form_data parameter required for fill_form action")
        
        driver = self._get_driver()
        filled_fields = []
        
        for field_selector, value in form_data.items():
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, field_selector))
                )
                
                # Clear and fill field
                element.clear()
                element.send_keys(str(value))
                filled_fields.append(field_selector)
                
            except Exception as e:
                logger.warning(f"Failed to fill field {field_selector}: {str(e)}")
        
        return {
            "action": "fill_form",
            "filled_fields": filled_fields,
            "total_fields": len(form_data)
        }
    
    def _click_element_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Click element
        النقر على عنصر
        """
        selector = params.get('selector')
        if not selector:
            raise ValueError("selector parameter required for click_element action")
        
        driver = self._get_driver()
        
        element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        
        # Scroll to element and click
        driver.execute_script("arguments[0].scrollIntoView();", element)
        time.sleep(1)
        element.click()
        
        # Wait after click
        wait_time = params.get('wait_after_click', 2)
        time.sleep(wait_time)
        
        return {
            "action": "click_element",
            "selector": selector,
            "current_url": driver.current_url
        }
    
    def _extract_data_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data from page
        استخراج البيانات من الصفحة
        """
        selectors = params.get('selectors', {})
        if not selectors:
            raise ValueError("selectors parameter required for extract_data action")
        
        driver = self._get_driver()
        extracted_data = {}
        
        for field_name, selector in selectors.items():
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                
                if len(elements) == 1:
                    extracted_data[field_name] = elements[0].text.strip()
                elif len(elements) > 1:
                    extracted_data[field_name] = [el.text.strip() for el in elements]
                else:
                    extracted_data[field_name] = None
                    
            except Exception as e:
                logger.warning(f"Failed to extract {field_name}: {str(e)}")
                extracted_data[field_name] = None
        
        return {
            "action": "extract_data",
            "data": extracted_data,
            "url": driver.current_url
        }
    
    def _screenshot_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take screenshot
        أخذ لقطة شاشة
        """
        filename = params.get('filename', f'screenshot_{int(time.time())}.png')
        filepath = self.bot_dir / "data" / filename
        
        driver = self._get_driver()
        driver.save_screenshot(str(filepath))
        
        return {
            "action": "screenshot",
            "filename": filename,
            "filepath": str(filepath),
            "url": driver.current_url
        }
    
    def stop(self) -> bool:
        """
        Stop web automation bot and close driver
        إيقاف بوت أتمتة الويب وإغلاق التشغيل
        """
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info(f"Chrome driver closed for bot {self.bot_id}")
        except Exception as e:
            logger.error(f"Error closing Chrome driver: {str(e)}")
        
        return super().stop()
