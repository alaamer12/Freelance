# Service ID: PYL94 - Part 3
# Data Export and Job Management
# تصدير البيانات وإدارة المهام

import json
import csv
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from dataclasses import asdict
import pickle
import hashlib
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty
import time

logger = logging.getLogger(__name__)

# ==================== SECTION 5: Data Export and Storage ====================

class DataExporter:
    """
    Export scraped data to various formats
    تصدير البيانات المكشوطة إلى تنسيقات مختلفة
    """
    
    def __init__(self, output_directory: str = "./exports"):
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(exist_ok=True)
        self.export_history: List[Dict[str, Any]] = []
    
    def export_to_json(self, data: List[Dict[str, Any]], filename: str, 
                      pretty_print: bool = True) -> bool:
        """
        Export data to JSON format
        تصدير البيانات إلى تنسيق JSON
        """
        try:
            filepath = self.output_directory / f"{filename}.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                else:
                    json.dump(data, f, ensure_ascii=False, default=str)
            
            self._log_export("JSON", filepath, len(data))
            logger.info(f"Data exported to JSON: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"JSON export failed: {str(e)}")
            return False
    
    def export_to_csv(self, data: List[Dict[str, Any]], filename: str,
                     delimiter: str = ',') -> bool:
        """
        Export data to CSV format
        تصدير البيانات إلى تنسيق CSV
        """
        try:
            if not data:
                logger.warning("No data to export to CSV")
                return False
            
            filepath = self.output_directory / f"{filename}.csv"
            df = pd.DataFrame(data)
            
            df.to_csv(filepath, index=False, encoding='utf-8', sep=delimiter)
            
            self._log_export("CSV", filepath, len(data))
            logger.info(f"Data exported to CSV: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"CSV export failed: {str(e)}")
            return False
    
    def export_to_excel(self, data: List[Dict[str, Any]], filename: str,
                       sheet_name: str = "ScrapedData") -> bool:
        """
        Export data to Excel format
        تصدير البيانات إلى تنسيق Excel
        """
        try:
            if not data:
                logger.warning("No data to export to Excel")
                return False
            
            filepath = self.output_directory / f"{filename}.xlsx"
            df = pd.DataFrame(data)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            self._log_export("Excel", filepath, len(data))
            logger.info(f"Data exported to Excel: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Excel export failed: {str(e)}")
            return False
    
    def export_to_xml(self, data: List[Dict[str, Any]], filename: str,
                     root_element: str = "data", item_element: str = "item") -> bool:
        """
        Export data to XML format
        تصدير البيانات إلى تنسيق XML
        """
        try:
            filepath = self.output_directory / f"{filename}.xml"
            
            root = ET.Element(root_element)
            
            for item in data:
                item_elem = ET.SubElement(root, item_element)
                for key, value in item.items():
                    # Clean key name for XML
                    clean_key = str(key).replace(' ', '_').replace('-', '_')
                    elem = ET.SubElement(item_elem, clean_key)
                    elem.text = str(value) if value is not None else ""
            
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            
            self._log_export("XML", filepath, len(data))
            logger.info(f"Data exported to XML: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"XML export failed: {str(e)}")
            return False
    
    def export_to_database(self, data: List[Dict[str, Any]], filename: str,
                          table_name: str = "scraped_data") -> bool:
        """
        Export data to SQLite database
        تصدير البيانات إلى قاعدة بيانات SQLite
        """
        try:
            if not data:
                logger.warning("No data to export to database")
                return False
            
            filepath = self.output_directory / f"{filename}.db"
            df = pd.DataFrame(data)
            
            with sqlite3.connect(filepath) as conn:
                df.to_sql(table_name, conn, if_exists='replace', index=False)
            
            self._log_export("Database", filepath, len(data))
            logger.info(f"Data exported to database: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Database export failed: {str(e)}")
            return False
    
    def export_multiple_formats(self, data: List[Dict[str, Any]], base_filename: str,
                              formats: List[str] = None) -> Dict[str, bool]:
        """
        Export data to multiple formats simultaneously
        تصدير البيانات إلى تنسيقات متعددة في نفس الوقت
        """
        if formats is None:
            formats = ['json', 'csv', 'excel']
        
        results = {}
        
        for format_type in formats:
            if format_type.lower() == 'json':
                results['json'] = self.export_to_json(data, base_filename)
            elif format_type.lower() == 'csv':
                results['csv'] = self.export_to_csv(data, base_filename)
            elif format_type.lower() == 'excel':
                results['excel'] = self.export_to_excel(data, base_filename)
            elif format_type.lower() == 'xml':
                results['xml'] = self.export_to_xml(data, base_filename)
            elif format_type.lower() == 'database':
                results['database'] = self.export_to_database(data, base_filename)
        
        successful_exports = sum(1 for success in results.values() if success)
        logger.info(f"Multi-format export completed: {successful_exports}/{len(formats)} successful")
        
        return results
    
    def _log_export(self, format_type: str, filepath: Path, record_count: int) -> None:
        """
        Log export operation
        تسجيل عملية التصدير
        """
        export_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "format": format_type,
            "filepath": str(filepath),
            "record_count": record_count,
            "file_size": filepath.stat().st_size if filepath.exists() else 0
        }
        self.export_history.append(export_record)
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """
        Get export operation history
        الحصول على تاريخ عمليات التصدير
        """
        return self.export_history.copy()
    
    def create_data_report(self, data: List[Dict[str, Any]], filename: str) -> bool:
        """
        Create comprehensive data report
        إنشاء تقرير شامل للبيانات
        """
        try:
            if not data:
                return False
            
            df = pd.DataFrame(data)
            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "summary": {
                    "total_records": len(df),
                    "columns": len(df.columns),
                    "column_names": list(df.columns)
                },
                "data_quality": {
                    "missing_values": df.isnull().sum().to_dict(),
                    "duplicate_records": int(df.duplicated().sum()),
                    "completeness_percentage": round((df.count().sum() / (len(df) * len(df.columns))) * 100, 2)
                },
                "column_analysis": {},
                "source_analysis": {}
            }
            
            # Column analysis
            for col in df.columns:
                if col.startswith('_'):
                    continue
                
                col_analysis = {
                    "data_type": str(df[col].dtype),
                    "unique_values": int(df[col].nunique()),
                    "null_count": int(df[col].isnull().sum())
                }
                
                if df[col].dtype == 'object':
                    col_analysis["sample_values"] = df[col].dropna().head(5).tolist()
                    col_analysis["value_lengths"] = {
                        "min": int(df[col].astype(str).str.len().min()),
                        "max": int(df[col].astype(str).str.len().max()),
                        "avg": round(df[col].astype(str).str.len().mean(), 2)
                    }
                
                report["column_analysis"][col] = col_analysis
            
            # Source analysis
            if '_source_url' in df.columns:
                report["source_analysis"] = {
                    "unique_sources": int(df['_source_url'].nunique()),
                    "records_per_source": df['_source_url'].value_counts().to_dict()
                }
            
            # Save report
            filepath = self.output_directory / f"{filename}_report.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Data report created: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Report creation failed: {str(e)}")
            return False

