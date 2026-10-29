# Service ID: PYL94 - Part 2
# Advanced Web Scraping Components
# مكونات كشط المواقع المتقدمة

import asyncio
import aiohttp
import json
import csv
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import sqlite3
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import random
import hashlib
import pickle

logger = logging.getLogger(__name__)

# ==================== SECTION 2: Selenium-based Scraping ====================

class SeleniumScraper:
    """
    Selenium-based web scraping for JavaScript-heavy sites
    كشط المواقع باستخدام Selenium للمواقع الثقيلة بـ JavaScript
    """
    
    def __init__(self, headless: bool = True, window_size: tuple = (1920, 1080)):
        self.headless = headless
        self.window_size = window_size
        self.drivers: Dict[str, webdriver.Chrome] = {}
        self.driver_options = self._setup_chrome_options()
    
    def _setup_chrome_options(self) -> Options:
        """
        Setup Chrome driver options
        إعداد خيارات تشغيل Chrome
        """
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        # Random user agent
        try:
            ua = UserAgent()
            options.add_argument(f'--user-agent={ua.random}')
        except:
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        return options
    
    def get_driver(self, session_id: str = "default") -> webdriver.Chrome:
        """
        Get or create Chrome driver instance
        الحصول على أو إنشاء مثيل تشغيل Chrome
        """
        if session_id not in self.drivers:
            try:
                driver = webdriver.Chrome(options=self.driver_options)
                driver.set_page_load_timeout(30)
                driver.implicitly_wait(10)
                self.drivers[session_id] = driver
                logger.info(f"Chrome driver created for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to create Chrome driver: {str(e)}")
                raise
        
        return self.drivers[session_id]
    
    def scrape_target(self, target, driver_session: str = "default") -> List[Dict[str, Any]]:
        """
        Scrape target using Selenium
        كشط الهدف باستخدام Selenium
        """
        driver = self.get_driver(driver_session)
        extracted_data = []
        
        try:
            # Navigate to URL
            logger.info(f"Navigating to: {target.url}")
            driver.get(target.url)
            
            # Wait for page load
            WebDriverWait(driver, target.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait time for dynamic content
            time.sleep(target.wait_time)
            
            # Extract data from current page
            page_data = self._extract_selenium_data(driver, target)
            extracted_data.extend(page_data)
            
            # Handle pagination if specified
            if target.pagination_selector and target.max_pages > 1:
                pagination_data = self._handle_selenium_pagination(driver, target)
                extracted_data.extend(pagination_data)
                
            logger.info(f"Extracted {len(extracted_data)} items from {target.url}")
        
        except TimeoutException:
            logger.error(f"Timeout loading page: {target.url}")
        except WebDriverException as e:
            logger.error(f"WebDriver error for {target.url}: {str(e)}")
        except Exception as e:
            logger.error(f"Selenium scraping failed for {target.url}: {str(e)}")
        
        return extracted_data
    
    def _extract_selenium_data(self, driver: webdriver.Chrome, target) -> List[Dict[str, Any]]:
        """
        Extract data using Selenium WebDriver
        استخراج البيانات باستخدام Selenium WebDriver
        """
        extracted_items = []
        
        try:
            # Find containers
            if 'container' in target.selectors:
                containers = driver.find_elements(By.CSS_SELECTOR, target.selectors['container'])
            else:
                containers = [driver]  # Use entire page
            
            for container in containers:
                item_data = {}
                
                # Extract data for each selector
                for field_name, selector in target.selectors.items():
                    if field_name == 'container':
                        continue
                    
                    try:
                        if hasattr(container, 'find_element'):
                            element = container.find_element(By.CSS_SELECTOR, selector)
                        else:
                            element = driver.find_element(By.CSS_SELECTOR, selector)
                        
                        # Extract data based on selector type
                        if selector.endswith('@href'):
                            item_data[field_name] = element.get_attribute('href') or ''
                        elif selector.endswith('@src'):
                            item_data[field_name] = element.get_attribute('src') or ''
                        elif '@' in selector:
                            attr = selector.split('@')[-1]
                            item_data[field_name] = element.get_attribute(attr) or ''
                        else:
                            item_data[field_name] = element.text.strip()
                    
                    except Exception:
                        item_data[field_name] = ""
                
                # Add metadata
                item_data['_scraped_at'] = datetime.utcnow().isoformat()
                item_data['_source_url'] = target.url
                item_data['_target_name'] = target.name
                
                if any(value for value in item_data.values() if value):
                    extracted_items.append(item_data)
        
        except Exception as e:
            logger.error(f"Selenium data extraction failed: {str(e)}")
        
        return extracted_items
    
    def _handle_selenium_pagination(self, driver: webdriver.Chrome, target) -> List[Dict[str, Any]]:
        """
        Handle pagination using Selenium
        معالجة التصفح باستخدام Selenium
        """
        all_data = []
        current_page = 2
        
        try:
            while current_page <= target.max_pages:
                try:
                    # Find and click next page button
                    next_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, target.pagination_selector))
                    )
                    
                    # Scroll to button and click
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    time.sleep(1)
                    next_button.click()
                    
                    # Wait for new content to load
                    time.sleep(target.wait_time)
                    
                    # Extract data from new page
                    page_data = self._extract_selenium_data(driver, target)
                    
                    if not page_data:  # No more data
                        logger.info("No more data found, stopping pagination")
                        break
                    
                    all_data.extend(page_data)
                    current_page += 1
                    logger.info(f"Scraped page {current_page-1}, got {len(page_data)} items")
                
                except TimeoutException:
                    logger.info("No more pages found")
                    break
                except Exception as e:
                    logger.error(f"Pagination error: {str(e)}")
                    break
        
        except Exception as e:
            logger.error(f"Selenium pagination failed: {str(e)}")
        
        return all_data
    
    def execute_javascript(self, driver_session: str, script: str) -> Any:
        """
        Execute JavaScript in browser
        تنفيذ JavaScript في المتصفح
        """
        try:
            driver = self.get_driver(driver_session)
            return driver.execute_script(script)
        except Exception as e:
            logger.error(f"JavaScript execution failed: {str(e)}")
            return None
    
    def take_screenshot(self, driver_session: str, filename: str) -> bool:
        """
        Take screenshot of current page
        أخذ لقطة شاشة للصفحة الحالية
        """
        try:
            driver = self.get_driver(driver_session)
            driver.save_screenshot(filename)
            logger.info(f"Screenshot saved: {filename}")
            return True
        except Exception as e:
            logger.error(f"Screenshot failed: {str(e)}")
            return False
    
    def close_driver(self, session_id: str = "default") -> None:
        """
        Close specific driver session
        إغلاق جلسة تشغيل محددة
        """
        if session_id in self.drivers:
            try:
                self.drivers[session_id].quit()
                del self.drivers[session_id]
                logger.info(f"Driver closed: {session_id}")
            except Exception as e:
                logger.error(f"Error closing driver {session_id}: {str(e)}")
    
    def close_all_drivers(self) -> None:
        """
        Close all driver sessions
        إغلاق جميع جلسات التشغيل
        """
        for session_id in list(self.drivers.keys()):
            self.close_driver(session_id)

