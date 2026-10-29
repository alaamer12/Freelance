# Service ID: PYL12
# Service Name: Python data processing and analysis toolkit
# أدوات معالجة وتحليل البيانات بـ Python

import pandas as pd
import numpy as np
import json
import csv
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import aiofiles
from pathlib import Path
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing
from functools import wraps
import time
import statistics
from collections import defaultdict, Counter
import re

# Configure logging for data processing operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== SECTION 1: Data Models and Types ====================

class DataFormat(Enum):
    """
    Supported data formats for processing
    تنسيقات البيانات المدعومة للمعالجة
    """
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"
    PARQUET = "parquet"
    SQL = "sql"
    XML = "xml"
    PICKLE = "pickle"

class ProcessingStatus(Enum):
    """
    Status of data processing operations
    حالة عمليات معالجة البيانات
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DataQuality(Enum):
    """
    Data quality assessment levels
    مستويات تقييم جودة البيانات
    """
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"

@dataclass
class DatasetInfo:
    """
    Information about a dataset
    معلومات حول مجموعة البيانات
    """
    name: str
    format: DataFormat
    size_bytes: int
    rows: int
    columns: int
    created_at: datetime
    last_modified: datetime
    file_path: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessingTask:
    """
    Data processing task definition
    تعريف مهمة معالجة البيانات
    """
    task_id: str
    name: str
    operation: str
    parameters: Dict[str, Any]
    input_datasets: List[str]
    output_path: str
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: float = 0.0

@dataclass
class DataQualityReport:
    """
    Data quality assessment report
    تقرير تقييم جودة البيانات
    """
    dataset_name: str
    overall_quality: DataQuality
    total_rows: int
    missing_values: Dict[str, int]
    duplicate_rows: int
    data_types: Dict[str, str]
    outliers: Dict[str, int]
    quality_score: float
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)

class DataProcessor:
    """
    Advanced data processing and analysis toolkit
    أدوات متقدمة لمعالجة وتحليل البيانات
    """
    
    def __init__(self, workspace_path: str = "./data_workspace", 
                 max_workers: int = None, enable_caching: bool = True):
        """
        Initialize data processor with workspace and configuration
        تهيئة معالج البيانات مع مساحة العمل والتكوين
        """
        self.workspace_path = Path(workspace_path)
        self.workspace_path.mkdir(exist_ok=True)
        
        # Create subdirectories for organization
        (self.workspace_path / "raw").mkdir(exist_ok=True)
        (self.workspace_path / "processed").mkdir(exist_ok=True)
        (self.workspace_path / "cache").mkdir(exist_ok=True)
        (self.workspace_path / "exports").mkdir(exist_ok=True)
        
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.enable_caching = enable_caching
        self.datasets: Dict[str, DatasetInfo] = {}
        self.processing_tasks: Dict[str, ProcessingTask] = {}
        self.cache: Dict[str, Any] = {}
        
        logger.info(f"Data processor initialized with workspace: {workspace_path}")
        logger.info(f"Maximum workers: {self.max_workers}")
    
    def _generate_checksum(self, data: Union[pd.DataFrame, str]) -> str:
        """
        Generate checksum for data integrity verification
        إنشاء المجموع الاختباري للتحقق من سلامة البيانات
        """
        if isinstance(data, pd.DataFrame):
            data_str = data.to_string()
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _cache_key(self, operation: str, parameters: Dict[str, Any]) -> str:
        """
        Generate cache key for operations
        إنشاء مفتاح التخزين المؤقت للعمليات
        """
        params_str = json.dumps(parameters, sort_keys=True)
        return f"{operation}_{hashlib.md5(params_str.encode()).hexdigest()}"
    
    def register_dataset(self, name: str, file_path: str, 
                        format: DataFormat = None) -> DatasetInfo:
        """
        Register a dataset for processing
        تسجيل مجموعة بيانات للمعالجة
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        # Auto-detect format if not provided
        if format is None:
            extension = file_path_obj.suffix.lower()
            format_map = {
                '.csv': DataFormat.CSV,
                '.json': DataFormat.JSON,
                '.xlsx': DataFormat.EXCEL,
                '.xls': DataFormat.EXCEL,
                '.parquet': DataFormat.PARQUET,
                '.pkl': DataFormat.PICKLE,
                '.pickle': DataFormat.PICKLE
            }
            format = format_map.get(extension, DataFormat.CSV)
        
        # Get file statistics
        stat = file_path_obj.stat()
        size_bytes = stat.st_size
        created_at = datetime.fromtimestamp(stat.st_ctime)
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Load data to get dimensions
        try:
            df = self.load_dataset(file_path, format)
            rows, columns = df.shape
            checksum = self._generate_checksum(df)
        except Exception as e:
            logger.warning(f"Could not analyze dataset dimensions: {str(e)}")
            rows, columns = 0, 0
            checksum = None
        
        dataset_info = DatasetInfo(
            name=name,
            format=format,
            size_bytes=size_bytes,
            rows=rows,
            columns=columns,
            created_at=created_at,
            last_modified=last_modified,
            file_path=str(file_path),
            checksum=checksum
        )
        
        self.datasets[name] = dataset_info
        logger.info(f"Dataset registered: {name} ({rows} rows, {columns} columns)")
        
        return dataset_info
    
    def load_dataset(self, file_path: str, format: DataFormat) -> pd.DataFrame:
        """
        Load dataset from file based on format
        تحميل مجموعة البيانات من الملف حسب التنسيق
        """
        try:
            if format == DataFormat.CSV:
                return pd.read_csv(file_path)
            elif format == DataFormat.JSON:
                return pd.read_json(file_path)
            elif format == DataFormat.EXCEL:
                return pd.read_excel(file_path)
            elif format == DataFormat.PARQUET:
                return pd.read_parquet(file_path)
            elif format == DataFormat.PICKLE:
                return pd.read_pickle(file_path)
            elif format == DataFormat.SQL:
                # Assume SQLite for simplicity
                conn = sqlite3.connect(file_path)
                tables = pd.read_sql_query(
                    "SELECT name FROM sqlite_master WHERE type='table'", conn
                ).name.tolist()
                if tables:
                    return pd.read_sql_query(f"SELECT * FROM {tables[0]}", conn)
                else:
                    raise ValueError("No tables found in SQLite database")
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error loading dataset from {file_path}: {str(e)}")
            raise