class JobManager:
    """
    Manage scraping jobs and execution
    إدارة مهام الكشط والتنفيذ
    """
    
    def __init__(self, workspace_path: str = "./scraping_workspace"):
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        self.jobs: Dict[str, Any] = {}
        self.job_queue: Queue = Queue()
        self.active_jobs: Dict[str, threading.Thread] = {}
        self.job_results: Dict[str, Dict[str, Any]] = {}
        
        # Initialize components
        self.data_exporter = DataExporter(str(self.workspace_path / "exports"))
        
        # Job execution thread pool
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.is_running = True
        
        # Start job processor
        self.job_processor_thread = threading.Thread(target=self._process_job_queue, daemon=True)
        self.job_processor_thread.start()
        
        logger.info("Job manager initialized")
    
    def submit_job(self, job) -> bool:
        """
        Submit job for execution
        تقديم مهمة للتنفيذ
        """
        try:
            job.status = "PENDING"  # Assuming ScrapingStatus enum
            self.jobs[job.job_id] = job
            self.job_queue.put(job.job_id)
            
            logger.info(f"Job submitted: {job.name} ({job.job_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit job {job.job_id}: {str(e)}")
            return False
    
    def _process_job_queue(self) -> None:
        """
        Process jobs from queue
        معالجة المهام من الطابور
        """
        while self.is_running:
            try:
                job_id = self.job_queue.get(timeout=1)
                if job_id in self.jobs:
                    job = self.jobs[job_id]
                    
                    # Execute job in thread pool
                    future = self.executor.submit(self._execute_job, job)
                    
                    # Store future for monitoring
                    self.job_results[job_id] = {
                        "future": future,
                        "started_at": datetime.utcnow()
                    }
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Job queue processing error: {str(e)}")
    
    def _execute_job(self, job) -> Dict[str, Any]:
        """
        Execute individual scraping job
        تنفيذ مهمة كشط فردية
        """
        job_result = {
            "job_id": job.job_id,
            "status": "running",
            "started_at": datetime.utcnow(),
            "data": [],
            "errors": []
        }
        
        try:
            job.status = "RUNNING"  # Assuming ScrapingStatus enum
            job.started_at = datetime.utcnow()
            
            # Import here to avoid circular imports
            from .scraping_engine import ScrapingEngine
            from .scraping_advanced import SeleniumScraper, AsyncScraper
            
            # Execute based on method
            if job.method.value == "requests":
                engine = ScrapingEngine()
                engine.jobs[job.job_id] = job
                success = engine.start_job(job.job_id)
                job_result["data"] = job.data_cache if success else []
                
            elif job.method.value == "selenium":
                scraper = SeleniumScraper()
                all_data = []
                for target in job.targets:
                    target_data = scraper.scrape_target(target)
                    all_data.extend(target_data)
                scraper.close_all_drivers()
                job_result["data"] = all_data
                job.data_cache = all_data
                
            elif job.method.value == "async_http":
                scraper = AsyncScraper()
                import asyncio
                all_data = asyncio.run(scraper.scrape_multiple_targets(job.targets))
                asyncio.run(scraper.close_session())
                job_result["data"] = all_data
                job.data_cache = all_data
            
            # Update job status
            job.status = "COMPLETED"  # Assuming ScrapingStatus enum
            job.completed_at = datetime.utcnow()
            job.scraped_items = len(job_result["data"])
            
            # Export data
            if job_result["data"]:
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                export_filename = f"{job.job_id}_{timestamp}"
                
                # Export in specified format
                if job.output_format.value == "json":
                    self.data_exporter.export_to_json(job_result["data"], export_filename)
                elif job.output_format.value == "csv":
                    self.data_exporter.export_to_csv(job_result["data"], export_filename)
                elif job.output_format.value == "excel":
                    self.data_exporter.export_to_excel(job_result["data"], export_filename)
                elif job.output_format.value == "xml":
                    self.data_exporter.export_to_xml(job_result["data"], export_filename)
                
                # Create data report
                self.data_exporter.create_data_report(job_result["data"], export_filename)
            
            job_result["status"] = "completed"
            job_result["completed_at"] = datetime.utcnow()
            
            logger.info(f"Job completed: {job.name} - {len(job_result['data'])} items scraped")
            
        except Exception as e:
            job.status = "FAILED"  # Assuming ScrapingStatus enum
            job_result["status"] = "failed"
            job_result["errors"].append(str(e))
            logger.error(f"Job execution failed: {job.name} - {str(e)}")
        
        return job_result
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get current job status
        الحصول على حالة المهمة الحالية
        """
        if job_id not in self.jobs:
            return {"status": "not_found"}
        
        job = self.jobs[job_id]
        status = {
            "job_id": job_id,
            "name": job.name,
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "scraped_items": job.scraped_items,
            "failed_items": job.failed_items,
            "total_targets": len(job.targets)
        }
        
        # Add execution details if available
        if job_id in self.job_results:
            result = self.job_results[job_id]
            if "future" in result:
                status["is_running"] = not result["future"].done()
                if result["future"].done():
                    try:
                        execution_result = result["future"].result()
                        status["execution_result"] = execution_result
                    except Exception as e:
                        status["execution_error"] = str(e)
        
        return status
    
    def list_jobs(self) -> List[Dict[str, Any]]:
        """
        List all jobs with their status
        سرد جميع المهام مع حالتها
        """
        job_list = []
        for job_id in self.jobs:
            job_list.append(self.get_job_status(job_id))
        
        return job_list
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel running job
        إلغاء المهمة الجارية
        """
        try:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = "CANCELLED"  # Assuming ScrapingStatus enum
                
                # Cancel future if exists
                if job_id in self.job_results and "future" in self.job_results[job_id]:
                    future = self.job_results[job_id]["future"]
                    future.cancel()
                
                logger.info(f"Job cancelled: {job_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {str(e)}")
            return False
    
    def get_job_data(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get scraped data from completed job
        الحصول على البيانات المكشوطة من المهمة المكتملة
        """
        if job_id not in self.jobs:
            return []
        
        job = self.jobs[job_id]
        return job.data_cache
    
    def cleanup_completed_jobs(self, older_than_hours: int = 24) -> int:
        """
        Clean up old completed jobs
        تنظيف المهام المكتملة القديمة
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        cleaned_count = 0
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if (job.completed_at and 
                job.completed_at < cutoff_time and 
                job.status.value in ["completed", "failed", "cancelled"]):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
            if job_id in self.job_results:
                del self.job_results[job_id]
            cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old jobs")
        return cleaned_count
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get scraping performance statistics
        الحصول على إحصائيات أداء الكشط
        """
        stats = {
            "total_jobs": len(self.jobs),
            "completed_jobs": 0,
            "failed_jobs": 0,
            "running_jobs": 0,
            "total_items_scraped": 0,
            "average_items_per_job": 0,
            "success_rate": 0.0
        }
        
        for job in self.jobs.values():
            if hasattr(job.status, 'value'):
                status = job.status.value
            else:
                status = str(job.status)
                
            if status == "completed":
                stats["completed_jobs"] += 1
                stats["total_items_scraped"] += job.scraped_items
            elif status == "failed":
                stats["failed_jobs"] += 1
            elif status == "running":
                stats["running_jobs"] += 1
        
        if stats["completed_jobs"] > 0:
            stats["average_items_per_job"] = stats["total_items_scraped"] / stats["completed_jobs"]
            stats["success_rate"] = (stats["completed_jobs"] / len(self.jobs)) * 100
        
        return stats
    
    def shutdown(self) -> None:
        """
        Shutdown job manager
        إيقاف مدير المهام
        """
        self.is_running = False
        self.executor.shutdown(wait=True)
        logger.info("Job manager shutdown completed")
