# Service ID: PYL94
# Service Name: Python web scraping and data extraction tools
# أدوات استخراج البيانات وكشط المواقع بـ Python

import requests
import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import urllib.parse
from pathlib import Path
import hashlib
import random
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import pandas as pd
from fake_useragent import UserAgent

# Configure logging for scraping operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== SECTION 1: Core Scraping Models and Configuration ====================

class ScrapingMethod(Enum):
    """
    Web scraping methods
    طرق كشط المواقع
    """
    REQUESTS = "requests"
    SELENIUM = "selenium"
    ASYNC_HTTP = "async_http"
    HYBRID = "hybrid"

class DataFormat(Enum):
    """
    Output data formats
    تنسيقات البيانات المخرجة
    """
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    XML = "xml"

class ScrapingStatus(Enum):
    """
    Scraping job status
    حالة مهمة الكشط
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

@dataclass
class ScrapingTarget:
    """
    Target website or page for scraping
    الموقع أو الصفحة المستهدفة للكشط
    """
    url: str
    name: str
    selectors: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    wait_time: float = 1.0
    timeout: int = 30
    max_retries: int = 3
    javascript_required: bool = False
    pagination_selector: Optional[str] = None
    max_pages: int = 1

@dataclass
class ScrapingJob:
    """
    Scraping job configuration and status
    تكوين وحالة مهمة الكشط
    """
    job_id: str
    name: str
    targets: List[ScrapingTarget]
    method: ScrapingMethod = ScrapingMethod.REQUESTS
    output_format: DataFormat = DataFormat.JSON
    output_path: str = ""
    status: ScrapingStatus = ScrapingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_items: int = 0
    scraped_items: int = 0
    failed_items: int = 0
    error_log: List[str] = field(default_factory=list)
    data_cache: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ProxyConfig:
    """
    Proxy configuration for scraping
    تكوين البروكسي للكشط
    """
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    
    def to_url(self) -> str:
        """Convert proxy config to URL format"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

