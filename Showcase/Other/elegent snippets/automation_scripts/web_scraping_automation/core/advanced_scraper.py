# Service ID: ATS34
# Service Name: Advanced web scraping scripts for efficient data extraction
# تطوير سكريبتات متقدمة لاستخراج البيانات من المواقع بكفاءة

import requests
import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
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
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue, Empty
import csv
from lxml import html, etree
import xml.etree.ElementTree as ET

# Configure logging for scraping operations
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('advanced_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== SECTION 1: Advanced Scraping Configuration ====================

class ScrapingStrategy(Enum):
    """
    Web scraping strategies
    استراتيجيات كشط المواقع
    """
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"
    STEALTH = "stealth"

class DataExtractionMode(Enum):
    """
    Data extraction modes
    أنماط استخراج البيانات
    """
    STRUCTURED = "structured"
    SEMI_STRUCTURED = "semi_structured"
    UNSTRUCTURED = "unstructured"
    MIXED = "mixed"

class AntiDetectionLevel(Enum):
    """
    Anti-detection protection levels
    مستويات الحماية من الكشف
    """
    BASIC = "basic"
    ADVANCED = "advanced"
    MAXIMUM = "maximum"

@dataclass
class ScrapingProfile:
    """
    Advanced scraping profile configuration
    تكوين ملف تعريف الكشط المتقدم
    """
    name: str
    strategy: ScrapingStrategy = ScrapingStrategy.BALANCED
    extraction_mode: DataExtractionMode = DataExtractionMode.STRUCTURED
    anti_detection: AntiDetectionLevel = AntiDetectionLevel.ADVANCED
    max_concurrent_requests: int = 5
    request_delay_range: tuple = (1.0, 3.0)
    retry_attempts: int = 3
    timeout: int = 30
    use_proxy_rotation: bool = True
    use_user_agent_rotation: bool = True
    respect_robots_txt: bool = True
    custom_headers: Dict[str, str] = field(default_factory=dict)
    javascript_execution: bool = False
    screenshot_on_error: bool = False

@dataclass
class ExtractionRule:
    """
    Data extraction rule definition
    تعريف قاعدة استخراج البيانات
    """
    field_name: str
    selector: str
    selector_type: str = "css"  # css, xpath, regex
    extraction_method: str = "text"  # text, attribute, html, href, src
    attribute_name: Optional[str] = None
    data_type: str = "string"  # string, integer, float, date, url
    required: bool = True
    default_value: Any = None
    validation_regex: Optional[str] = None
    transformation_function: Optional[Callable] = None

@dataclass
class ScrapingTarget:
    """
    Advanced scraping target with comprehensive configuration
    هدف الكشط المتقدم مع التكوين الشامل
    """
    url: str
    name: str
    profile: ScrapingProfile
    extraction_rules: List[ExtractionRule]
    pagination_config: Optional[Dict[str, Any]] = None
    authentication_config: Optional[Dict[str, Any]] = None
    custom_cookies: Dict[str, str] = field(default_factory=dict)
    pre_processing_script: Optional[str] = None
    post_processing_function: Optional[Callable] = None

class AdvancedWebScraper:
    """
    Advanced web scraping engine with intelligent automation
    محرك كشط المواقع المتقدم مع الأتمتة الذكية
    """
    
    def __init__(self, workspace_path: str = "./scraping_workspace", 
                 max_workers: int = 10):
        """
        Initialize advanced web scraper
        تهيئة كاشط المواقع المتقدم
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Create workspace structure
        (self.workspace_path / "data").mkdir(exist_ok=True)
        (self.workspace_path / "logs").mkdir(exist_ok=True)
        (self.workspace_path / "cache").mkdir(exist_ok=True)
        (self.workspace_path / "screenshots").mkdir(exist_ok=True)
        (self.workspace_path / "profiles").mkdir(exist_ok=True)
        
        self.max_workers = max_workers
        self.session_pool: Dict[str, requests.Session] = {}
        self.proxy_pool: List[Dict[str, str]] = []
        self.user_agents: List[str] = []
        self.scraped_data: Dict[str, List[Dict[str, Any]]] = {}
        
        # Performance tracking
        self.performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_data_points": 0,
            "average_response_time": 0.0,
            "start_time": datetime.utcnow()
        }
        
        # Initialize components
        self._initialize_user_agents()
        self._load_proxy_list()
        
        logger.info(f"Advanced web scraper initialized: {workspace_path}")
    
    def _initialize_user_agents(self) -> None:
        """
        Initialize comprehensive user agent pool
        تهيئة مجموعة شاملة من وكلاء المستخدم
        """
        try:
            ua = UserAgent()
            # Generate diverse user agents
            self.user_agents = [
                ua.chrome, ua.firefox, ua.safari, ua.edge,
                ua.chrome, ua.firefox, ua.safari, ua.edge,
                ua.random, ua.random
            ]
        except:
            # Fallback comprehensive user agents
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
            ]
    
    def _load_proxy_list(self) -> None:
        """
        Load proxy configuration from file or API
        تحميل تكوين البروكسي من ملف أو API
        """
        proxy_file = self.workspace_path / "proxies.json"
        if proxy_file.exists():
            try:
                with open(proxy_file, 'r') as f:
                    self.proxy_pool = json.load(f)
                logger.info(f"Loaded {len(self.proxy_pool)} proxies")
            except Exception as e:
                logger.warning(f"Failed to load proxies: {str(e)}")
    
    def add_proxy(self, proxy_config: Dict[str, str]) -> None:
        """
        Add proxy to rotation pool
        إضافة بروكسي لمجموعة التدوير
        """
        self.proxy_pool.append(proxy_config)
        logger.info(f"Proxy added: {proxy_config.get('host', 'unknown')}")
    
    def create_scraping_session(self, profile: ScrapingProfile) -> requests.Session:
        """
        Create optimized scraping session
        إنشاء جلسة كشط محسنة
        """
        session = requests.Session()
        
        # Set user agent
        if profile.use_user_agent_rotation:
            session.headers.update({
                'User-Agent': random.choice(self.user_agents)
            })
        
        # Add custom headers
        session.headers.update(profile.custom_headers)
        
        # Set common headers for stealth
        if profile.anti_detection in [AntiDetectionLevel.ADVANCED, AntiDetectionLevel.MAXIMUM]:
            stealth_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            session.headers.update(stealth_headers)
        
        # Configure proxy
        if profile.use_proxy_rotation and self.proxy_pool:
            proxy = random.choice(self.proxy_pool)
            session.proxies = {
                'http': f"http://{proxy['host']}:{proxy['port']}",
                'https': f"http://{proxy['host']}:{proxy['port']}"
            }
        
        # Set timeout and retries
        session.timeout = profile.timeout
        
        return session
    
    def extract_data_from_element(self, element, rule: ExtractionRule) -> Any:
        """
        Extract data from HTML element based on rule
        استخراج البيانات من عنصر HTML بناءً على القاعدة
        """
        try:
            if rule.selector_type == "css":
                if rule.extraction_method == "text":
                    value = element.get_text(strip=True) if hasattr(element, 'get_text') else element.text
                elif rule.extraction_method == "attribute" and rule.attribute_name:
                    value = element.get(rule.attribute_name, '') if hasattr(element, 'get') else element.get_attribute(rule.attribute_name)
                elif rule.extraction_method == "href":
                    value = element.get('href', '') if hasattr(element, 'get') else element.get_attribute('href')
                elif rule.extraction_method == "src":
                    value = element.get('src', '') if hasattr(element, 'get') else element.get_attribute('src')
                elif rule.extraction_method == "html":
                    value = str(element)
                else:
                    value = element.get_text(strip=True) if hasattr(element, 'get_text') else element.text
            
            # Apply data type conversion
            if rule.data_type == "integer":
                value = int(re.sub(r'[^\d]', '', str(value))) if value else 0
            elif rule.data_type == "float":
                value = float(re.sub(r'[^\d.]', '', str(value))) if value else 0.0
            elif rule.data_type == "date":
                # Basic date parsing - can be enhanced
                value = pd.to_datetime(value, errors='coerce') if value else None
            elif rule.data_type == "url":
                # Ensure URL is absolute
                if value and not value.startswith(('http://', 'https://')):
                    value = urllib.parse.urljoin(self.current_url, value)
            
            # Apply validation
            if rule.validation_regex and value:
                if not re.match(rule.validation_regex, str(value)):
                    value = rule.default_value
            
            # Apply transformation function
            if rule.transformation_function and value:
                value = rule.transformation_function(value)
            
            return value if value else rule.default_value
            
        except Exception as e:
            logger.warning(f"Data extraction failed for {rule.field_name}: {str(e)}")
            return rule.default_value
    
    def scrape_target(self, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """
        Scrape single target with advanced configuration
        كشط هدف واحد مع التكوين المتقدم
        """
        self.current_url = target.url
        session = self.create_scraping_session(target.profile)
        extracted_data = []
        
        try:
            # Apply request delay
            delay = random.uniform(*target.profile.request_delay_range)
            time.sleep(delay)
            
            # Make request with retries
            response = None
            for attempt in range(target.profile.retry_attempts):
                try:
                    start_time = time.time()
                    response = session.get(target.url, timeout=target.profile.timeout)
                    response_time = time.time() - start_time
                    
                    # Update performance stats
                    self.performance_stats["total_requests"] += 1
                    self.performance_stats["average_response_time"] = (
                        (self.performance_stats["average_response_time"] * (self.performance_stats["total_requests"] - 1) + response_time) / 
                        self.performance_stats["total_requests"]
                    )
                    
                    if response.status_code == 200:
                        self.performance_stats["successful_requests"] += 1
                        break
                    else:
                        logger.warning(f"HTTP {response.status_code} for {target.url}, attempt {attempt + 1}")
                        
                except Exception as e:
                    logger.warning(f"Request failed for {target.url}, attempt {attempt + 1}: {str(e)}")
                    if attempt < target.profile.retry_attempts - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
            
            if not response or response.status_code != 200:
                self.performance_stats["failed_requests"] += 1
                return []
            
            # Parse content based on extraction mode
            if target.profile.extraction_mode == DataExtractionMode.STRUCTURED:
                soup = BeautifulSoup(response.content, 'html.parser')
                extracted_data = self._extract_structured_data(soup, target)
            elif target.profile.extraction_mode == DataExtractionMode.SEMI_STRUCTURED:
                soup = BeautifulSoup(response.content, 'html.parser')
                extracted_data = self._extract_semi_structured_data(soup, target)
            elif target.profile.extraction_mode == DataExtractionMode.UNSTRUCTURED:
                extracted_data = self._extract_unstructured_data(response.text, target)
            elif target.profile.extraction_mode == DataExtractionMode.MIXED:
                soup = BeautifulSoup(response.content, 'html.parser')
                extracted_data = self._extract_mixed_data(soup, response.text, target)
            
            # Apply post-processing
            if target.post_processing_function:
                extracted_data = target.post_processing_function(extracted_data)
            
            # Update performance stats
            self.performance_stats["total_data_points"] += len(extracted_data)
            
            logger.info(f"Scraped {len(extracted_data)} items from {target.url}")
            return extracted_data
            
        except Exception as e:
            self.performance_stats["failed_requests"] += 1
            logger.error(f"Scraping failed for {target.url}: {str(e)}")
            return []
        
        finally:
            session.close()
    
    def _extract_structured_data(self, soup: BeautifulSoup, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """
        Extract structured data using CSS selectors
        استخراج البيانات المنظمة باستخدام محددات CSS
        """
        extracted_items = []
        
        try:
            # Find container elements
            container_rule = next((rule for rule in target.extraction_rules if rule.field_name == "container"), None)
            if container_rule:
                containers = soup.select(container_rule.selector)
            else:
                containers = [soup]  # Use entire page as container
            
            for container in containers:
                item_data = {}
                
                # Extract data for each rule
                for rule in target.extraction_rules:
                    if rule.field_name == "container":
                        continue
                    
                    try:
                        if rule.selector_type == "css":
                            element = container.select_one(rule.selector)
                        elif rule.selector_type == "xpath":
                            # Convert to lxml for xpath support
                            dom = html.fromstring(str(container))
                            elements = dom.xpath(rule.selector)
                            element = elements[0] if elements else None
                        else:
                            element = container.select_one(rule.selector)
                        
                        if element:
                            item_data[rule.field_name] = self.extract_data_from_element(element, rule)
                        else:
                            item_data[rule.field_name] = rule.default_value
                            
                    except Exception as e:
                        logger.warning(f"Failed to extract {rule.field_name}: {str(e)}")
                        item_data[rule.field_name] = rule.default_value
                
                # Add metadata
                item_data['_scraped_at'] = datetime.utcnow().isoformat()
                item_data['_source_url'] = target.url
                item_data['_target_name'] = target.name
                
                # Check if item has required fields
                has_required_data = any(
                    item_data.get(rule.field_name) not in [None, '', rule.default_value]
                    for rule in target.extraction_rules 
                    if rule.required and rule.field_name != "container"
                )
                
                if has_required_data:
                    extracted_items.append(item_data)
        
        except Exception as e:
            logger.error(f"Structured data extraction failed: {str(e)}")
        
        return extracted_items
