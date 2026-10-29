# Service ID: ATS34 - Part 3
# Asynchronous Scraping and Data Management
# الكشط غير المتزامن وإدارة البيانات

import asyncio
import aiohttp
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
import sqlite3
import csv
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import pickle
import xml.etree.ElementTree as ET
from queue import Queue, Empty
import random

logger = logging.getLogger(__name__)

# ==================== SECTION 4: Asynchronous Scraping Engine ====================

class AsyncScrapingManager:
    """
    High-performance asynchronous scraping manager
    مدير الكشط غير المتزامن عالي الأداء
    """
    
    def __init__(self, max_concurrent: int = 20, timeout: int = 30, 
                 rate_limit: float = 1.0):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.rate_limit = rate_limit
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = asyncio.Queue(maxsize=max_concurrent)
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_bytes_downloaded": 0,
            "average_response_time": 0.0,
            "requests_per_second": 0.0,
            "start_time": None
        }
        
        # Initialize rate limiter
        for _ in range(max_concurrent):
            self.rate_limiter.put_nowait(None)
    
    async def create_session(self) -> aiohttp.ClientSession:
        """
        Create optimized aiohttp session
        إنشاء جلسة aiohttp محسنة
        """
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            # Comprehensive headers for stealth
            headers = {
                'User-Agent': random.choice([
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
        
        return self.session
    
    async def scrape_url(self, url: str, target_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape single URL asynchronously
        كشط رابط واحد بشكل غير متزامن
        """
        async with self.semaphore:
            # Rate limiting
            await self.rate_limiter.get()
            
            session = await self.create_session()
            start_time = time.time()
            
            try:
                # Apply rate limiting delay
                await asyncio.sleep(self.rate_limit)
                
                async with session.get(
                    url,
                    headers=target_config.get("headers", {}),
                    cookies=target_config.get("cookies", {})
                ) as response:
                    
                    response_time = time.time() - start_time
                    content_length = int(response.headers.get('content-length', 0))
                    
                    # Update statistics
                    self.stats["total_requests"] += 1
                    self.stats["total_bytes_downloaded"] += content_length
                    
                    # Update average response time
                    current_avg = self.stats["average_response_time"]
                    total_requests = self.stats["total_requests"]
                    self.stats["average_response_time"] = (
                        (current_avg * (total_requests - 1) + response_time) / total_requests
                    )
                    
                    if response.status == 200:
                        self.stats["successful_requests"] += 1
                        content = await response.text()
                        
                        # Parse and extract data
                        soup = BeautifulSoup(content, 'html.parser')
                        extracted_data = self._extract_data_async(soup, target_config, url)
                        
                        return {
                            "status": "success",
                            "url": url,
                            "data": extracted_data,
                            "response_time": response_time,
                            "content_length": content_length
                        }
                    else:
                        self.stats["failed_requests"] += 1
                        logger.warning(f"HTTP {response.status} for {url}")
                        return {
                            "status": "failed",
                            "url": url,
                            "error": f"HTTP {response.status}",
                            "response_time": response_time
                        }
            
            except asyncio.TimeoutError:
                self.stats["failed_requests"] += 1
                logger.error(f"Timeout for {url}")
                return {
                    "status": "timeout",
                    "url": url,
                    "error": "Request timeout"
                }
            
            except Exception as e:
                self.stats["failed_requests"] += 1
                logger.error(f"Async scraping failed for {url}: {str(e)}")
                return {
                    "status": "error",
                    "url": url,
                    "error": str(e)
                }
            
            finally:
                # Return rate limiter token
                self.rate_limiter.put_nowait(None)
    
    def _extract_data_async(self, soup: BeautifulSoup, target_config: Dict[str, Any], 
                           url: str) -> List[Dict[str, Any]]:
        """
        Extract data from BeautifulSoup object
        استخراج البيانات من كائن BeautifulSoup
        """
        extracted_items = []
        extraction_rules = target_config.get("extraction_rules", [])
        
        try:
            # Find containers
            container_selector = target_config.get("container_selector")
            if container_selector:
                containers = soup.select(container_selector)
            else:
                containers = [soup]
            
            for container in containers:
                item_data = {}
                
                # Extract data for each rule
                for rule in extraction_rules:
                    field_name = rule.get("field_name")
                    selector = rule.get("selector")
                    extraction_method = rule.get("extraction_method", "text")
                    
                    if not field_name or not selector:
                        continue
                    
                    try:
                        element = container.select_one(selector)
                        if element:
                            if extraction_method == "text":
                                value = element.get_text(strip=True)
                            elif extraction_method == "href":
                                value = element.get('href', '')
                            elif extraction_method == "src":
                                value = element.get('src', '')
                            elif extraction_method == "attribute":
                                attr_name = rule.get("attribute_name", "")
                                value = element.get(attr_name, '')
                            else:
                                value = element.get_text(strip=True)
                            
                            # Apply data transformation
                            data_type = rule.get("data_type", "string")
                            if data_type == "integer" and value:
                                value = int(''.join(filter(str.isdigit, str(value)))) if str(value).strip() else 0
                            elif data_type == "float" and value:
                                value = float(''.join(c for c in str(value) if c.isdigit() or c == '.')) if str(value).strip() else 0.0
                            
                            item_data[field_name] = value
                        else:
                            item_data[field_name] = rule.get("default_value", "")
                    
                    except Exception as e:
                        logger.warning(f"Failed to extract {field_name}: {str(e)}")
                        item_data[field_name] = rule.get("default_value", "")
                
                # Add metadata
                item_data['_scraped_at'] = datetime.utcnow().isoformat()
                item_data['_source_url'] = url
                
                # Only add if we have meaningful data
                if any(value for key, value in item_data.items() if not key.startswith('_') and value):
                    extracted_items.append(item_data)
        
        except Exception as e:
            logger.error(f"Async data extraction failed: {str(e)}")
        
        return extracted_items
    
    async def scrape_multiple_urls(self, url_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently
        كشط روابط متعددة بشكل متزامن
        """
        if not self.stats["start_time"]:
            self.stats["start_time"] = time.time()
        
        tasks = []
        for config in url_configs:
            url = config.get("url")
            if url:
                task = self.scrape_url(url, config)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate requests per second
        elapsed_time = time.time() - self.stats["start_time"]
        if elapsed_time > 0:
            self.stats["requests_per_second"] = self.stats["total_requests"] / elapsed_time
        
        # Process results
        successful_results = []
        for result in results:
            if isinstance(result, dict) and result.get("status") == "success":
                successful_results.extend(result.get("data", []))
            elif isinstance(result, Exception):
                logger.error(f"Task failed with exception: {str(result)}")
        
        logger.info(f"Async scraping completed: {len(successful_results)} items from {len(url_configs)} URLs")
        return successful_results
    
    async def close_session(self) -> None:
        """
        Close aiohttp session
        إغلاق جلسة aiohttp
        """
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Async session closed")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get scraping performance statistics
        الحصول على إحصائيات أداء الكشط
        """
        stats = self.stats.copy()
        
        if stats["total_requests"] > 0:
            stats["success_rate"] = (stats["successful_requests"] / stats["total_requests"]) * 100
            stats["failure_rate"] = (stats["failed_requests"] / stats["total_requests"]) * 100
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
        
        if stats["start_time"]:
            elapsed_time = time.time() - stats["start_time"]
            stats["total_runtime"] = elapsed_time
        
        return stats

# ==================== SECTION 5: Data Management and Export ====================

class ScrapingDataManager:
    """
    Comprehensive data management and export system
    نظام إدارة وتصدير البيانات الشامل
    """
    
    def __init__(self, workspace_path: str = "./scraping_data"):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Create data structure
        (self.workspace_path / "raw").mkdir(exist_ok=True)
        (self.workspace_path / "processed").mkdir(exist_ok=True)
        (self.workspace_path / "exports").mkdir(exist_ok=True)
        (self.workspace_path / "backups").mkdir(exist_ok=True)
        
        self.data_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.processing_history: List[Dict[str, Any]] = []
        
        # Initialize database
        self.db_path = self.workspace_path / "scraping_data.db"
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """
        Initialize SQLite database for data storage
        تهيئة قاعدة بيانات SQLite لتخزين البيانات
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create main data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scraped_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        source_url TEXT NOT NULL,
                        target_name TEXT,
                        data_json TEXT NOT NULL,
                        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        data_hash TEXT,
                        quality_score REAL
                    )
                ''')
                
                # Create sessions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scraping_sessions (
                        session_id TEXT PRIMARY KEY,
                        session_name TEXT,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        total_items INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 0.0,
                        configuration_json TEXT
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON scraped_data(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_url ON scraped_data(source_url)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON scraped_data(scraped_at)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
    
    def store_scraped_data(self, session_id: str, data: List[Dict[str, Any]], 
                          session_config: Dict[str, Any] = None) -> bool:
        """
        Store scraped data in database
        تخزين البيانات المكشوطة في قاعدة البيانات
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Store session info
                if session_config:
                    cursor.execute('''
                        INSERT OR REPLACE INTO scraping_sessions 
                        (session_id, session_name, start_time, configuration_json)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        session_id,
                        session_config.get("name", f"Session {session_id}"),
                        datetime.utcnow(),
                        json.dumps(session_config)
                    ))
                
                # Store data items
                for item in data:
                    data_json = json.dumps(item, default=str)
                    data_hash = hashlib.md5(data_json.encode()).hexdigest()
                    
                    cursor.execute('''
                        INSERT INTO scraped_data 
                        (session_id, source_url, target_name, data_json, data_hash)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        session_id,
                        item.get('_source_url', ''),
                        item.get('_target_name', ''),
                        data_json,
                        data_hash
                    ))
                
                # Update session totals
                cursor.execute('''
                    UPDATE scraping_sessions 
                    SET total_items = (
                        SELECT COUNT(*) FROM scraped_data WHERE session_id = ?
                    ),
                    end_time = ?
                    WHERE session_id = ?
                ''', (session_id, datetime.utcnow(), session_id))
                
                conn.commit()
                logger.info(f"Stored {len(data)} items for session {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Data storage failed: {str(e)}")
            return False
    
    def retrieve_session_data(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve data for specific session
        استرداد البيانات لجلسة محددة
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT data_json FROM scraped_data 
                    WHERE session_id = ? 
                    ORDER BY scraped_at
                ''', (session_id,))
                
                results = cursor.fetchall()
                data = []
                
                for row in results:
                    try:
                        item_data = json.loads(row[0])
                        data.append(item_data)
                    except json.JSONDecodeError:
                        continue
                
                logger.info(f"Retrieved {len(data)} items for session {session_id}")
                return data
                
        except Exception as e:
            logger.error(f"Data retrieval failed: {str(e)}")
            return []
    
    def export_to_csv(self, session_id: str, filename: str = None) -> bool:
        """
        Export session data to CSV
        تصدير بيانات الجلسة إلى CSV
        """
        try:
            data = self.retrieve_session_data(session_id)
            if not data:
                logger.warning(f"No data found for session {session_id}")
                return False
            
            df = pd.DataFrame(data)
            
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{session_id}_{timestamp}.csv"
            
            filepath = self.workspace_path / "exports" / filename
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            logger.info(f"Data exported to CSV: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"CSV export failed: {str(e)}")
            return False
    
    def export_to_json(self, session_id: str, filename: str = None, 
                      pretty_print: bool = True) -> bool:
        """
        Export session data to JSON
        تصدير بيانات الجلسة إلى JSON
        """
        try:
            data = self.retrieve_session_data(session_id)
            if not data:
                logger.warning(f"No data found for session {session_id}")
                return False
            
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{session_id}_{timestamp}.json"
            
            filepath = self.workspace_path / "exports" / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                else:
                    json.dump(data, f, ensure_ascii=False, default=str)
            
            logger.info(f"Data exported to JSON: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            return False
    
    def export_to_excel(self, session_id: str, filename: str = None) -> bool:
        """
        Export session data to Excel
        تصدير بيانات الجلسة إلى Excel
        """
        try:
            data = self.retrieve_session_data(session_id)
            if not data:
                logger.warning(f"No data found for session {session_id}")
                return False
            
            df = pd.DataFrame(data)
            
            if not filename:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                filename = f"{session_id}_{timestamp}.xlsx"
            
            filepath = self.workspace_path / "exports" / filename
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='ScrapedData', index=False)
            
            logger.info(f"Data exported to Excel: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Excel export failed: {str(e)}")
            return False
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive session statistics
        الحصول على إحصائيات الجلسة الشاملة
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get session info
                cursor.execute('''
                    SELECT session_name, start_time, end_time, total_items
                    FROM scraping_sessions WHERE session_id = ?
                ''', (session_id,))
                
                session_info = cursor.fetchone()
                if not session_info:
                    return {"status": "session_not_found"}
                
                # Get data statistics
                cursor.execute('''
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT source_url) as unique_sources,
                           MIN(scraped_at) as first_scraped,
                           MAX(scraped_at) as last_scraped
                    FROM scraped_data WHERE session_id = ?
                ''', (session_id,))
                
                data_stats = cursor.fetchone()
                
                stats = {
                    "session_id": session_id,
                    "session_name": session_info[0],
                    "start_time": session_info[1],
                    "end_time": session_info[2],
                    "total_items": session_info[3],
                    "total_records": data_stats[0],
                    "unique_sources": data_stats[1],
                    "first_scraped": data_stats[2],
                    "last_scraped": data_stats[3]
                }
                
                # Calculate duration
                if session_info[1] and session_info[2]:
                    start = datetime.fromisoformat(session_info[1])
                    end = datetime.fromisoformat(session_info[2])
                    duration = end - start
                    stats["duration_seconds"] = duration.total_seconds()
                
                return stats
                
        except Exception as e:
            logger.error(f"Statistics retrieval failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Clean up old scraping sessions
        تنظيف جلسات الكشط القديمة
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get sessions to delete
                cursor.execute('''
                    SELECT session_id FROM scraping_sessions 
                    WHERE end_time < ? OR end_time IS NULL
                ''', (cutoff_date,))
                
                sessions_to_delete = [row[0] for row in cursor.fetchall()]
                
                # Delete data
                cursor.execute('''
                    DELETE FROM scraped_data 
                    WHERE session_id IN (
                        SELECT session_id FROM scraping_sessions 
                        WHERE end_time < ? OR end_time IS NULL
                    )
                ''', (cutoff_date,))
                
                # Delete sessions
                cursor.execute('''
                    DELETE FROM scraping_sessions 
                    WHERE end_time < ? OR end_time IS NULL
                ''', (cutoff_date,))
                
                conn.commit()
                
                logger.info(f"Cleaned up {len(sessions_to_delete)} old sessions")
                return len(sessions_to_delete)
                
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            return 0
