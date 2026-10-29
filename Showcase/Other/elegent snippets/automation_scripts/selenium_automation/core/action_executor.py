# Service ID: ATS21 - Part 2
# Advanced Action Execution and Element Handling
# تنفيذ الإجراءات المتقدمة ومعالجة العناصر

import time
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import base64
import hashlib
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException, ElementNotInteractableException
)
from bs4 import BeautifulSoup
import pandas as pd

logger = logging.getLogger(__name__)

# ==================== SECTION 2: Advanced Action Execution ====================

class ActionExecutor:
    """
    Advanced action executor for Selenium automation
    منفذ الإجراءات المتقدم لأتمتة Selenium
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.action_history: List[Dict[str, Any]] = []
        self.element_cache: Dict[str, Any] = {}
        
    def execute_action(self, driver: webdriver.Chrome, action, input_data: Dict[str, Any] = None) -> Any:
        """
        Execute automation action with advanced error handling
        تنفيذ إجراء الأتمتة مع معالجة الأخطاء المتقدمة
        """
        action_start = time.time()
        
        try:
            # Log action start
            logger.info(f"Executing action: {action.action_id} ({action.action_type.value})")
            
            # Check condition if specified
            if action.condition_check and not action.condition_check(driver):
                logger.info(f"Action condition not met: {action.action_id}")
                return None
            
            # Execute based on action type
            result = None
            if action.action_type.value == "navigate":
                result = self._execute_navigate(driver, action.parameters, input_data)
            elif action.action_type.value == "click":
                result = self._execute_click(driver, action.parameters, input_data)
            elif action.action_type.value == "type":
                result = self._execute_type(driver, action.parameters, input_data)
            elif action.action_type.value == "select":
                result = self._execute_select(driver, action.parameters, input_data)
            elif action.action_type.value == "wait":
                result = self._execute_wait(driver, action.parameters, input_data)
            elif action.action_type.value == "extract":
                result = self._execute_extract(driver, action.parameters, input_data)
            elif action.action_type.value == "screenshot":
                result = self._execute_screenshot(driver, action.parameters, input_data)
            elif action.action_type.value == "execute_script":
                result = self._execute_script(driver, action.parameters, input_data)
            elif action.action_type.value == "upload_file":
                result = self._execute_upload_file(driver, action.parameters, input_data)
            elif action.action_type.value == "download_file":
                result = self._execute_download_file(driver, action.parameters, input_data)
            elif action.action_type.value == "handle_alert":
                result = self._execute_handle_alert(driver, action.parameters, input_data)
            elif action.action_type.value == "switch_frame":
                result = self._execute_switch_frame(driver, action.parameters, input_data)
            elif action.action_type.value == "scroll":
                result = self._execute_scroll(driver, action.parameters, input_data)
            else:
                raise ValueError(f"Unknown action type: {action.action_type.value}")
            
            # Log successful execution
            execution_time = time.time() - action_start
            self.action_history.append({
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "status": "success",
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Action completed: {action.action_id} in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = time.time() - action_start
            self.action_history.append({
                "action_id": action.action_id,
                "action_type": action.action_type.value,
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.error(f"Action failed: {action.action_id} - {str(e)}")
            raise
    
    def _execute_navigate(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                         input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute navigation action
        تنفيذ إجراء التنقل
        """
        url = params.get('url')
        if not url:
            raise ValueError("URL parameter required for navigate action")
        
        # Support dynamic URL with input data
        if input_data:
            for key, value in input_data.items():
                url = url.replace(f"{{{key}}}", str(value))
        
        driver.get(url)
        
        # Wait for page load
        wait_for_element = params.get('wait_for_element')
        if wait_for_element:
            WebDriverWait(driver, params.get('timeout', 30)).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
            )
        
        return {
            "url": driver.current_url,
            "title": driver.title,
            "page_source_length": len(driver.page_source)
        }
    
    def _execute_click(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                      input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute click action with advanced element handling
        تنفيذ إجراء النقر مع معالجة العناصر المتقدمة
        """
        selector = params.get('selector')
        if not selector:
            raise ValueError("Selector parameter required for click action")
        
        # Find element with multiple strategies
        element = self._find_element_robust(driver, selector, params.get('timeout', 30))
        
        # Scroll to element if needed
        if params.get('scroll_to_element', True):
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
        
        # Wait for element to be clickable
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable(element))
        
        # Click method selection
        click_method = params.get('click_method', 'normal')
        if click_method == 'javascript':
            driver.execute_script("arguments[0].click();", element)
        elif click_method == 'action_chains':
            ActionChains(driver).move_to_element(element).click().perform()
        else:
            element.click()
        
        # Wait after click
        wait_after = params.get('wait_after_click', 1)
        time.sleep(wait_after)
        
        return {
            "element_tag": element.tag_name,
            "element_text": element.text[:100],
            "current_url": driver.current_url
        }
    
    def _execute_type(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                     input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute typing action with text processing
        تنفيذ إجراء الكتابة مع معالجة النص
        """
        selector = params.get('selector')
        text = params.get('text', '')
        
        if not selector:
            raise ValueError("Selector parameter required for type action")
        
        # Support dynamic text with input data
        if input_data:
            for key, value in input_data.items():
                text = text.replace(f"{{{key}}}", str(value))
        
        element = self._find_element_robust(driver, selector, params.get('timeout', 30))
        
        # Clear field if specified
        if params.get('clear_first', True):
            element.clear()
        
        # Typing method selection
        typing_method = params.get('typing_method', 'normal')
        if typing_method == 'human_like':
            # Simulate human typing with delays
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
        elif typing_method == 'javascript':
            driver.execute_script(f"arguments[0].value = '{text}';", element)
            # Trigger input events
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", element)
        else:
            element.send_keys(text)
        
        # Press additional keys if specified
        additional_keys = params.get('additional_keys', [])
        for key in additional_keys:
            if hasattr(Keys, key.upper()):
                element.send_keys(getattr(Keys, key.upper()))
        
        return {
            "text_entered": text,
            "element_value": element.get_attribute('value'),
            "element_tag": element.tag_name
        }
    
    def _execute_select(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                       input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute select dropdown action
        تنفيذ إجراء اختيار القائمة المنسدلة
        """
        selector = params.get('selector')
        if not selector:
            raise ValueError("Selector parameter required for select action")
        
        element = self._find_element_robust(driver, selector, params.get('timeout', 30))
        select = Select(element)
        
        # Selection method
        select_by = params.get('select_by', 'visible_text')
        value = params.get('value')
        
        # Support dynamic value with input data
        if input_data and value:
            for key, val in input_data.items():
                value = str(value).replace(f"{{{key}}}", str(val))
        
        if select_by == 'visible_text':
            select.select_by_visible_text(value)
        elif select_by == 'value':
            select.select_by_value(value)
        elif select_by == 'index':
            select.select_by_index(int(value))
        else:
            raise ValueError(f"Unknown select method: {select_by}")
        
        # Get selected option info
        selected_option = select.first_selected_option
        
        return {
            "selected_text": selected_option.text,
            "selected_value": selected_option.get_attribute('value'),
            "select_by": select_by,
            "total_options": len(select.options)
        }
    
    def _execute_wait(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                     input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute wait action with various conditions
        تنفيذ إجراء الانتظار مع شروط مختلفة
        """
        wait_type = params.get('wait_type', 'time')
        timeout = params.get('timeout', 30)
        
        if wait_type == 'time':
            duration = params.get('duration', 1)
            time.sleep(duration)
            return {"wait_type": "time", "duration": duration}
        
        elif wait_type == 'element_present':
            selector = params.get('selector')
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            return {"wait_type": "element_present", "selector": selector}
        
        elif wait_type == 'element_visible':
            selector = params.get('selector')
            WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            return {"wait_type": "element_visible", "selector": selector}
        
        elif wait_type == 'element_clickable':
            selector = params.get('selector')
            WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            return {"wait_type": "element_clickable", "selector": selector}
        
        elif wait_type == 'url_contains':
            url_part = params.get('url_part')
            WebDriverWait(driver, timeout).until(EC.url_contains(url_part))
            return {"wait_type": "url_contains", "url_part": url_part, "current_url": driver.current_url}
        
        elif wait_type == 'title_contains':
            title_part = params.get('title_part')
            WebDriverWait(driver, timeout).until(EC.title_contains(title_part))
            return {"wait_type": "title_contains", "title_part": title_part, "current_title": driver.title}
        
        else:
            raise ValueError(f"Unknown wait type: {wait_type}")
    
    def _execute_extract(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                        input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute data extraction action
        تنفيذ إجراء استخراج البيانات
        """
        extraction_rules = params.get('extraction_rules', {})
        if not extraction_rules:
            raise ValueError("Extraction rules required for extract action")
        
        extracted_data = {}
        
        for field_name, rule in extraction_rules.items():
            try:
                selector = rule.get('selector')
                extraction_method = rule.get('method', 'text')
                multiple = rule.get('multiple', False)
                
                if multiple:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    values = []
                    
                    for element in elements:
                        value = self._extract_element_data(element, extraction_method, rule)
                        if value:
                            values.append(value)
                    
                    extracted_data[field_name] = values
                else:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    value = self._extract_element_data(element, extraction_method, rule)
                    extracted_data[field_name] = value
                    
            except NoSuchElementException:
                extracted_data[field_name] = rule.get('default_value', None)
            except Exception as e:
                logger.warning(f"Failed to extract {field_name}: {str(e)}")
                extracted_data[field_name] = rule.get('default_value', None)
        
        # Add metadata
        extracted_data['_extraction_timestamp'] = datetime.utcnow().isoformat()
        extracted_data['_source_url'] = driver.current_url
        extracted_data['_page_title'] = driver.title
        
        return extracted_data
    
    def _extract_element_data(self, element, method: str, rule: Dict[str, Any]) -> Any:
        """
        Extract data from element using specified method
        استخراج البيانات من العنصر باستخدام الطريقة المحددة
        """
        try:
            if method == 'text':
                value = element.text.strip()
            elif method == 'attribute':
                attr_name = rule.get('attribute_name', 'value')
                value = element.get_attribute(attr_name)
            elif method == 'href':
                value = element.get_attribute('href')
            elif method == 'src':
                value = element.get_attribute('src')
            elif method == 'html':
                value = element.get_attribute('outerHTML')
            elif method == 'inner_html':
                value = element.get_attribute('innerHTML')
            else:
                value = element.text.strip()
            
            # Apply data transformation
            data_type = rule.get('data_type', 'string')
            if data_type == 'integer' and value:
                value = int(re.sub(r'[^\d]', '', str(value))) if str(value).strip() else 0
            elif data_type == 'float' and value:
                value = float(re.sub(r'[^\d.]', '', str(value))) if str(value).strip() else 0.0
            elif data_type == 'boolean':
                value = bool(value) if value else False
            
            # Apply regex pattern if specified
            pattern = rule.get('regex_pattern')
            if pattern and value:
                match = re.search(pattern, str(value))
                value = match.group(1) if match and match.groups() else value
            
            return value
            
        except Exception as e:
            logger.warning(f"Element data extraction failed: {str(e)}")
            return rule.get('default_value', None)
    
    def _execute_screenshot(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                           input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute screenshot action
        تنفيذ إجراء لقطة الشاشة
        """
        filename = params.get('filename', f'screenshot_{int(time.time())}.png')
        full_page = params.get('full_page', False)
        element_selector = params.get('element_selector')
        
        screenshot_path = self.workspace_path / "screenshots" / filename
        screenshot_path.parent.mkdir(exist_ok=True)
        
        if element_selector:
            # Screenshot specific element
            element = self._find_element_robust(driver, element_selector, params.get('timeout', 30))
            element.screenshot(str(screenshot_path))
        elif full_page:
            # Full page screenshot
            original_size = driver.get_window_size()
            required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
            required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
            driver.set_window_size(required_width, required_height)
            driver.save_screenshot(str(screenshot_path))
            driver.set_window_size(original_size['width'], original_size['height'])
        else:
            # Regular screenshot
            driver.save_screenshot(str(screenshot_path))
        
        return {
            "screenshot_path": str(screenshot_path),
            "filename": filename,
            "file_size": screenshot_path.stat().st_size,
            "full_page": full_page,
            "element_screenshot": bool(element_selector)
        }
    
    def _execute_script(self, driver: webdriver.Chrome, params: Dict[str, Any], 
                       input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute JavaScript code
        تنفيذ كود JavaScript
        """
        script = params.get('script')
        if not script:
            raise ValueError("Script parameter required for execute_script action")
        
        # Support dynamic script with input data
        if input_data:
            for key, value in input_data.items():
                script = script.replace(f"{{{key}}}", json.dumps(value))
        
        # Execute script
        result = driver.execute_script(script)
        
        return {
            "script_executed": True,
            "script_result": result,
            "script_length": len(script)
        }
    
    def _find_element_robust(self, driver: webdriver.Chrome, selector: str, timeout: int = 30):
        """
        Find element with robust error handling and multiple strategies
        العثور على العنصر مع معالجة قوية للأخطاء واستراتيجيات متعددة
        """
        # Try different selector strategies
        strategies = [
            (By.CSS_SELECTOR, selector),
            (By.XPATH, selector),
            (By.ID, selector),
            (By.NAME, selector),
            (By.CLASS_NAME, selector)
        ]
        
        for by, value in strategies:
            try:
                element = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except (TimeoutException, NoSuchElementException):
                continue
        
        # If all strategies fail, try one more time with CSS selector
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            raise NoSuchElementException(f"Element not found with selector: {selector}")
    
    def get_action_statistics(self) -> Dict[str, Any]:
        """
        Get action execution statistics
        الحصول على إحصائيات تنفيذ الإجراءات
        """
        if not self.action_history:
            return {"total_actions": 0}
        
        successful_actions = [a for a in self.action_history if a['status'] == 'success']
        failed_actions = [a for a in self.action_history if a['status'] == 'failed']
        
        avg_execution_time = sum(a['execution_time'] for a in self.action_history) / len(self.action_history)
        
        return {
            "total_actions": len(self.action_history),
            "successful_actions": len(successful_actions),
            "failed_actions": len(failed_actions),
            "success_rate": (len(successful_actions) / len(self.action_history)) * 100,
            "average_execution_time": round(avg_execution_time, 3),
            "action_types": list(set(a['action_type'] for a in self.action_history))
        }
