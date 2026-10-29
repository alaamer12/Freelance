# Service ID: ATS34 - Part 2
# Advanced Web Scraping Features and Intelligence
# ميزات الكشط المتقدمة والذكاء الاصطناعي

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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import pickle
import sqlite3
from lxml import html
import re
import csv
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# ==================== SECTION 2: Intelligent Data Processing ====================

class DataIntelligenceEngine:
    """
    Intelligent data processing and analysis engine
    محرك المعالجة والتحليل الذكي للبيانات
    """
    
    def __init__(self):
        self.data_patterns: Dict[str, Any] = {}
        self.quality_metrics: Dict[str, float] = {}
        self.anomaly_detection_rules: List[Dict[str, Any]] = []
    
    def analyze_data_quality(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze scraped data quality
        تحليل جودة البيانات المكشوطة
        """
        if not data:
            return {"status": "no_data", "quality_score": 0.0}
        
        df = pd.DataFrame(data)
        
        quality_report = {
            "total_records": len(df),
            "total_fields": len(df.columns),
            "completeness": {},
            "consistency": {},
            "accuracy": {},
            "quality_score": 0.0,
            "recommendations": []
        }
        
        try:
            # Completeness analysis
            for col in df.columns:
                if not col.startswith('_'):
                    non_null_count = df[col].count()
                    completeness_rate = (non_null_count / len(df)) * 100
                    quality_report["completeness"][col] = {
                        "rate": round(completeness_rate, 2),
                        "missing_count": len(df) - non_null_count
                    }
                    
                    if completeness_rate < 70:
                        quality_report["recommendations"].append(
                            f"Field '{col}' has low completeness ({completeness_rate:.1f}%) - check extraction rules"
                        )
            
            # Consistency analysis
            for col in df.columns:
                if not col.startswith('_') and df[col].dtype == 'object':
                    unique_patterns = df[col].astype(str).apply(self._extract_pattern).value_counts()
                    consistency_score = (unique_patterns.iloc[0] / len(df)) * 100 if len(unique_patterns) > 0 else 100
                    quality_report["consistency"][col] = {
                        "score": round(consistency_score, 2),
                        "pattern_count": len(unique_patterns)
                    }
                    
                    if consistency_score < 80 and len(unique_patterns) > 5:
                        quality_report["recommendations"].append(
                            f"Field '{col}' shows inconsistent patterns - consider data normalization"
                        )
            
            # Calculate overall quality score
            completeness_scores = [metrics["rate"] for metrics in quality_report["completeness"].values()]
            consistency_scores = [metrics["score"] for metrics in quality_report["consistency"].values()]
            
            avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
            avg_consistency = sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0
            
            quality_report["quality_score"] = round((avg_completeness + avg_consistency) / 2, 2)
            
            logger.info(f"Data quality analysis completed: {quality_report['quality_score']}% quality score")
            return quality_report
            
        except Exception as e:
            logger.error(f"Data quality analysis failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def _extract_pattern(self, value: str) -> str:
        """
        Extract data pattern from value
        استخراج نمط البيانات من القيمة
        """
        if pd.isna(value) or value == '':
            return "empty"
        
        value = str(value)
        
        # Email pattern
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            return "email"
        
        # URL pattern
        if re.match(r'^https?://', value):
            return "url"
        
        # Phone pattern
        if re.match(r'^[\+]?[1-9]?[\d\s\-\(\)]{7,15}$', value):
            return "phone"
        
        # Date pattern
        if re.match(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}', value):
            return "date"
        
        # Number pattern
        if re.match(r'^\d+\.?\d*$', value):
            return "number"
        
        # Text pattern based on length
        if len(value) < 20:
            return "short_text"
        elif len(value) < 100:
            return "medium_text"
        else:
            return "long_text"
    
    def detect_anomalies(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect anomalies in scraped data
        كشف الشذوذ في البيانات المكشوطة
        """
        anomalies = []
        
        if not data:
            return anomalies
        
        df = pd.DataFrame(data)
        
        try:
            for col in df.columns:
                if col.startswith('_'):
                    continue
                
                # Check for outliers in numeric data
                if df[col].dtype in ['int64', 'float64']:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    
                    outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                    for idx, row in outliers.iterrows():
                        anomalies.append({
                            "type": "outlier",
                            "field": col,
                            "value": row[col],
                            "record_index": idx,
                            "description": f"Value {row[col]} is outside normal range [{lower_bound:.2f}, {upper_bound:.2f}]"
                        })
                
                # Check for unusual text patterns
                elif df[col].dtype == 'object':
                    value_lengths = df[col].astype(str).str.len()
                    mean_length = value_lengths.mean()
                    std_length = value_lengths.std()
                    
                    unusual_lengths = df[abs(value_lengths - mean_length) > 3 * std_length]
                    for idx, row in unusual_lengths.iterrows():
                        anomalies.append({
                            "type": "unusual_length",
                            "field": col,
                            "value": row[col],
                            "record_index": idx,
                            "description": f"Text length {len(str(row[col]))} is unusual (mean: {mean_length:.1f})"
                        })
            
            logger.info(f"Anomaly detection completed: {len(anomalies)} anomalies found")
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {str(e)}")
            return []
    
    def suggest_improvements(self, target, extraction_results: List[Dict[str, Any]]) -> List[str]:
        """
        Suggest improvements for scraping configuration
        اقتراح تحسينات لتكوين الكشط
        """
        suggestions = []
        
        if not extraction_results:
            suggestions.append("No data extracted - check URL accessibility and selector accuracy")
            return suggestions
        
        try:
            df = pd.DataFrame(extraction_results)
            
            # Check extraction rule effectiveness
            for rule in target.extraction_rules:
                if rule.field_name == "container":
                    continue
                
                if rule.field_name in df.columns:
                    success_rate = (df[rule.field_name].count() / len(df)) * 100
                    
                    if success_rate < 50:
                        suggestions.append(
                            f"Rule '{rule.field_name}' has low success rate ({success_rate:.1f}%) - consider updating selector '{rule.selector}'"
                        )
                    elif success_rate < 80:
                        suggestions.append(
                            f"Rule '{rule.field_name}' could be improved ({success_rate:.1f}% success) - verify selector specificity"
                        )
                else:
                    suggestions.append(f"Rule '{rule.field_name}' produced no results - check selector '{rule.selector}'")
            
            # Performance suggestions
            if len(extraction_results) < 5:
                suggestions.append("Low data yield - consider checking pagination or expanding target scope")
            
            # Data quality suggestions
            quality_report = self.analyze_data_quality(extraction_results)
            if quality_report.get("quality_score", 0) < 70:
                suggestions.append("Overall data quality is low - review extraction rules and data validation")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Improvement suggestion failed: {str(e)}")
            return ["Unable to analyze results for improvements"]

# ==================== SECTION 3: Advanced Selenium Automation ====================

class IntelligentSeleniumScraper:
    """
    Intelligent Selenium-based scraping with advanced automation
    كشط ذكي باستخدام Selenium مع الأتمتة المتقدمة
    """
    
    def __init__(self, headless: bool = True, window_size: tuple = (1920, 1080)):
        self.headless = headless
        self.window_size = window_size
        self.drivers: Dict[str, webdriver.Chrome] = {}
        self.page_load_strategies = {}
        self.element_wait_strategies = {}
    
    def create_stealth_driver(self, session_id: str = "default") -> webdriver.Chrome:
        """
        Create stealth Chrome driver with anti-detection measures
        إنشاء تشغيل Chrome خفي مع تدابير مكافحة الكشف
        """
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Stealth options
        options.add_argument(f'--window-size={self.window_size[0]},{self.window_size[1]}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Random user agent
        from fake_useragent import UserAgent
        ua = UserAgent()
        options.add_argument(f'--user-agent={ua.random}')
        
        try:
            driver = webdriver.Chrome(options=options)
            
            # Execute stealth scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": ua.random
            })
            
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            
            self.drivers[session_id] = driver
            logger.info(f"Stealth Chrome driver created: {session_id}")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create stealth driver: {str(e)}")
            raise
    
    def smart_element_wait(self, driver: webdriver.Chrome, selector: str, 
                          wait_type: str = "presence", timeout: int = 10) -> Any:
        """
        Intelligent element waiting with multiple strategies
        انتظار ذكي للعناصر مع استراتيجيات متعددة
        """
        wait = WebDriverWait(driver, timeout)
        
        try:
            if wait_type == "presence":
                return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            elif wait_type == "visible":
                return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
            elif wait_type == "clickable":
                return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            elif wait_type == "all_present":
                return wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
            else:
                return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                
        except Exception as e:
            logger.warning(f"Element wait failed for '{selector}': {str(e)}")
            return None
    
    def handle_dynamic_content(self, driver: webdriver.Chrome, target) -> None:
        """
        Handle dynamic content loading
        معالجة تحميل المحتوى الديناميكي
        """
        try:
            # Wait for initial page load
            time.sleep(2)
            
            # Scroll to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Check for loading indicators
            loading_selectors = [
                '.loading', '.spinner', '.loader', '[data-loading]',
                '.fa-spinner', '.fa-circle-o-notch'
            ]
            
            for selector in loading_selectors:
                try:
                    loading_element = driver.find_element(By.CSS_SELECTOR, selector)
                    if loading_element.is_displayed():
                        # Wait for loading to complete
                        WebDriverWait(driver, 30).until(
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        break
                except:
                    continue
            
            # Handle infinite scroll
            if target.pagination_config and target.pagination_config.get("type") == "infinite_scroll":
                self._handle_infinite_scroll(driver, target.pagination_config)
            
        except Exception as e:
            logger.warning(f"Dynamic content handling failed: {str(e)}")
    
    def _handle_infinite_scroll(self, driver: webdriver.Chrome, pagination_config: Dict[str, Any]) -> None:
        """
        Handle infinite scroll pagination
        معالجة التصفح بالتمرير اللانهائي
        """
        max_scrolls = pagination_config.get("max_scrolls", 10)
        scroll_pause_time = pagination_config.get("scroll_pause", 2)
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        scrolls = 0
        
        while scrolls < max_scrolls:
            # Scroll down to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(scroll_pause_time)
            
            # Check if new content loaded
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            
            last_height = new_height
            scrolls += 1
            
            logger.info(f"Infinite scroll: {scrolls}/{max_scrolls}")
    
    def extract_with_javascript(self, driver: webdriver.Chrome, 
                              extraction_script: str) -> List[Dict[str, Any]]:
        """
        Extract data using custom JavaScript
        استخراج البيانات باستخدام JavaScript مخصص
        """
        try:
            result = driver.execute_script(extraction_script)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return [result]
            else:
                return []
                
        except Exception as e:
            logger.error(f"JavaScript extraction failed: {str(e)}")
            return []
    
    def handle_authentication(self, driver: webdriver.Chrome, 
                            auth_config: Dict[str, Any]) -> bool:
        """
        Handle website authentication
        معالجة المصادقة للموقع
        """
        try:
            auth_type = auth_config.get("type", "form")
            
            if auth_type == "form":
                # Navigate to login page
                login_url = auth_config.get("login_url")
                if login_url:
                    driver.get(login_url)
                
                # Fill login form
                username_selector = auth_config.get("username_selector")
                password_selector = auth_config.get("password_selector")
                submit_selector = auth_config.get("submit_selector")
                
                if username_selector and password_selector:
                    username_field = self.smart_element_wait(driver, username_selector, "visible")
                    password_field = self.smart_element_wait(driver, password_selector, "visible")
                    
                    if username_field and password_field:
                        username_field.send_keys(auth_config.get("username", ""))
                        password_field.send_keys(auth_config.get("password", ""))
                        
                        if submit_selector:
                            submit_button = self.smart_element_wait(driver, submit_selector, "clickable")
                            if submit_button:
                                submit_button.click()
                                time.sleep(3)  # Wait for login to complete
                
                return True
                
            elif auth_type == "cookies":
                # Set authentication cookies
                cookies = auth_config.get("cookies", {})
                for name, value in cookies.items():
                    driver.add_cookie({"name": name, "value": value})
                
                return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return False
    
    def capture_page_screenshot(self, driver: webdriver.Chrome, 
                              filename: str, full_page: bool = True) -> bool:
        """
        Capture page screenshot
        التقاط لقطة شاشة للصفحة
        """
        try:
            if full_page:
                # Get full page dimensions
                total_height = driver.execute_script("return document.body.scrollHeight")
                driver.set_window_size(self.window_size[0], total_height)
            
            screenshot_path = Path("screenshots") / filename
            screenshot_path.parent.mkdir(exist_ok=True)
            
            driver.save_screenshot(str(screenshot_path))
            logger.info(f"Screenshot saved: {screenshot_path}")
            return True
            
        except Exception as e:
            logger.error(f"Screenshot capture failed: {str(e)}")
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
