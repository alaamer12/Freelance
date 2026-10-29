# Service ID: ATS78 - Part 2
# Specialized Automation Bots
# بوتات الأتمتة المتخصصة

import os
import shutil
import zipfile
import csv
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import pandas as pd
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import hashlib
import psutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import schedule
import pickle

logger = logging.getLogger(__name__)

# Import base classes from automation_bots.py
from .automation_bots import AutomationBot, BotTask, BotExecution, BotStatus, BotType, TaskPriority

# ==================== SECTION 3: File Processing Bot ====================

class FileProcessorBot(AutomationBot):
    """
    File processing and management automation bot
    بوت أتمتة معالجة وإدارة الملفات
    """
    
    def __init__(self, bot_id: str, name: str, workspace_path: str = "./bot_workspace"):
        super().__init__(bot_id, name, BotType.FILE_PROCESSOR, workspace_path)
        self.processed_files: List[str] = []
        self.file_watchers: Dict[str, threading.Thread] = {}
        self.processing_stats = {
            "files_processed": 0,
            "bytes_processed": 0,
            "processing_errors": 0
        }
    
    def _perform_task_action(self, task: BotTask) -> Dict[str, Any]:
        """
        Perform file processing task
        تنفيذ مهمة معالجة الملفات
        """
        action_type = task.parameters.get('action_type')
        
        if action_type == 'copy_files':
            return self._copy_files_action(task.parameters)
        elif action_type == 'move_files':
            return self._move_files_action(task.parameters)
        elif action_type == 'compress_files':
            return self._compress_files_action(task.parameters)
        elif action_type == 'process_csv':
            return self._process_csv_action(task.parameters)
        elif action_type == 'organize_files':
            return self._organize_files_action(task.parameters)
        elif action_type == 'watch_directory':
            return self._watch_directory_action(task.parameters)
        elif action_type == 'cleanup_files':
            return self._cleanup_files_action(task.parameters)
        else:
            raise ValueError(f"Unknown file processing action: {action_type}")
    
    def _copy_files_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Copy files from source to destination
        نسخ الملفات من المصدر إلى الوجهة
        """
        source_path = Path(params.get('source_path', ''))
        dest_path = Path(params.get('dest_path', ''))
        file_pattern = params.get('file_pattern', '*')
        
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        
        dest_path.mkdir(parents=True, exist_ok=True)
        
        copied_files = []
        total_bytes = 0
        
        if source_path.is_file():
            # Copy single file
            dest_file = dest_path / source_path.name
            shutil.copy2(source_path, dest_file)
            copied_files.append(str(source_path))
            total_bytes = source_path.stat().st_size
        else:
            # Copy multiple files matching pattern
            for file_path in source_path.glob(file_pattern):
                if file_path.is_file():
                    dest_file = dest_path / file_path.name
                    shutil.copy2(file_path, dest_file)
                    copied_files.append(str(file_path))
                    total_bytes += file_path.stat().st_size
        
        self.processing_stats["files_processed"] += len(copied_files)
        self.processing_stats["bytes_processed"] += total_bytes
        
        return {
            "action": "copy_files",
            "copied_files": copied_files,
            "total_files": len(copied_files),
            "total_bytes": total_bytes,
            "dest_path": str(dest_path)
        }
    
    def _move_files_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Move files from source to destination
        نقل الملفات من المصدر إلى الوجهة
        """
        source_path = Path(params.get('source_path', ''))
        dest_path = Path(params.get('dest_path', ''))
        file_pattern = params.get('file_pattern', '*')
        
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        
        dest_path.mkdir(parents=True, exist_ok=True)
        
        moved_files = []
        total_bytes = 0
        
        if source_path.is_file():
            # Move single file
            file_size = source_path.stat().st_size
            dest_file = dest_path / source_path.name
            shutil.move(str(source_path), str(dest_file))
            moved_files.append(str(dest_file))
            total_bytes = file_size
        else:
            # Move multiple files matching pattern
            for file_path in source_path.glob(file_pattern):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    dest_file = dest_path / file_path.name
                    shutil.move(str(file_path), str(dest_file))
                    moved_files.append(str(dest_file))
                    total_bytes += file_size
        
        self.processing_stats["files_processed"] += len(moved_files)
        self.processing_stats["bytes_processed"] += total_bytes
        
        return {
            "action": "move_files",
            "moved_files": moved_files,
            "total_files": len(moved_files),
            "total_bytes": total_bytes,
            "dest_path": str(dest_path)
        }
    
    def _compress_files_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress files into archive
        ضغط الملفات في أرشيف
        """
        source_path = Path(params.get('source_path', ''))
        archive_path = Path(params.get('archive_path', ''))
        compression_type = params.get('compression_type', 'zip')
        
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        
        compressed_files = []
        original_size = 0
        
        if compression_type == 'zip':
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if source_path.is_file():
                    zipf.write(source_path, source_path.name)
                    compressed_files.append(str(source_path))
                    original_size = source_path.stat().st_size
                else:
                    for file_path in source_path.rglob('*'):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source_path)
                            zipf.write(file_path, arcname)
                            compressed_files.append(str(file_path))
                            original_size += file_path.stat().st_size
        
        compressed_size = archive_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        self.processing_stats["files_processed"] += len(compressed_files)
        self.processing_stats["bytes_processed"] += original_size
        
        return {
            "action": "compress_files",
            "archive_path": str(archive_path),
            "compressed_files": len(compressed_files),
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": round(compression_ratio, 2)
        }
    
    def _process_csv_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process CSV file with transformations
        معالجة ملف CSV مع التحويلات
        """
        csv_path = Path(params.get('csv_path', ''))
        output_path = Path(params.get('output_path', ''))
        operations = params.get('operations', [])
        
        if not csv_path.exists():
            raise ValueError(f"CSV file does not exist: {csv_path}")
        
        # Read CSV file
        df = pd.read_csv(csv_path)
        original_rows = len(df)
        
        # Apply operations
        for operation in operations:
            op_type = operation.get('type')
            
            if op_type == 'filter':
                column = operation.get('column')
                condition = operation.get('condition')
                value = operation.get('value')
                
                if condition == 'equals':
                    df = df[df[column] == value]
                elif condition == 'contains':
                    df = df[df[column].str.contains(str(value), na=False)]
                elif condition == 'greater_than':
                    df = df[df[column] > value]
                elif condition == 'less_than':
                    df = df[df[column] < value]
            
            elif op_type == 'sort':
                column = operation.get('column')
                ascending = operation.get('ascending', True)
                df = df.sort_values(by=column, ascending=ascending)
            
            elif op_type == 'group_by':
                column = operation.get('column')
                agg_func = operation.get('agg_func', 'count')
                df = df.groupby(column).agg(agg_func).reset_index()
            
            elif op_type == 'add_column':
                column_name = operation.get('column_name')
                column_value = operation.get('column_value')
                df[column_name] = column_value
        
        # Save processed CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        processed_rows = len(df)
        file_size = output_path.stat().st_size
        
        self.processing_stats["files_processed"] += 1
        self.processing_stats["bytes_processed"] += file_size
        
        return {
            "action": "process_csv",
            "input_path": str(csv_path),
            "output_path": str(output_path),
            "original_rows": original_rows,
            "processed_rows": processed_rows,
            "operations_applied": len(operations),
            "file_size": file_size
        }
    
    def _organize_files_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize files by type, date, or custom rules
        تنظيم الملفات حسب النوع أو التاريخ أو القواعد المخصصة
        """
        source_path = Path(params.get('source_path', ''))
        organization_type = params.get('organization_type', 'by_extension')
        
        if not source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        
        organized_files = {}
        
        for file_path in source_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            if organization_type == 'by_extension':
                extension = file_path.suffix.lower() or 'no_extension'
                dest_dir = source_path / f"by_extension/{extension}"
            
            elif organization_type == 'by_date':
                file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
                date_folder = file_date.strftime('%Y-%m-%d')
                dest_dir = source_path / f"by_date/{date_folder}"
            
            elif organization_type == 'by_size':
                file_size = file_path.stat().st_size
                if file_size < 1024 * 1024:  # < 1MB
                    size_category = 'small'
                elif file_size < 10 * 1024 * 1024:  # < 10MB
                    size_category = 'medium'
                else:
                    size_category = 'large'
                dest_dir = source_path / f"by_size/{size_category}"
            
            else:
                continue
            
            # Create destination directory and move file
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / file_path.name
            
            # Handle name conflicts
            counter = 1
            while dest_file.exists():
                name_parts = file_path.stem, counter, file_path.suffix
                dest_file = dest_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                counter += 1
            
            shutil.move(str(file_path), str(dest_file))
            
            category = dest_dir.name
            if category not in organized_files:
                organized_files[category] = []
            organized_files[category].append(str(dest_file))
        
        total_files = sum(len(files) for files in organized_files.values())
        self.processing_stats["files_processed"] += total_files
        
        return {
            "action": "organize_files",
            "organization_type": organization_type,
            "organized_files": organized_files,
            "total_files": total_files,
            "categories": len(organized_files)
        }

# ==================== SECTION 4: Data Collection Bot ====================

class DataCollectorBot(AutomationBot):
    """
    Data collection and aggregation automation bot
    بوت أتمتة جمع وتجميع البيانات
    """
    
    def __init__(self, bot_id: str, name: str, workspace_path: str = "./bot_workspace"):
        super().__init__(bot_id, name, BotType.DATA_COLLECTOR, workspace_path)
        self.collected_data: List[Dict[str, Any]] = []
        self.data_sources: Dict[str, Dict[str, Any]] = {}
        self.collection_stats = {
            "total_records": 0,
            "successful_collections": 0,
            "failed_collections": 0
        }
    
    def _perform_task_action(self, task: BotTask) -> Dict[str, Any]:
        """
        Perform data collection task
        تنفيذ مهمة جمع البيانات
        """
        action_type = task.parameters.get('action_type')
        
        if action_type == 'collect_api_data':
            return self._collect_api_data_action(task.parameters)
        elif action_type == 'collect_database_data':
            return self._collect_database_data_action(task.parameters)
        elif action_type == 'collect_file_data':
            return self._collect_file_data_action(task.parameters)
        elif action_type == 'aggregate_data':
            return self._aggregate_data_action(task.parameters)
        elif action_type == 'export_data':
            return self._export_data_action(task.parameters)
        else:
            raise ValueError(f"Unknown data collection action: {action_type}")
    
    def _collect_api_data_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from API endpoints
        جمع البيانات من نقاط API
        """
        api_url = params.get('api_url')
        headers = params.get('headers', {})
        auth = params.get('auth')
        data_path = params.get('data_path', '')  # JSONPath to extract data
        
        if not api_url:
            raise ValueError("api_url parameter required")
        
        try:
            # Make API request
            response = requests.get(api_url, headers=headers, auth=auth, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract data using path if specified
            if data_path:
                # Simple dot notation path extraction
                path_parts = data_path.split('.')
                for part in path_parts:
                    if isinstance(data, dict):
                        data = data.get(part, {})
                    elif isinstance(data, list) and part.isdigit():
                        data = data[int(part)] if int(part) < len(data) else {}
            
            # Ensure data is a list
            if not isinstance(data, list):
                data = [data] if data else []
            
            # Add metadata to each record
            for record in data:
                if isinstance(record, dict):
                    record['_collected_at'] = datetime.utcnow().isoformat()
                    record['_source'] = 'api'
                    record['_source_url'] = api_url
            
            self.collected_data.extend(data)
            self.collection_stats["total_records"] += len(data)
            self.collection_stats["successful_collections"] += 1
            
            return {
                "action": "collect_api_data",
                "api_url": api_url,
                "records_collected": len(data),
                "status_code": response.status_code,
                "response_size": len(response.content)
            }
            
        except Exception as e:
            self.collection_stats["failed_collections"] += 1
            raise Exception(f"API data collection failed: {str(e)}")
    
    def _collect_database_data_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from database
        جمع البيانات من قاعدة البيانات
        """
        db_path = params.get('db_path')
        query = params.get('query')
        
        if not db_path or not query:
            raise ValueError("db_path and query parameters required")
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                # Get column names
                columns = [description[0] for description in cursor.description]
                
                # Fetch data and convert to dictionaries
                rows = cursor.fetchall()
                data = []
                
                for row in rows:
                    record = dict(zip(columns, row))
                    record['_collected_at'] = datetime.utcnow().isoformat()
                    record['_source'] = 'database'
                    record['_source_db'] = db_path
                    data.append(record)
                
                self.collected_data.extend(data)
                self.collection_stats["total_records"] += len(data)
                self.collection_stats["successful_collections"] += 1
                
                return {
                    "action": "collect_database_data",
                    "db_path": db_path,
                    "query": query,
                    "records_collected": len(data),
                    "columns": columns
                }
                
        except Exception as e:
            self.collection_stats["failed_collections"] += 1
            raise Exception(f"Database data collection failed: {str(e)}")
    
    def _collect_file_data_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from files (CSV, JSON, Excel)
        جمع البيانات من الملفات
        """
        file_path = Path(params.get('file_path', ''))
        file_type = params.get('file_type', 'auto')
        
        if not file_path.exists():
            raise ValueError(f"File does not exist: {file_path}")
        
        try:
            data = []
            
            # Auto-detect file type if not specified
            if file_type == 'auto':
                file_type = file_path.suffix.lower()
            
            if file_type in ['.csv', 'csv']:
                df = pd.read_csv(file_path)
                data = df.to_dict('records')
            
            elif file_type in ['.json', 'json']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    if isinstance(file_data, list):
                        data = file_data
                    else:
                        data = [file_data]
            
            elif file_type in ['.xlsx', '.xls', 'excel']:
                df = pd.read_excel(file_path)
                data = df.to_dict('records')
            
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Add metadata
            for record in data:
                if isinstance(record, dict):
                    record['_collected_at'] = datetime.utcnow().isoformat()
                    record['_source'] = 'file'
                    record['_source_file'] = str(file_path)
            
            self.collected_data.extend(data)
            self.collection_stats["total_records"] += len(data)
            self.collection_stats["successful_collections"] += 1
            
            return {
                "action": "collect_file_data",
                "file_path": str(file_path),
                "file_type": file_type,
                "records_collected": len(data),
                "file_size": file_path.stat().st_size
            }
            
        except Exception as e:
            self.collection_stats["failed_collections"] += 1
            raise Exception(f"File data collection failed: {str(e)}")
    
    def _aggregate_data_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate collected data
        تجميع البيانات المجمعة
        """
        aggregation_rules = params.get('aggregation_rules', [])
        
        if not self.collected_data:
            return {
                "action": "aggregate_data",
                "message": "No data to aggregate",
                "aggregated_data": {}
            }
        
        df = pd.DataFrame(self.collected_data)
        aggregated_results = {}
        
        for rule in aggregation_rules:
            rule_name = rule.get('name', f'rule_{len(aggregated_results)}')
            group_by = rule.get('group_by')
            agg_func = rule.get('agg_func', 'count')
            column = rule.get('column')
            
            try:
                if group_by:
                    if column and agg_func != 'count':
                        result = df.groupby(group_by)[column].agg(agg_func)
                    else:
                        result = df.groupby(group_by).size()
                else:
                    if column and agg_func != 'count':
                        result = df[column].agg(agg_func)
                    else:
                        result = len(df)
                
                # Convert to serializable format
                if hasattr(result, 'to_dict'):
                    aggregated_results[rule_name] = result.to_dict()
                else:
                    aggregated_results[rule_name] = result
                    
            except Exception as e:
                logger.warning(f"Aggregation rule '{rule_name}' failed: {str(e)}")
                aggregated_results[rule_name] = {"error": str(e)}
        
        return {
            "action": "aggregate_data",
            "total_records": len(self.collected_data),
            "aggregation_rules_applied": len(aggregation_rules),
            "aggregated_data": aggregated_results
        }
    
    def _export_data_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export collected data
        تصدير البيانات المجمعة
        """
        export_format = params.get('format', 'json')
        output_path = Path(params.get('output_path', ''))
        
        if not self.collected_data:
            return {
                "action": "export_data",
                "message": "No data to export"
            }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if export_format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(self.collected_data, f, indent=2, default=str)
            
            elif export_format == 'csv':
                df = pd.DataFrame(self.collected_data)
                df.to_csv(output_path, index=False)
            
            elif export_format == 'excel':
                df = pd.DataFrame(self.collected_data)
                df.to_excel(output_path, index=False)
            
            else:
                raise ValueError(f"Unsupported export format: {export_format}")
            
            file_size = output_path.stat().st_size
            
            return {
                "action": "export_data",
                "format": export_format,
                "output_path": str(output_path),
                "records_exported": len(self.collected_data),
                "file_size": file_size
            }
            
        except Exception as e:
            raise Exception(f"Data export failed: {str(e)}")
    
    def get_collection_summary(self) -> Dict[str, Any]:
        """
        Get data collection summary
        الحصول على ملخص جمع البيانات
        """
        return {
            "total_records": len(self.collected_data),
            "collection_stats": self.collection_stats,
            "data_sources": len(self.data_sources),
            "latest_collection": self.collected_data[-1]['_collected_at'] if self.collected_data else None
        }
