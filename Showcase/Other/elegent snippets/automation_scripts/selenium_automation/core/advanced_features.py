# Service ID: ATS21 - Part 3
# Advanced Selenium Features and Utilities
# الميزات والأدوات المتقدمة لـ Selenium

import time
import logging
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService

import pandas as pd
import sqlite3
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ==================== SECTION 3: Advanced Features and Utilities ====================

@dataclass
class BrowserProfile:
    """
    Browser profile configuration
    تكوين ملف تعريف المتصفح
    """
    name: str
    browser_type: str
    user_agent: str
    viewport_size: tuple
    proxy_settings: Optional[Dict[str, str]] = None
    extensions: List[str] = None
    preferences: Dict[str, Any] = None
    stealth_mode: bool = True

class AdvancedBrowserManager:
    """
    Advanced browser session management with profiles and optimization
    إدارة جلسات المتصفح المتقدمة مع الملفات الشخصية والتحسين
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.profiles_path = workspace_path / "browser_profiles"
        self.profiles_path.mkdir(exist_ok=True)
        
        self.active_sessions: Dict[str, webdriver.Chrome] = {}
        self.session_stats: Dict[str, Dict[str, Any]] = {}
        self.browser_profiles: Dict[str, BrowserProfile] = {}
        
        # Load default profiles
        self._initialize_default_profiles()
    
    def _initialize_default_profiles(self):
        """
        Initialize default browser profiles
        تهيئة ملفات تعريف المتصفح الافتراضية
        """
        default_profiles = [
            BrowserProfile(
                name="desktop_chrome",
                browser_type="chrome",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport_size=(1920, 1080),
                stealth_mode=True
            ),
            BrowserProfile(
                name="mobile_chrome",
                browser_type="chrome",
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                viewport_size=(375, 812),
                stealth_mode=True
            ),
            BrowserProfile(
                name="firefox_desktop",
                browser_type="firefox",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
                viewport_size=(1920, 1080),
                stealth_mode=True
            )
        ]
        
        for profile in default_profiles:
            self.browser_profiles[profile.name] = profile
    
    def create_browser_session(self, profile_name: str = "desktop_chrome", 
                             session_id: Optional[str] = None) -> str:
        """
        Create optimized browser session with profile
        إنشاء جلسة متصفح محسنة مع الملف الشخصي
        """
        if session_id is None:
            session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        
        profile = self.browser_profiles.get(profile_name)
        if not profile:
            raise ValueError(f"Browser profile not found: {profile_name}")
        
        try:
            # Create browser with profile settings
            driver = self._create_optimized_driver(profile, session_id)
            
            # Store session
            self.active_sessions[session_id] = driver
            self.session_stats[session_id] = {
                "profile_name": profile_name,
                "created_at": datetime.utcnow().isoformat(),
                "page_loads": 0,
                "actions_executed": 0,
                "errors_count": 0,
                "last_activity": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Browser session created: {session_id} with profile {profile_name}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create browser session: {str(e)}")
            raise
    
    def _create_optimized_driver(self, profile: BrowserProfile, session_id: str) -> webdriver.Chrome:
        """
        Create optimized WebDriver instance
        إنشاء مثيل WebDriver محسن
        """
        if profile.browser_type == "chrome":
            return self._create_chrome_driver(profile, session_id)
        elif profile.browser_type == "firefox":
            return self._create_firefox_driver(profile, session_id)
        elif profile.browser_type == "edge":
            return self._create_edge_driver(profile, session_id)
        else:
            raise ValueError(f"Unsupported browser type: {profile.browser_type}")
    
    def _create_chrome_driver(self, profile: BrowserProfile, session_id: str) -> webdriver.Chrome:
        """
        Create optimized Chrome driver
        إنشاء سائق Chrome محسن
        """
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        
        # Basic optimization options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--disable-javascript")  # Can be enabled per need
        
        # Performance optimizations
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=4096")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")
        
        # Stealth mode options
        if profile.stealth_mode:
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
        
        # User agent
        options.add_argument(f"--user-agent={profile.user_agent}")
        
        # Window size
        options.add_argument(f"--window-size={profile.viewport_size[0]},{profile.viewport_size[1]}")
        
        # Proxy settings
        if profile.proxy_settings:
            proxy_server = profile.proxy_settings.get('server')
            if proxy_server:
                options.add_argument(f"--proxy-server={proxy_server}")
        
        # Profile directory
        profile_dir = self.profiles_path / f"chrome_{session_id}"
        profile_dir.mkdir(exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        
        # Custom preferences
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2  # Block images for faster loading
            }
        }
        
        if profile.preferences:
            prefs.update(profile.preferences)
        
        options.add_experimental_option("prefs", prefs)
        
        # Create driver
        driver = webdriver.Chrome(options=options)
        
        # Additional stealth configurations
        if profile.stealth_mode:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def get_session(self, session_id: str) -> webdriver.Chrome:
        """
        Get active browser session
        الحصول على جلسة المتصفح النشطة
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session not found: {session_id}")
        
        # Update last activity
        self.session_stats[session_id]["last_activity"] = datetime.utcnow().isoformat()
        return self.active_sessions[session_id]
    
    def close_session(self, session_id: str):
        """
        Close browser session and cleanup
        إغلاق جلسة المتصفح والتنظيف
        """
        if session_id in self.active_sessions:
            try:
                self.active_sessions[session_id].quit()
                del self.active_sessions[session_id]
                
                # Cleanup profile directory
                profile_dir = self.profiles_path / f"chrome_{session_id}"
                if profile_dir.exists():
                    import shutil
                    shutil.rmtree(profile_dir, ignore_errors=True)
                
                logger.info(f"Browser session closed: {session_id}")
                
            except Exception as e:
                logger.error(f"Error closing session {session_id}: {str(e)}")
    
    def cleanup_inactive_sessions(self, max_idle_minutes: int = 30):
        """
        Cleanup inactive browser sessions
        تنظيف جلسات المتصفح غير النشطة
        """
        current_time = datetime.utcnow()
        inactive_sessions = []
        
        for session_id, stats in self.session_stats.items():
            last_activity = datetime.fromisoformat(stats["last_activity"])
            idle_time = current_time - last_activity
            
            if idle_time.total_seconds() > (max_idle_minutes * 60):
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            self.close_session(session_id)
            if session_id in self.session_stats:
                del self.session_stats[session_id]
        
        logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")