# ==================== SECTION 3: Asynchronous Scraping ====================

class AsyncScraper:
    """
    Asynchronous web scraping for high-performance data extraction
    كشط المواقع غير المتزامن لاستخراج البيانات عالي الأداء
    """
    
    def __init__(self, max_concurrent: int = 10, timeout: int = 30):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def create_session(self) -> aiohttp.ClientSession:
        """
        Create aiohttp session with proper configuration
        إنشاء جلسة aiohttp مع التكوين المناسب
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            
            headers = {
                'User-Agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                ])
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
        
        return self.session
    
    async def scrape_target(self, target) -> List[Dict[str, Any]]:
        """
        Scrape single target asynchronously
        كشط هدف واحد بشكل غير متزامن
        """
        async with self.semaphore:
            session = await self.create_session()
            
            try:
                # Add delay for rate limiting
                await asyncio.sleep(target.wait_time)
                
                async with session.get(
                    target.url,
                    headers=target.headers,
                    cookies=target.cookies
                ) as response:
                    if response.status == 200:
                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')
                        data = self._extract_async_data(soup, target)
                        logger.info(f"Async scraped {len(data)} items from {target.url}")
                        return data
                    else:
                        logger.error(f"HTTP {response.status} for {target.url}")
                        return []
            
            except asyncio.TimeoutError:
                logger.error(f"Timeout for {target.url}")
                return []
            except Exception as e:
                logger.error(f"Async scraping failed for {target.url}: {str(e)}")
                return []
    
    def _extract_async_data(self, soup: BeautifulSoup, target) -> List[Dict[str, Any]]:
        """
        Extract data from BeautifulSoup object
        استخراج البيانات من كائن BeautifulSoup
        """
        extracted_items = []
        
        try:
            # Find containers
            if 'container' in target.selectors:
                containers = soup.select(target.selectors['container'])
            else:
                containers = [soup]
            
            for container in containers:
                item_data = {}
                
                # Extract data for each selector
                for field_name, selector in target.selectors.items():
                    if field_name == 'container':
                        continue
                    
                    try:
                        element = container.select_one(selector)
                        if element:
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
                    except Exception:
                        item_data[field_name] = ""
                
                # Add metadata
                item_data['_scraped_at'] = datetime.utcnow().isoformat()
                item_data['_source_url'] = target.url
                item_data['_target_name'] = target.name
                
                if any(value for value in item_data.values() if value):
                    extracted_items.append(item_data)
        
        except Exception as e:
            logger.error(f"Async data extraction failed: {str(e)}")
        
        return extracted_items
    
    async def scrape_multiple_targets(self, targets: List) -> List[Dict[str, Any]]:
        """
        Scrape multiple targets concurrently
        كشط أهداف متعددة بشكل متزامن
        """
        tasks = [self.scrape_target(target) for target in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_data = []
        for result in results:
            if isinstance(result, list):
                all_data.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Task failed: {str(result)}")
        
        logger.info(f"Async scraping completed: {len(all_data)} total items")
        return all_data
    
    async def close_session(self) -> None:
        """
        Close aiohttp session
        إغلاق جلسة aiohttp
        """
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Async session closed")

# ==================== SECTION 4: Data Processing and Analysis ====================

class ScrapedDataProcessor:
    """
    Process and analyze scraped data
    معالجة وتحليل البيانات المكشوطة
    """
    
    def __init__(self):
        self.data_cache: List[Dict[str, Any]] = []
        self.processed_data: Optional[pd.DataFrame] = None
    
    def load_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Load scraped data for processing
        تحميل البيانات المكشوطة للمعالجة
        """
        self.data_cache = data
        self.processed_data = pd.DataFrame(data) if data else pd.DataFrame()
        logger.info(f"Loaded {len(data)} records for processing")
    
    def clean_data(self) -> pd.DataFrame:
        """
        Clean and normalize scraped data
        تنظيف وتطبيع البيانات المكشوطة
        """
        if self.processed_data is None or self.processed_data.empty:
            logger.warning("No data to clean")
            return pd.DataFrame()
        
        df = self.processed_data.copy()
        
        try:
            # Remove empty rows
            df = df.dropna(how='all')
            
            # Remove duplicate rows
            initial_count = len(df)
            df = df.drop_duplicates()
            removed_duplicates = initial_count - len(df)
            
            # Clean text fields
            text_columns = df.select_dtypes(include=['object']).columns
            for col in text_columns:
                if col not in ['_scraped_at', '_source_url', '_target_name']:
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].replace('', None)
            
            # Convert scraped_at to datetime
            if '_scraped_at' in df.columns:
                df['_scraped_at'] = pd.to_datetime(df['_scraped_at'])
            
            logger.info(f"Data cleaned: {len(df)} records, {removed_duplicates} duplicates removed")
            self.processed_data = df
            return df
        
        except Exception as e:
            logger.error(f"Data cleaning failed: {str(e)}")
            return self.processed_data
    
    def validate_data(self) -> Dict[str, Any]:
        """
        Validate data quality and completeness
        التحقق من جودة واكتمال البيانات
        """
        if self.processed_data is None or self.processed_data.empty:
            return {"status": "no_data", "issues": ["No data available"]}
        
        df = self.processed_data
        validation_report = {
            "total_records": len(df),
            "columns": list(df.columns),
            "missing_data": {},
            "data_types": {},
            "issues": [],
            "quality_score": 0.0
        }
        
        try:
            # Check missing data
            for col in df.columns:
                missing_count = df[col].isnull().sum()
                missing_percentage = (missing_count / len(df)) * 100
                validation_report["missing_data"][col] = {
                    "count": int(missing_count),
                    "percentage": round(missing_percentage, 2)
                }
                
                if missing_percentage > 50:
                    validation_report["issues"].append(f"High missing data in {col}: {missing_percentage:.1f}%")
            
            # Check data types
            for col in df.columns:
                validation_report["data_types"][col] = str(df[col].dtype)
            
            # Calculate quality score
            total_cells = len(df) * len(df.columns)
            non_null_cells = df.count().sum()
            validation_report["quality_score"] = round((non_null_cells / total_cells) * 100, 2)
            
            logger.info(f"Data validation completed: {validation_report['quality_score']}% quality score")
            return validation_report
        
        except Exception as e:
            logger.error(f"Data validation failed: {str(e)}")
            validation_report["issues"].append(f"Validation error: {str(e)}")
            return validation_report
    
    def analyze_data(self) -> Dict[str, Any]:
        """
        Perform basic data analysis
        إجراء تحليل أساسي للبيانات
        """
        if self.processed_data is None or self.processed_data.empty:
            return {"status": "no_data"}
        
        df = self.processed_data
        analysis = {
            "summary": {
                "total_records": len(df),
                "columns": len(df.columns),
                "memory_usage": df.memory_usage(deep=True).sum()
            },
            "column_stats": {},
            "source_distribution": {},
            "temporal_analysis": {}
        }
        
        try:
            # Column statistics
            for col in df.columns:
                if col.startswith('_'):
                    continue
                
                col_stats = {
                    "type": str(df[col].dtype),
                    "non_null_count": int(df[col].count()),
                    "unique_values": int(df[col].nunique())
                }
                
                if df[col].dtype in ['object']:
                    col_stats["top_values"] = df[col].value_counts().head(5).to_dict()
                elif df[col].dtype in ['int64', 'float64']:
                    col_stats["statistics"] = {
                        "mean": float(df[col].mean()) if not df[col].empty else 0,
                        "median": float(df[col].median()) if not df[col].empty else 0,
                        "std": float(df[col].std()) if not df[col].empty else 0
                    }
                
                analysis["column_stats"][col] = col_stats
            
            # Source distribution
            if '_source_url' in df.columns:
                analysis["source_distribution"] = df['_source_url'].value_counts().to_dict()
            
            # Temporal analysis
            if '_scraped_at' in df.columns:
                df['_scraped_at'] = pd.to_datetime(df['_scraped_at'])
                analysis["temporal_analysis"] = {
                    "date_range": {
                        "start": df['_scraped_at'].min().isoformat(),
                        "end": df['_scraped_at'].max().isoformat()
                    },
                    "hourly_distribution": df['_scraped_at'].dt.hour.value_counts().to_dict()
                }
            
            logger.info("Data analysis completed")
            return analysis
        
        except Exception as e:
            logger.error(f"Data analysis failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def filter_data(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply filters to processed data
        تطبيق المرشحات على البيانات المعالجة
        """
        if self.processed_data is None or self.processed_data.empty:
            return pd.DataFrame()
        
        df = self.processed_data.copy()
        
        try:
            for column, filter_value in filters.items():
                if column not in df.columns:
                    continue
                
                if isinstance(filter_value, dict):
                    # Range filter
                    if 'min' in filter_value:
                        df = df[df[column] >= filter_value['min']]
                    if 'max' in filter_value:
                        df = df[df[column] <= filter_value['max']]
                elif isinstance(filter_value, list):
                    # Multiple values filter
                    df = df[df[column].isin(filter_value)]
                else:
                    # Exact match filter
                    df = df[df[column] == filter_value]
            
            logger.info(f"Data filtered: {len(df)} records remaining")
            return df
        
        except Exception as e:
            logger.error(f"Data filtering failed: {str(e)}")
            return self.processed_data