# ==================== SECTION 2: Data Quality Assessment ====================

class DataQualityAnalyzer:
    """
    Advanced data quality assessment and reporting
    تقييم وإعداد تقارير جودة البيانات المتقدمة
    """
    
    def __init__(self):
        self.quality_thresholds = {
            'missing_percentage': 0.05,  # 5% missing values threshold
            'duplicate_percentage': 0.02,  # 2% duplicate threshold
            'outlier_percentage': 0.1,  # 10% outlier threshold
        }
    
    def analyze_data_quality(self, df: pd.DataFrame, dataset_name: str) -> DataQualityReport:
        """
        Comprehensive data quality analysis
        تحليل شامل لجودة البيانات
        """
        total_rows = len(df)
        
        # Analyze missing values
        missing_values = {}
        for column in df.columns:
            missing_count = df[column].isnull().sum()
            if missing_count > 0:
                missing_values[column] = missing_count
        
        # Analyze duplicate rows
        duplicate_rows = df.duplicated().sum()
        
        # Analyze data types
        data_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Analyze outliers for numeric columns
        outliers = {}
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outlier_count = ((df[column] < lower_bound) | 
                           (df[column] > upper_bound)).sum()
            if outlier_count > 0:
                outliers[column] = outlier_count
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(
            total_rows, missing_values, duplicate_rows, outliers
        )
        
        # Determine overall quality level
        overall_quality = self._determine_quality_level(quality_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            missing_values, duplicate_rows, outliers, total_rows
        )
        
        return DataQualityReport(
            dataset_name=dataset_name,
            overall_quality=overall_quality,
            total_rows=total_rows,
            missing_values=missing_values,
            duplicate_rows=duplicate_rows,
            data_types=data_types,
            outliers=outliers,
            quality_score=quality_score,
            recommendations=recommendations
        )
    
    def _calculate_quality_score(self, total_rows: int, missing_values: Dict[str, int],
                               duplicate_rows: int, outliers: Dict[str, int]) -> float:
        """
        Calculate overall quality score (0-100)
        حساب نقاط الجودة الإجمالية (0-100)
        """
        score = 100.0
        
        # Deduct points for missing values
        total_missing = sum(missing_values.values())
        missing_percentage = total_missing / (total_rows * len(missing_values)) if missing_values else 0
        score -= min(missing_percentage * 100, 30)  # Max 30 points deduction
        
        # Deduct points for duplicates
        duplicate_percentage = duplicate_rows / total_rows if total_rows > 0 else 0
        score -= min(duplicate_percentage * 100, 20)  # Max 20 points deduction
        
        # Deduct points for outliers
        total_outliers = sum(outliers.values())
        outlier_percentage = total_outliers / total_rows if total_rows > 0 else 0
        score -= min(outlier_percentage * 50, 15)  # Max 15 points deduction
        
        return max(score, 0.0)
    
    def _determine_quality_level(self, score: float) -> DataQuality:
        """
        Determine quality level based on score
        تحديد مستوى الجودة بناءً على النقاط
        """
        if score >= 90:
            return DataQuality.EXCELLENT
        elif score >= 75:
            return DataQuality.GOOD
        elif score >= 60:
            return DataQuality.FAIR
        elif score >= 40:
            return DataQuality.POOR
        else:
            return DataQuality.CRITICAL
    
    def _generate_recommendations(self, missing_values: Dict[str, int],
                                duplicate_rows: int, outliers: Dict[str, int],
                                total_rows: int) -> List[str]:
        """
        Generate data quality improvement recommendations
        إنشاء توصيات لتحسين جودة البيانات
        """
        recommendations = []
        
        if missing_values:
            recommendations.append(
                f"Handle missing values in columns: {', '.join(missing_values.keys())}"
            )
            recommendations.append(
                "Consider imputation strategies or remove rows with excessive missing data"
            )
        
        if duplicate_rows > 0:
            duplicate_percentage = (duplicate_rows / total_rows) * 100
            recommendations.append(
                f"Remove {duplicate_rows} duplicate rows ({duplicate_percentage:.1f}% of data)"
            )
        
        if outliers:
            recommendations.append(
                f"Investigate outliers in columns: {', '.join(outliers.keys())}"
            )
            recommendations.append(
                "Consider outlier treatment methods (capping, transformation, or removal)"
            )
        
        if not missing_values and not duplicate_rows and not outliers:
            recommendations.append("Data quality is excellent - no immediate actions needed")
        
        return recommendations
    
    def generate_quality_report(self, report: DataQualityReport) -> str:
        """
        Generate formatted quality report
        إنشاء تقرير جودة منسق
        """
        report_lines = [
            f"=== DATA QUALITY REPORT ===",
            f"Dataset: {report.dataset_name}",
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"OVERALL QUALITY: {report.overall_quality.value.upper()}",
            f"Quality Score: {report.quality_score:.1f}/100",
            f"Total Rows: {report.total_rows:,}",
            f"",
            f"ISSUES FOUND:",
        ]
        
        if report.missing_values:
            report_lines.append(f"• Missing Values:")
            for column, count in report.missing_values.items():
                percentage = (count / report.total_rows) * 100
                report_lines.append(f"  - {column}: {count:,} ({percentage:.1f}%)")
        
        if report.duplicate_rows > 0:
            duplicate_percentage = (report.duplicate_rows / report.total_rows) * 100
            report_lines.append(f"• Duplicate Rows: {report.duplicate_rows:,} ({duplicate_percentage:.1f}%)")
        
        if report.outliers:
            report_lines.append(f"• Outliers:")
            for column, count in report.outliers.items():
                percentage = (count / report.total_rows) * 100
                report_lines.append(f"  - {column}: {count:,} ({percentage:.1f}%)")
        
        report_lines.extend([
            f"",
            f"RECOMMENDATIONS:",
        ])
        
        for i, recommendation in enumerate(report.recommendations, 1):
            report_lines.append(f"{i}. {recommendation}")
        
        return "\n".join(report_lines)