class ParallelAutomationManager:
    """
    Parallel automation execution manager
    مدير تنفيذ الأتمتة المتوازية
    """
    
    def __init__(self, workspace_path: Path, max_workers: int = 4):
        self.workspace_path = workspace_path
        self.max_workers = max_workers
        self.browser_manager = AdvancedBrowserManager(workspace_path)
        self.execution_results: Dict[str, Any] = {}
        self.execution_lock = threading.Lock()
    
    def execute_workflows_parallel(self, workflows: List[Dict[str, Any]], 
                                 input_data_list: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute multiple workflows in parallel
        تنفيذ عدة مسارات عمل بشكل متوازي
        """
        if input_data_list is None:
            input_data_list = [{}] * len(workflows)
        
        if len(workflows) != len(input_data_list):
            raise ValueError("Workflows and input data lists must have same length")
        
        execution_id = f"parallel_{int(time.time())}"
        start_time = time.time()
        
        # Prepare execution tasks
        tasks = []
        for i, (workflow, input_data) in enumerate(zip(workflows, input_data_list)):
            task_id = f"{execution_id}_task_{i}"
            tasks.append({
                "task_id": task_id,
                "workflow": workflow,
                "input_data": input_data
            })
        
        # Execute tasks in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._execute_single_workflow, task): task
                for task in tasks
            }
            
            # Collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results[task["task_id"]] = result
                except Exception as e:
                    logger.error(f"Task {task['task_id']} failed: {str(e)}")
                    results[task["task_id"]] = {
                        "status": "failed",
                        "error": str(e),
                        "task_id": task["task_id"]
                    }
        
        # Compile execution summary
        execution_time = time.time() - start_time
        successful_tasks = [r for r in results.values() if r.get("status") == "success"]
        failed_tasks = [r for r in results.values() if r.get("status") == "failed"]
        
        summary = {
            "execution_id": execution_id,
            "total_tasks": len(tasks),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "success_rate": (len(successful_tasks) / len(tasks)) * 100,
            "total_execution_time": round(execution_time, 2),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store results
        with self.execution_lock:
            self.execution_results[execution_id] = summary
        
        logger.info(f"Parallel execution completed: {execution_id} - {len(successful_tasks)}/{len(tasks)} successful")
        return summary
    
    def _execute_single_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute single workflow task
        تنفيذ مهمة مسار عمل واحد
        """
        task_id = task["task_id"]
        workflow = task["workflow"]
        input_data = task["input_data"]
        
        session_id = None
        start_time = time.time()
        
        try:
            # Create browser session for this task
            profile_name = workflow.get("browser_profile", "desktop_chrome")
            session_id = self.browser_manager.create_browser_session(profile_name)
            driver = self.browser_manager.get_session(session_id)
            
            # Execute workflow actions
            from .selenium_automation_engine import SeleniumAutomationEngine
            engine = SeleniumAutomationEngine(self.workspace_path)
            
            # Register and execute workflow
            workflow_id = engine.register_workflow(workflow)
            execution_result = engine.execute_workflow(workflow_id, input_data, session_id)
            
            execution_time = time.time() - start_time
            
            return {
                "status": "success",
                "task_id": task_id,
                "workflow_id": workflow_id,
                "execution_time": round(execution_time, 2),
                "result": execution_result,
                "session_id": session_id
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Workflow execution failed for task {task_id}: {str(e)}")
            
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
                "execution_time": round(execution_time, 2),
                "session_id": session_id
            }
        
        finally:
            # Cleanup session
            if session_id:
                try:
                    self.browser_manager.close_session(session_id)
                except Exception as e:
                    logger.warning(f"Failed to cleanup session {session_id}: {str(e)}")

class AutomationReportGenerator:
    """
    Advanced reporting and analytics for automation executions
    التقارير والتحليلات المتقدمة لتنفيذ الأتمتة
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.reports_path = workspace_path / "reports"
        self.reports_path.mkdir(exist_ok=True)
        
        # Initialize database for execution history
        self.db_path = workspace_path / "automation_history.db"
        self._initialize_database()
    
    def _initialize_database(self):
        """
        Initialize SQLite database for execution history
        تهيئة قاعدة بيانات SQLite لسجل التنفيذ
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT UNIQUE,
                    workflow_id TEXT,
                    status TEXT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    execution_time REAL,
                    actions_count INTEGER,
                    success_rate REAL,
                    error_message TEXT,
                    input_data TEXT,
                    output_data TEXT,
                    browser_profile TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS action_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT,
                    action_id TEXT,
                    action_type TEXT,
                    status TEXT,
                    execution_time REAL,
                    error_message TEXT,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (execution_id) REFERENCES workflow_executions (execution_id)
                )
            """)
    
    def record_execution(self, execution_data: Dict[str, Any]):
        """
        Record workflow execution in database
        تسجيل تنفيذ مسار العمل في قاعدة البيانات
        """
        with sqlite3.connect(self.db_path) as conn:
            # Record workflow execution
            conn.execute("""
                INSERT OR REPLACE INTO workflow_executions 
                (execution_id, workflow_id, status, start_time, end_time, execution_time, 
                 actions_count, success_rate, error_message, input_data, output_data, browser_profile)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution_data.get("execution_id"),
                execution_data.get("workflow_id"),
                execution_data.get("status"),
                execution_data.get("start_time"),
                execution_data.get("end_time"),
                execution_data.get("execution_time"),
                execution_data.get("actions_count", 0),
                execution_data.get("success_rate", 0),
                execution_data.get("error_message"),
                json.dumps(execution_data.get("input_data", {})),
                json.dumps(execution_data.get("output_data", {})),
                execution_data.get("browser_profile")
            ))
            
            # Record individual action executions
            action_history = execution_data.get("action_history", [])
            for action in action_history:
                conn.execute("""
                    INSERT INTO action_executions 
                    (execution_id, action_id, action_type, status, execution_time, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_data.get("execution_id"),
                    action.get("action_id"),
                    action.get("action_type"),
                    action.get("status"),
                    action.get("execution_time"),
                    action.get("error"),
                    action.get("timestamp")
                ))
    
    def generate_performance_report(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive performance report
        إنشاء تقرير أداء شامل
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            # Overall statistics
            overall_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_executions,
                    AVG(execution_time) as avg_execution_time,
                    AVG(success_rate) as avg_success_rate,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_executions,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions
                FROM workflow_executions 
                WHERE created_at >= ? AND created_at <= ?
            """, (start_date.isoformat(), end_date.isoformat())).fetchone()
            
            # Performance by workflow
            workflow_stats = conn.execute("""
                SELECT 
                    workflow_id,
                    COUNT(*) as executions,
                    AVG(execution_time) as avg_time,
                    AVG(success_rate) as avg_success_rate,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM workflow_executions 
                WHERE created_at >= ? AND created_at <= ?
                GROUP BY workflow_id
                ORDER BY executions DESC
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()
            
            # Performance by browser profile
            browser_stats = conn.execute("""
                SELECT 
                    browser_profile,
                    COUNT(*) as executions,
                    AVG(execution_time) as avg_time,
                    AVG(success_rate) as avg_success_rate
                FROM workflow_executions 
                WHERE created_at >= ? AND created_at <= ? AND browser_profile IS NOT NULL
                GROUP BY browser_profile
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()
            
            # Most common errors
            error_stats = conn.execute("""
                SELECT 
                    error_message,
                    COUNT(*) as occurrences
                FROM workflow_executions 
                WHERE created_at >= ? AND created_at <= ? AND error_message IS NOT NULL
                GROUP BY error_message
                ORDER BY occurrences DESC
                LIMIT 10
            """, (start_date.isoformat(), end_date.isoformat())).fetchall()
        
        # Compile report
        report = {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days_back
            },
            "overall_statistics": {
                "total_executions": overall_stats[0] or 0,
                "average_execution_time": round(overall_stats[1] or 0, 2),
                "average_success_rate": round(overall_stats[2] or 0, 2),
                "successful_executions": overall_stats[3] or 0,
                "failed_executions": overall_stats[4] or 0,
                "overall_success_rate": round((overall_stats[3] or 0) / max(overall_stats[0] or 1, 1) * 100, 2)
            },
            "workflow_performance": [
                {
                    "workflow_id": row[0],
                    "executions": row[1],
                    "avg_execution_time": round(row[2], 2),
                    "avg_success_rate": round(row[3], 2),
                    "successful": row[4],
                    "failed": row[5],
                    "success_rate": round(row[4] / max(row[1], 1) * 100, 2)
                }
                for row in workflow_stats
            ],
            "browser_performance": [
                {
                    "browser_profile": row[0],
                    "executions": row[1],
                    "avg_execution_time": round(row[2], 2),
                    "avg_success_rate": round(row[3], 2)
                }
                for row in browser_stats
            ],
            "common_errors": [
                {
                    "error_message": row[0],
                    "occurrences": row[1]
                }
                for row in error_stats
            ],
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Save report to file
        report_filename = f"performance_report_{int(time.time())}.json"
        report_path = self.reports_path / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Performance report generated: {report_path}")
        return report
    
    def export_execution_data(self, format: str = "excel", days_back: int = 30) -> str:
        """
        Export execution data to various formats
        تصدير بيانات التنفيذ إلى تنسيقات مختلفة
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get execution data
            executions_df = pd.read_sql_query("""
                SELECT * FROM workflow_executions 
                WHERE created_at >= ? AND created_at <= ?
                ORDER BY created_at DESC
            """, conn, params=(start_date.isoformat(), end_date.isoformat()))
            
            # Get action data
            actions_df = pd.read_sql_query("""
                SELECT ae.* FROM action_executions ae
                JOIN workflow_executions we ON ae.execution_id = we.execution_id
                WHERE we.created_at >= ? AND we.created_at <= ?
                ORDER BY ae.timestamp DESC
            """, conn, params=(start_date.isoformat(), end_date.isoformat()))
        
        timestamp = int(time.time())
        
        if format.lower() == "excel":
            filename = f"automation_data_{timestamp}.xlsx"
            filepath = self.reports_path / filename
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                executions_df.to_excel(writer, sheet_name='Workflow Executions', index=False)
                actions_df.to_excel(writer, sheet_name='Action Executions', index=False)
        
        elif format.lower() == "csv":
            filename = f"automation_data_{timestamp}.csv"
            filepath = self.reports_path / filename
            executions_df.to_csv(filepath, index=False)
        
        elif format.lower() == "json":
            filename = f"automation_data_{timestamp}.json"
            filepath = self.reports_path / filename
            
            data = {
                "workflow_executions": executions_df.to_dict('records'),
                "action_executions": actions_df.to_dict('records'),
                "exported_at": datetime.utcnow().isoformat()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Execution data exported: {filepath}")
        return str(filepath)