class ScrapingEngine:
    """
    Advanced web scraping engine with multiple methods
    محرك كشط المواقع المتقدم بطرق متعددة
    """
    
    def __init__(self, workspace_path: str = "./scraping_workspace", 
                 max_workers: int = 5, use_cache: bool = True):
        """
        Initialize scraping engine
        تهيئة محرك الكشط
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.workspace_path / "data").mkdir(exist_ok=True)
        (self.workspace_path / "cache").mkdir(exist_ok=True)
        (self.workspace_path / "logs").mkdir(exist_ok=True)
        
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.jobs: Dict[str, ScrapingJob] = {}
        self.proxy_pool: List[ProxyConfig] = []
        self.user_agents: List[str] = []
        self.session_pool: Dict[str, requests.Session] = {}
        
        # Initialize user agents
        self._initialize_user_agents()
        
        # Rate limiting
        self.last_request_times = {}
        
        logger.info(f"Scraping engine initialized: {workspace_path}")
    
    def _initialize_user_agents(self) -> None:
        """
        Initialize user agent rotation
        تهيئة تدوير وكلاء المستخدم
        """
        try:
            ua = UserAgent()
            self.user_agents = [ua.random for _ in range(10)]
        except:
            # Fallback user agents
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            ]
    
    def add_proxy(self, proxy: ProxyConfig) -> None:
        """
        Add proxy to rotation pool
        إضافة بروكسي لمجموعة التدوير
        """
        self.proxy_pool.append(proxy)
        logger.info(f"Proxy added: {proxy.host}:{proxy.port}")
    
    def create_job(self, job: ScrapingJob) -> bool:
        """
        Create new scraping job
        إنشاء مهمة كشط جديدة
        """
        try:
            # Validate targets
            for target in job.targets:
                if not self._validate_url(target.url):
                    raise ValueError(f"Invalid URL: {target.url}")
            
            # Set output path if not provided
            if not job.output_path:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                job.output_path = str(self.workspace_path / "data" / f"{job.job_id}_{timestamp}")
            
            self.jobs[job.job_id] = job
            logger.info(f"Scraping job created: {job.name} ({job.job_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create job {job.job_id}: {str(e)}")
            return False
    
    def _validate_url(self, url: str) -> bool:
        """
        Validate URL format
        التحقق من تنسيق الرابط
        """
        try:
            result = urllib.parse.urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def start_job(self, job_id: str) -> bool:
        """
        Start scraping job execution
        بدء تنفيذ مهمة الكشط
        """
        if job_id not in self.jobs:
            logger.error(f"Job not found: {job_id}")
            return False
        
        job = self.jobs[job_id]
        
        if job.status == ScrapingStatus.RUNNING:
            logger.warning(f"Job already running: {job_id}")
            return False
        
        try:
            job.status = ScrapingStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            # Execute job based on method
            if job.method == ScrapingMethod.REQUESTS:
                self._execute_requests_job(job)
            elif job.method == ScrapingMethod.SELENIUM:
                self._execute_selenium_job(job)
            elif job.method == ScrapingMethod.ASYNC_HTTP:
                asyncio.run(self._execute_async_job(job))
            
            job.status = ScrapingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            
            # Save results
            self._save_job_results(job)
            
            logger.info(f"Job completed: {job.name} - {job.scraped_items} items scraped")
            return True
            
        except Exception as e:
            job.status = ScrapingStatus.FAILED
            job.error_log.append(str(e))
            logger.error(f"Job failed: {job.name} - {str(e)}")
            return False
    
    def _get_session(self, domain: str) -> requests.Session:
        """
        Get or create session for domain
        الحصول على أو إنشاء جلسة للنطاق
        """
        if domain not in self.session_pool:
            session = requests.Session()
            
            # Set random user agent
            session.headers.update({
                'User-Agent': random.choice(self.user_agents)
            })
            
            # Set proxy if available
            if self.proxy_pool:
                proxy = random.choice(self.proxy_pool)
                session.proxies = {
                    'http': proxy.to_url(),
                    'https': proxy.to_url()
                }
            
            self.session_pool[domain] = session
        
        return self.session_pool[domain]
    
    def _respect_rate_limit(self, domain: str, delay: float = 1.0) -> None:
        """
        Implement rate limiting per domain
        تطبيق تحديد المعدل لكل نطاق
        """
        current_time = time.time()
        
        if domain in self.last_request_times:
            elapsed = current_time - self.last_request_times[domain]
            if elapsed < delay:
                sleep_time = delay - elapsed
                time.sleep(sleep_time)
        
        self.last_request_times[domain] = time.time()
    
    def _execute_requests_job(self, job: ScrapingJob) -> None:
        """
        Execute job using requests library
        تنفيذ المهمة باستخدام مكتبة requests
        """
        for target in job.targets:
            try:
                domain = urllib.parse.urlparse(target.url).netloc
                session = self._get_session(domain)
                
                # Apply rate limiting
                self._respect_rate_limit(domain, target.wait_time)
                
                # Make request
                response = session.get(
                    target.url,
                    headers=target.headers,
                    cookies=target.cookies,
                    timeout=target.timeout
                )
                response.raise_for_status()
                
                # Parse content
                soup = BeautifulSoup(response.content, 'html.parser')
                extracted_data = self._extract_data(soup, target)
                
                job.data_cache.extend(extracted_data)
                job.scraped_items += len(extracted_data)
                
            except Exception as e:
                job.failed_items += 1
                job.error_log.append(f"Target {target.name}: {str(e)}")
                logger.error(f"Failed to scrape {target.url}: {str(e)}")
    
    def _extract_data(self, soup: BeautifulSoup, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """
        Extract data using CSS selectors
        استخراج البيانات باستخدام محددات CSS
        """
        extracted_items = []
        
        try:
            # Find all items (assuming there's a container selector)
            if 'container' in target.selectors:
                containers = soup.select(target.selectors['container'])
            else:
                containers = [soup]  # Use entire page as container
            
            for container in containers:
                item_data = {}
                
                # Extract data for each selector
                for field_name, selector in target.selectors.items():
                    if field_name == 'container':
                        continue
                    
                    try:
                        element = container.select_one(selector)
                        if element:
                            # Extract text, attribute, or href based on selector
                            if selector.endswith('@href'):
                                item_data[field_name] = element.get('href', '')
                            elif selector.endswith('@src'):
                                item_data[field_name] = element.get('src', '')
                            elif '@' in selector:
                                attr = selector.split('@')[-1]
                                item_data[field_name] = element.get(attr, '')
                            else:
                                item_data[field_name] = element.get_text(strip=True)
                        else:
                            item_data[field_name] = ""
                    except Exception as e:
                        item_data[field_name] = ""
                        logger.warning(f"Failed to extract {field_name}: {str(e)}")
                
                # Add metadata
                item_data['_scraped_at'] = datetime.utcnow().isoformat()
                item_data['_source_url'] = target.url
                item_data['_target_name'] = target.name
                
                if any(item_data.values()):  # Only add if we got some data
                    extracted_items.append(item_data)
        
        except Exception as e:
            logger.error(f"Data extraction failed: {str(e)}")
        
        return extracted_items