# ==================== SECTION 3: Data Transformation Engine ====================

class DataTransformationEngine:
    """
    Advanced data transformation and manipulation engine
    محرك التحويل والمعالجة المتقدم للبيانات
    """
    
    def __init__(self, processor: DataProcessor):
        self.processor = processor
        self.transformation_history: List[Dict[str, Any]] = []
    
    def clean_data(self, df: pd.DataFrame, operations: Dict[str, Any]) -> pd.DataFrame:
        """
        Apply comprehensive data cleaning operations
        تطبيق عمليات تنظيف البيانات الشاملة
        """
        cleaned_df = df.copy()
        applied_operations = []
        
        # Remove duplicates
        if operations.get('remove_duplicates', False):
            initial_rows = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates()
            removed_rows = initial_rows - len(cleaned_df)
            applied_operations.append(f"Removed {removed_rows} duplicate rows")
        
        # Handle missing values
        missing_strategy = operations.get('missing_values', {})
        if missing_strategy:
            for column, strategy in missing_strategy.items():
                if column in cleaned_df.columns:
                    if strategy == 'drop':
                        cleaned_df = cleaned_df.dropna(subset=[column])
                        applied_operations.append(f"Dropped rows with missing {column}")
                    elif strategy == 'mean':
                        if cleaned_df[column].dtype in ['int64', 'float64']:
                            cleaned_df[column].fillna(cleaned_df[column].mean(), inplace=True)
                            applied_operations.append(f"Filled missing {column} with mean")
                    elif strategy == 'median':
                        if cleaned_df[column].dtype in ['int64', 'float64']:
                            cleaned_df[column].fillna(cleaned_df[column].median(), inplace=True)
                            applied_operations.append(f"Filled missing {column} with median")
                    elif strategy == 'mode':
                        mode_value = cleaned_df[column].mode().iloc[0] if not cleaned_df[column].mode().empty else None
                        if mode_value is not None:
                            cleaned_df[column].fillna(mode_value, inplace=True)
                            applied_operations.append(f"Filled missing {column} with mode")
                    elif isinstance(strategy, (str, int, float)):
                        cleaned_df[column].fillna(strategy, inplace=True)
                        applied_operations.append(f"Filled missing {column} with {strategy}")
        
        # Handle outliers
        outlier_strategy = operations.get('outliers', {})
        if outlier_strategy:
            for column, strategy in outlier_strategy.items():
                if column in cleaned_df.columns and cleaned_df[column].dtype in ['int64', 'float64']:
                    if strategy == 'remove':
                        Q1 = cleaned_df[column].quantile(0.25)
                        Q3 = cleaned_df[column].quantile(0.75)
                        IQR = Q3 - Q1
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR
                        
                        initial_rows = len(cleaned_df)
                        cleaned_df = cleaned_df[
                            (cleaned_df[column] >= lower_bound) & 
                            (cleaned_df[column] <= upper_bound)
                        ]
                        removed_rows = initial_rows - len(cleaned_df)
                        applied_operations.append(f"Removed {removed_rows} outliers from {column}")
                    
                    elif strategy == 'cap':
                        percentile_95 = cleaned_df[column].quantile(0.95)
                        percentile_5 = cleaned_df[column].quantile(0.05)
                        cleaned_df[column] = cleaned_df[column].clip(
                            lower=percentile_5, upper=percentile_95
                        )
                        applied_operations.append(f"Capped outliers in {column}")
        
        # Data type conversions
        type_conversions = operations.get('type_conversions', {})
        if type_conversions:
            for column, target_type in type_conversions.items():
                if column in cleaned_df.columns:
                    try:
                        if target_type == 'datetime':
                            cleaned_df[column] = pd.to_datetime(cleaned_df[column])
                        elif target_type == 'category':
                            cleaned_df[column] = cleaned_df[column].astype('category')
                        else:
                            cleaned_df[column] = cleaned_df[column].astype(target_type)
                        applied_operations.append(f"Converted {column} to {target_type}")
                    except Exception as e:
                        logger.warning(f"Could not convert {column} to {target_type}: {str(e)}")
        
        # Record transformation history
        self.transformation_history.append({
            'operation': 'clean_data',
            'timestamp': datetime.utcnow(),
            'operations_applied': applied_operations,
            'rows_before': len(df),
            'rows_after': len(cleaned_df)
        })
        
        return cleaned_df
    
    def aggregate_data(self, df: pd.DataFrame, group_by: List[str], 
                      aggregations: Dict[str, Union[str, List[str]]]) -> pd.DataFrame:
        """
        Perform advanced data aggregation
        تنفيذ تجميع البيانات المتقدم
        """
        try:
            # Prepare aggregation dictionary
            agg_dict = {}
            for column, operations in aggregations.items():
                if isinstance(operations, str):
                    operations = [operations]
                
                # Map operation names to pandas functions
                operation_map = {
                    'sum': 'sum',
                    'mean': 'mean',
                    'average': 'mean',
                    'median': 'median',
                    'min': 'min',
                    'max': 'max',
                    'count': 'count',
                    'std': 'std',
                    'var': 'var',
                    'first': 'first',
                    'last': 'last'
                }
                
                valid_operations = [operation_map.get(op, op) for op in operations]
                agg_dict[column] = valid_operations
            
            # Perform aggregation
            result_df = df.groupby(group_by).agg(agg_dict).reset_index()
            
            # Flatten column names if multi-level
            if isinstance(result_df.columns, pd.MultiIndex):
                result_df.columns = [
                    f"{col[0]}_{col[1]}" if col[1] else col[0] 
                    for col in result_df.columns
                ]
            
            # Record transformation
            self.transformation_history.append({
                'operation': 'aggregate_data',
                'timestamp': datetime.utcnow(),
                'group_by': group_by,
                'aggregations': aggregations,
                'rows_before': len(df),
                'rows_after': len(result_df)
            })
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error in data aggregation: {str(e)}")
            raise
    
    def pivot_data(self, df: pd.DataFrame, index: Union[str, List[str]], 
                  columns: str, values: str, 
                  aggfunc: str = 'mean') -> pd.DataFrame:
        """
        Create pivot tables from data
        إنشاء جداول محورية من البيانات
        """
        try:
            pivot_df = df.pivot_table(
                index=index,
                columns=columns,
                values=values,
                aggfunc=aggfunc,
                fill_value=0
            ).reset_index()
            
            # Flatten column names
            if isinstance(pivot_df.columns, pd.MultiIndex):
                pivot_df.columns = [
                    str(col[1]) if col[1] else str(col[0]) 
                    for col in pivot_df.columns
                ]
            
            # Record transformation
            self.transformation_history.append({
                'operation': 'pivot_data',
                'timestamp': datetime.utcnow(),
                'index': index,
                'columns': columns,
                'values': values,
                'aggfunc': aggfunc,
                'rows_before': len(df),
                'rows_after': len(pivot_df)
            })
            
            return pivot_df
            
        except Exception as e:
            logger.error(f"Error in data pivoting: {str(e)}")
            raise
    
    def merge_datasets(self, left_df: pd.DataFrame, right_df: pd.DataFrame,
                      join_keys: Union[str, List[str]], 
                      join_type: str = 'inner') -> pd.DataFrame:
        """
        Merge multiple datasets
        دمج مجموعات البيانات المتعددة
        """
        try:
            merged_df = pd.merge(
                left_df, right_df,
                on=join_keys,
                how=join_type,
                suffixes=('_left', '_right')
            )
            
            # Record transformation
            self.transformation_history.append({
                'operation': 'merge_datasets',
                'timestamp': datetime.utcnow(),
                'join_keys': join_keys,
                'join_type': join_type,
                'left_rows': len(left_df),
                'right_rows': len(right_df),
                'result_rows': len(merged_df)
            })
            
            return merged_df
            
        except Exception as e:
            logger.error(f"Error in dataset merging: {str(e)}")
            raise
    
    def apply_custom_function(self, df: pd.DataFrame, column: str,
                            function_code: str, new_column: str = None) -> pd.DataFrame:
        """
        Apply custom transformation function to column
        تطبيق دالة تحويل مخصصة على العمود
        """
        try:
            result_df = df.copy()
            
            # Create safe execution environment
            safe_globals = {
                'pd': pd,
                'np': np,
                'datetime': datetime,
                'timedelta': timedelta,
                're': re,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'abs': abs,
                'round': round,
                'min': min,
                'max': max,
                'sum': sum
            }
            
            # Execute custom function
            exec(f"def custom_func(x): {function_code}", safe_globals)
            custom_func = safe_globals['custom_func']
            
            target_column = new_column or column
            result_df[target_column] = result_df[column].apply(custom_func)
            
            # Record transformation
            self.transformation_history.append({
                'operation': 'apply_custom_function',
                'timestamp': datetime.utcnow(),
                'column': column,
                'function_code': function_code,
                'new_column': target_column
            })
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error applying custom function: {str(e)}")
            raise
    
    def get_transformation_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all transformations applied
        الحصول على تاريخ جميع التحويلات المطبقة
        """
        return self.transformation_history.copy()

# ==================== SECTION 4: Statistical Analysis Engine ====================

class StatisticalAnalysisEngine:
    """
    Advanced statistical analysis and insights generation
    محرك التحليل الإحصائي المتقدم وإنشاء الرؤى
    """
    
    def __init__(self):
        self.analysis_cache: Dict[str, Any] = {}
        self.analysis_history: List[Dict[str, Any]] = []
    
    def descriptive_statistics(self, df: pd.DataFrame, 
                             columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate comprehensive descriptive statistics
        إنشاء إحصائيات وصفية شاملة
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        stats_result = {}
        
        for column in columns:
            if column not in df.columns:
                continue
                
            series = df[column].dropna()
            
            if len(series) == 0:
                stats_result[column] = {"error": "No valid data"}
                continue
            
            column_stats = {
                'count': len(series),
                'mean': float(series.mean()),
                'median': float(series.median()),
                'std': float(series.std()),
                'var': float(series.var()),
                'min': float(series.min()),
                'max': float(series.max()),
                'range': float(series.max() - series.min()),
                'q1': float(series.quantile(0.25)),
                'q3': float(series.quantile(0.75)),
                'iqr': float(series.quantile(0.75) - series.quantile(0.25)),
                'skewness': float(series.skew()),
                'kurtosis': float(series.kurtosis()),
                'missing_values': int(df[column].isnull().sum()),
                'missing_percentage': float((df[column].isnull().sum() / len(df)) * 100)
            }
            
            # Additional percentiles
            percentiles = [5, 10, 25, 50, 75, 90, 95, 99]
            for p in percentiles:
                column_stats[f'p{p}'] = float(series.quantile(p/100))
            
            stats_result[column] = column_stats
        
        # Record analysis
        self.analysis_history.append({
            'operation': 'descriptive_statistics',
            'timestamp': datetime.utcnow(),
            'columns_analyzed': columns,
            'total_columns': len(columns)
        })
        
        return stats_result
    
    def correlation_analysis(self, df: pd.DataFrame, 
                           method: str = 'pearson',
                           min_correlation: float = 0.1) -> Dict[str, Any]:
        """
        Perform correlation analysis between variables
        تنفيذ تحليل الارتباط بين المتغيرات
        """
        numeric_df = df.select_dtypes(include=[np.number])
        
        if len(numeric_df.columns) < 2:
            return {"error": "Need at least 2 numeric columns for correlation analysis"}
        
        # Calculate correlation matrix
        correlation_matrix = numeric_df.corr(method=method)
        
        # Find significant correlations
        significant_correlations = []
        
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                col1 = correlation_matrix.columns[i]
                col2 = correlation_matrix.columns[j]
                corr_value = correlation_matrix.iloc[i, j]
                
                if abs(corr_value) >= min_correlation and not pd.isna(corr_value):
                    significant_correlations.append({
                        'variable1': col1,
                        'variable2': col2,
                        'correlation': float(corr_value),
                        'strength': self._interpret_correlation_strength(abs(corr_value)),
                        'direction': 'positive' if corr_value > 0 else 'negative'
                    })
        
        # Sort by absolute correlation value
        significant_correlations.sort(key=lambda x: abs(x['correlation']), reverse=True)
        
        result = {
            'correlation_matrix': correlation_matrix.to_dict(),
            'significant_correlations': significant_correlations,
            'method': method,
            'min_correlation_threshold': min_correlation,
            'total_pairs_analyzed': len(significant_correlations)
        }
        
        # Record analysis
        self.analysis_history.append({
            'operation': 'correlation_analysis',
            'timestamp': datetime.utcnow(),
            'method': method,
            'variables_count': len(numeric_df.columns),
            'significant_correlations_found': len(significant_correlations)
        })
        
        return result
    
    def _interpret_correlation_strength(self, abs_correlation: float) -> str:
        """
        Interpret correlation strength
        تفسير قوة الارتباط
        """
        if abs_correlation >= 0.9:
            return "very_strong"
        elif abs_correlation >= 0.7:
            return "strong"
        elif abs_correlation >= 0.5:
            return "moderate"
        elif abs_correlation >= 0.3:
            return "weak"
        else:
            return "very_weak"
    
    def distribution_analysis(self, df: pd.DataFrame, 
                            column: str) -> Dict[str, Any]:
        """
        Analyze distribution characteristics of a column
        تحليل خصائص التوزيع لعمود
        """
        if column not in df.columns:
            return {"error": f"Column '{column}' not found"}
        
        series = df[column].dropna()
        
        if len(series) == 0:
            return {"error": "No valid data in column"}
        
        # Basic distribution stats
        distribution_stats = {
            'column': column,
            'data_type': str(series.dtype),
            'sample_size': len(series),
            'unique_values': series.nunique(),
            'mean': float(series.mean()) if series.dtype in ['int64', 'float64'] else None,
            'median': float(series.median()) if series.dtype in ['int64', 'float64'] else None,
            'mode': series.mode().tolist(),
            'std': float(series.std()) if series.dtype in ['int64', 'float64'] else None,
            'skewness': float(series.skew()) if series.dtype in ['int64', 'float64'] else None,
            'kurtosis': float(series.kurtosis()) if series.dtype in ['int64', 'float64'] else None
        }
        
        # Value counts for categorical or low-cardinality data
        if series.nunique() <= 20 or series.dtype == 'object':
            value_counts = series.value_counts().head(10)
            distribution_stats['value_counts'] = value_counts.to_dict()
            distribution_stats['value_frequencies'] = (value_counts / len(series)).to_dict()
        
        # Distribution shape assessment for numeric data
        if series.dtype in ['int64', 'float64'] and not pd.isna(series.skew()):
            skew = series.skew()
            kurt = series.kurtosis()
            
            # Assess normality
            if abs(skew) < 0.5 and abs(kurt) < 3:
                distribution_stats['distribution_shape'] = 'approximately_normal'
            elif skew > 1:
                distribution_stats['distribution_shape'] = 'right_skewed'
            elif skew < -1:
                distribution_stats['distribution_shape'] = 'left_skewed'
            elif kurt > 3:
                distribution_stats['distribution_shape'] = 'heavy_tailed'
            else:
                distribution_stats['distribution_shape'] = 'irregular'
        
        # Record analysis
        self.analysis_history.append({
            'operation': 'distribution_analysis',
            'timestamp': datetime.utcnow(),
            'column': column,
            'data_type': str(series.dtype),
            'sample_size': len(series)
        })
        
        return distribution_stats
    
    def trend_analysis(self, df: pd.DataFrame, date_column: str, 
                      value_column: str, period: str = 'D') -> Dict[str, Any]:
        """
        Analyze trends over time
        تحليل الاتجاهات عبر الزمن
        """
        if date_column not in df.columns or value_column not in df.columns:
            return {"error": "Required columns not found"}
        
        try:
            # Prepare time series data
            ts_df = df[[date_column, value_column]].copy()
            ts_df[date_column] = pd.to_datetime(ts_df[date_column])
            ts_df = ts_df.sort_values(date_column)
            ts_df = ts_df.dropna()
            
            # Resample by period
            ts_df.set_index(date_column, inplace=True)
            resampled = ts_df[value_column].resample(period).mean()
            
            # Calculate trend metrics
            values = resampled.values
            x = np.arange(len(values))
            
            # Linear trend
            if len(values) > 1:
                slope, intercept = np.polyfit(x, values, 1)
                trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
                
                # Calculate R-squared for trend strength
                y_pred = slope * x + intercept
                ss_res = np.sum((values - y_pred) ** 2)
                ss_tot = np.sum((values - np.mean(values)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            else:
                slope, intercept, r_squared = 0, 0, 0
                trend_direction = 'insufficient_data'
            
            # Seasonal patterns (if enough data)
            seasonal_stats = {}
            if len(resampled) >= 12:  # At least a year of monthly data
                seasonal_stats = self._analyze_seasonality(resampled)
            
            result = {
                'date_column': date_column,
                'value_column': value_column,
                'period': period,
                'data_points': len(resampled),
                'date_range': {
                    'start': resampled.index.min().isoformat(),
                    'end': resampled.index.max().isoformat()
                },
                'trend': {
                    'direction': trend_direction,
                    'slope': float(slope),
                    'intercept': float(intercept),
                    'r_squared': float(r_squared),
                    'strength': self._interpret_trend_strength(r_squared)
                },
                'summary_stats': {
                    'mean': float(resampled.mean()),
                    'std': float(resampled.std()),
                    'min': float(resampled.min()),
                    'max': float(resampled.max()),
                    'growth_rate': float((resampled.iloc[-1] - resampled.iloc[0]) / resampled.iloc[0] * 100) if resampled.iloc[0] != 0 and len(resampled) > 1 else 0
                },
                'seasonal_patterns': seasonal_stats
            }
            
            # Record analysis
            self.analysis_history.append({
                'operation': 'trend_analysis',
                'timestamp': datetime.utcnow(),
                'date_column': date_column,
                'value_column': value_column,
                'period': period,
                'data_points': len(resampled)
            })
            
            return result
            
        except Exception as e:
            return {"error": f"Trend analysis failed: {str(e)}"}
    
    def _analyze_seasonality(self, time_series: pd.Series) -> Dict[str, Any]:
        """
        Analyze seasonal patterns in time series
        تحليل الأنماط الموسمية في السلاسل الزمنية
        """
        try:
            # Monthly seasonality
            monthly_avg = time_series.groupby(time_series.index.month).mean()
            monthly_std = time_series.groupby(time_series.index.month).std()
            
            # Day of week seasonality (if daily data)
            if hasattr(time_series.index, 'dayofweek'):
                weekly_avg = time_series.groupby(time_series.index.dayofweek).mean()
                weekly_std = time_series.groupby(time_series.index.dayofweek).std()
            else:
                weekly_avg = weekly_std = None
            
            seasonal_stats = {
                'monthly_patterns': {
                    'averages': monthly_avg.to_dict(),
                    'std_deviations': monthly_std.to_dict(),
                    'peak_month': int(monthly_avg.idxmax()),
                    'low_month': int(monthly_avg.idxmin())
                }
            }
            
            if weekly_avg is not None:
                seasonal_stats['weekly_patterns'] = {
                    'averages': weekly_avg.to_dict(),
                    'std_deviations': weekly_std.to_dict(),
                    'peak_day': int(weekly_avg.idxmax()),
                    'low_day': int(weekly_avg.idxmin())
                }
            
            return seasonal_stats
            
        except Exception as e:
            return {"error": f"Seasonality analysis failed: {str(e)}"}
    
    def _interpret_trend_strength(self, r_squared: float) -> str:
        """
        Interpret trend strength based on R-squared
        تفسير قوة الاتجاه بناءً على R-squared
        """
        if r_squared >= 0.8:
            return "very_strong"
        elif r_squared >= 0.6:
            return "strong"
        elif r_squared >= 0.4:
            return "moderate"
        elif r_squared >= 0.2:
            return "weak"
        else:
            return "very_weak"
    
    def comparative_analysis(self, df: pd.DataFrame, 
                           group_column: str, value_column: str) -> Dict[str, Any]:
        """
        Compare statistics across different groups
        مقارنة الإحصائيات عبر المجموعات المختلفة
        """
        if group_column not in df.columns or value_column not in df.columns:
            return {"error": "Required columns not found"}
        
        # Group statistics
        grouped = df.groupby(group_column)[value_column]
        
        group_stats = {}
        for group_name, group_data in grouped:
            clean_data = group_data.dropna()
            
            if len(clean_data) > 0:
                group_stats[str(group_name)] = {
                    'count': len(clean_data),
                    'mean': float(clean_data.mean()),
                    'median': float(clean_data.median()),
                    'std': float(clean_data.std()),
                    'min': float(clean_data.min()),
                    'max': float(clean_data.max()),
                    'q1': float(clean_data.quantile(0.25)),
                    'q3': float(clean_data.quantile(0.75))
                }
        
        # Overall comparison metrics
        all_means = [stats['mean'] for stats in group_stats.values()]
        all_stds = [stats['std'] for stats in group_stats.values()]
        
        comparison_result = {
            'group_column': group_column,
            'value_column': value_column,
            'groups_analyzed': len(group_stats),
            'group_statistics': group_stats,
            'comparison_summary': {
                'highest_mean_group': max(group_stats.keys(), key=lambda x: group_stats[x]['mean']),
                'lowest_mean_group': min(group_stats.keys(), key=lambda x: group_stats[x]['mean']),
                'most_variable_group': max(group_stats.keys(), key=lambda x: group_stats[x]['std']),
                'least_variable_group': min(group_stats.keys(), key=lambda x: group_stats[x]['std']),
                'overall_mean_range': max(all_means) - min(all_means),
                'coefficient_of_variation_range': max(all_stds) - min(all_stds)
            }
        }
        
        # Record analysis
        self.analysis_history.append({
            'operation': 'comparative_analysis',
            'timestamp': datetime.utcnow(),
            'group_column': group_column,
            'value_column': value_column,
            'groups_count': len(group_stats)
        })
        
        return comparison_result

# ==================== SECTION 5: Export and Reporting System ====================

class DataExportManager:
    """
    Advanced data export and reporting system
    نظام التصدير والإبلاغ المتقدم للبيانات
    """
    
    def __init__(self, processor: DataProcessor):
        self.processor = processor
        self.export_history: List[Dict[str, Any]] = []
    
    def export_to_format(self, df: pd.DataFrame, file_path: str, 
                        format: DataFormat, **kwargs) -> bool:
        """
        Export DataFrame to specified format
        تصدير DataFrame إلى التنسيق المحدد
        """
        try:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            if format == DataFormat.CSV:
                df.to_csv(file_path, index=kwargs.get('include_index', False))
            elif format == DataFormat.JSON:
                df.to_json(file_path, orient=kwargs.get('orient', 'records'), 
                          indent=kwargs.get('indent', 2))
            elif format == DataFormat.EXCEL:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=kwargs.get('sheet_name', 'Data'), 
                              index=kwargs.get('include_index', False))
            elif format == DataFormat.PARQUET:
                df.to_parquet(file_path, index=kwargs.get('include_index', False))
            elif format == DataFormat.PICKLE:
                df.to_pickle(file_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            # Record export
            self.export_history.append({
                'timestamp': datetime.utcnow(),
                'file_path': str(file_path),
                'format': format.value,
                'rows_exported': len(df),
                'columns_exported': len(df.columns),
                'file_size_bytes': file_path_obj.stat().st_size if file_path_obj.exists() else 0
            })
            
            logger.info(f"Data exported successfully to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            return False
    
    def generate_data_report(self, df: pd.DataFrame, dataset_name: str,
                           include_quality_analysis: bool = True,
                           include_statistical_analysis: bool = True) -> str:
        """
        Generate comprehensive data report
        إنشاء تقرير بيانات شامل
        """
        report_lines = [
            f"=== DATA ANALYSIS REPORT ===",
            f"Dataset: {dataset_name}",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"DATASET OVERVIEW:",
            f"• Total Rows: {len(df):,}",
            f"• Total Columns: {len(df.columns)}",
            f"• Memory Usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
            f"",
            f"COLUMN INFORMATION:",
        ]
        
        # Column details
        for i, (column, dtype) in enumerate(df.dtypes.items(), 1):
            null_count = df[column].isnull().sum()
            null_percentage = (null_count / len(df)) * 100
            unique_count = df[column].nunique()
            
            report_lines.append(
                f"{i:2d}. {column:20s} | {str(dtype):10s} | "
                f"Nulls: {null_count:6,} ({null_percentage:5.1f}%) | "
                f"Unique: {unique_count:6,}"
            )
        
        # Data quality analysis
        if include_quality_analysis:
            quality_analyzer = DataQualityAnalyzer()
            quality_report = quality_analyzer.analyze_data_quality(df, dataset_name)
            
            report_lines.extend([
                f"",
                f"DATA QUALITY ASSESSMENT:",
                f"• Overall Quality: {quality_report.overall_quality.value.upper()}",
                f"• Quality Score: {quality_report.quality_score:.1f}/100",
                f"• Duplicate Rows: {quality_report.duplicate_rows:,}",
            ])
            
            if quality_report.missing_values:
                report_lines.append(f"• Columns with Missing Values: {len(quality_report.missing_values)}")
            
            if quality_report.outliers:
                report_lines.append(f"• Columns with Outliers: {len(quality_report.outliers)}")
        
        # Statistical analysis
        if include_statistical_analysis:
            stats_engine = StatisticalAnalysisEngine()
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if numeric_columns:
                stats = stats_engine.descriptive_statistics(df, numeric_columns[:5])  # Limit to first 5
                
                report_lines.extend([
                    f"",
                    f"STATISTICAL SUMMARY (Top 5 Numeric Columns):",
                ])
                
                for column, column_stats in stats.items():
                    if 'error' not in column_stats:
                        report_lines.extend([
                            f"",
                            f"{column}:",
                            f"  Mean: {column_stats['mean']:.2f}",
                            f"  Median: {column_stats['median']:.2f}",
                            f"  Std Dev: {column_stats['std']:.2f}",
                            f"  Min: {column_stats['min']:.2f}",
                            f"  Max: {column_stats['max']:.2f}",
                        ])
        
        return "\n".join(report_lines)
    
    def create_summary_dashboard(self, datasets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Create summary dashboard for multiple datasets
        إنشاء لوحة معلومات ملخصة لمجموعات البيانات المتعددة
        """
        dashboard_data = {
            'generated_at': datetime.utcnow().isoformat(),
            'total_datasets': len(datasets),
            'datasets_summary': {},
            'overall_statistics': {
                'total_rows': 0,
                'total_columns': 0,
                'total_memory_mb': 0
            }
        }
        
        quality_analyzer = DataQualityAnalyzer()
        
        for name, df in datasets.items():
            # Basic info
            memory_usage = df.memory_usage(deep=True).sum() / 1024**2
            
            # Quality assessment
            quality_report = quality_analyzer.analyze_data_quality(df, name)
            
            dataset_summary = {
                'rows': len(df),
                'columns': len(df.columns),
                'memory_mb': round(memory_usage, 2),
                'data_types': df.dtypes.value_counts().to_dict(),
                'missing_values_total': sum(quality_report.missing_values.values()),
                'duplicate_rows': quality_report.duplicate_rows,
                'quality_score': quality_report.quality_score,
                'quality_level': quality_report.overall_quality.value
            }
            
            dashboard_data['datasets_summary'][name] = dataset_summary
            
            # Update overall statistics
            dashboard_data['overall_statistics']['total_rows'] += len(df)
            dashboard_data['overall_statistics']['total_columns'] += len(df.columns)
            dashboard_data['overall_statistics']['total_memory_mb'] += memory_usage
        
        # Round overall memory usage
        dashboard_data['overall_statistics']['total_memory_mb'] = round(
            dashboard_data['overall_statistics']['total_memory_mb'], 2
        )
        
        return dashboard_data
    
    def export_analysis_results(self, analysis_results: Dict[str, Any], 
                              output_path: str) -> bool:
        """
        Export analysis results to JSON file
        تصدير نتائج التحليل إلى ملف JSON
        """
        try:
            output_path_obj = Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert datetime objects to strings for JSON serialization
            serializable_results = self._make_json_serializable(analysis_results)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Analysis results exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export analysis results: {str(e)}")
            return False
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """
        Convert objects to JSON-serializable format
        تحويل الكائنات إلى تنسيق قابل للتسلسل JSON
        """
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def get_export_history(self) -> List[Dict[str, Any]]:
        """
        Get history of all export operations
        الحصول على تاريخ جميع عمليات التصدير
        """
        return self.export_history.copy()
