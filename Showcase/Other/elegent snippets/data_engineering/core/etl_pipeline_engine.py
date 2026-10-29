# Service ID: DSE28 - ETL Pipeline Automation Engine
# محرك أتمتة خطوط أنابيب ETL المتقدم

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from dataclasses import dataclass
import json
import yaml
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import schedule
import time
import threading

# Data validation and quality
from great_expectations import DataContext
from great_expectations.core.batch import RuntimeBatchRequest
import pandera as pa
from pandera import Column, DataFrameSchema, Check

# Data transformation libraries
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder
import pyjanitor  # For advanced data cleaning

logger = logging.getLogger(__name__)

@dataclass
class ETLConfig:
    """
    ETL pipeline configuration
    تكوين خط أنابيب ETL
    """
    pipeline_name: str
    source_config: Dict[str, Any]
    target_config: Dict[str, Any]
    transformation_steps: List[Dict[str, Any]]
    schedule_config: Optional[Dict[str, Any]] = None
    data_quality_checks: List[Dict[str, Any]] = None
    error_handling: Dict[str, Any] = None
    parallel_processing: bool = False
    batch_size: int = 10000

@dataclass
class ETLResult:
    """
    ETL execution result
    نتيجة تنفيذ ETL
    """
    pipeline_name: str
    execution_id: str
    status: str  # success, failed, partial
    records_processed: int
    records_loaded: int
    execution_time: float
    errors: List[str] = None
    data_quality_report: Dict[str, Any] = None
    started_at: str = None
    completed_at: str = None

class AdvancedETLPipelineEngine:
    """
    Advanced ETL pipeline automation engine
    محرك أتمتة خطوط أنابيب ETL المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.pipelines_path = workspace_path / "etl_pipelines"
        self.logs_path = workspace_path / "etl_logs"
        self.data_path = workspace_path / "etl_data"
        self.config_path = workspace_path / "etl_configs"
        
        for path in [self.pipelines_path, self.logs_path, self.data_path, self.config_path]:
            path.mkdir(exist_ok=True)
        
        self.registered_pipelines: Dict[str, ETLConfig] = {}
        self.execution_history: List[ETLResult] = []
        self.data_sources: Dict[str, Any] = {}
        self.transformations: Dict[str, Callable] = {}
        self.scheduler_thread = None
        self.is_scheduler_running = False
        
        # Register built-in transformations
        self._register_builtin_transformations()
    
    def register_pipeline(self, config: ETLConfig) -> bool:
        """
        Register ETL pipeline
        تسجيل خط أنابيب ETL
        """
        try:
            # Validate configuration
            self._validate_pipeline_config(config)
            
            # Store configuration
            self.registered_pipelines[config.pipeline_name] = config
            
            # Save configuration to file
            config_file = self.config_path / f"{config.pipeline_name}.yaml"
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config.__dict__, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Pipeline registered successfully: {config.pipeline_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register pipeline {config.pipeline_name}: {str(e)}")
            return False
    
    def execute_pipeline(self, pipeline_name: str, execution_params: Dict[str, Any] = None) -> ETLResult:
        """
        Execute ETL pipeline
        تنفيذ خط أنابيب ETL
        """
        execution_start = datetime.utcnow()
        execution_id = f"{pipeline_name}_{int(execution_start.timestamp())}"
        
        try:
            if pipeline_name not in self.registered_pipelines:
                raise ValueError(f"Pipeline not found: {pipeline_name}")
            
            config = self.registered_pipelines[pipeline_name]
            
            # Initialize result
            result = ETLResult(
                pipeline_name=pipeline_name,
                execution_id=execution_id,
                status="running",
                records_processed=0,
                records_loaded=0,
                execution_time=0,
                errors=[],
                started_at=execution_start.isoformat()
            )
            
            # Extract data
            logger.info(f"Starting extraction for pipeline: {pipeline_name}")
            extracted_data = self._extract_data(config.source_config, execution_params)
            
            if extracted_data is None or len(extracted_data) == 0:
                raise ValueError("No data extracted from source")
            
            result.records_processed = len(extracted_data)
            
            # Transform data
            logger.info(f"Starting transformation for pipeline: {pipeline_name}")
            transformed_data = self._transform_data(extracted_data, config.transformation_steps)
            
            # Data quality checks
            if config.data_quality_checks:
                logger.info(f"Running data quality checks for pipeline: {pipeline_name}")
                quality_report = self._run_data_quality_checks(transformed_data, config.data_quality_checks)
                result.data_quality_report = quality_report
                
                # Check if quality meets requirements
                if not quality_report.get('passed', True):
                    if config.error_handling and config.error_handling.get('fail_on_quality_issues', False):
                        raise ValueError("Data quality checks failed")
            
            # Load data
            logger.info(f"Starting load for pipeline: {pipeline_name}")
            loaded_records = self._load_data(transformed_data, config.target_config)
            result.records_loaded = loaded_records
            
            # Update result
            execution_end = datetime.utcnow()
            result.status = "success"
            result.execution_time = (execution_end - execution_start).total_seconds()
            result.completed_at = execution_end.isoformat()
            
            # Log execution
            self._log_execution(result)
            self.execution_history.append(result)
            
            logger.info(f"Pipeline executed successfully: {pipeline_name}")
            return result
            
        except Exception as e:
            execution_end = datetime.utcnow()
            result.status = "failed"
            result.execution_time = (execution_end - execution_start).total_seconds()
            result.completed_at = execution_end.isoformat()
            result.errors.append(str(e))
            
            self._log_execution(result)
            self.execution_history.append(result)
            
            logger.error(f"Pipeline execution failed: {pipeline_name} - {str(e)}")
            return result
    
    def _extract_data(self, source_config: Dict[str, Any], execution_params: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Extract data from various sources
        استخراج البيانات من مصادر مختلفة
        """
        source_type = source_config.get('type', '').lower()
        
        if source_type == 'database':
            return self._extract_from_database(source_config, execution_params)
        elif source_type == 'csv':
            return self._extract_from_csv(source_config)
        elif source_type == 'json':
            return self._extract_from_json(source_config)
        elif source_type == 'api':
            return self._extract_from_api(source_config, execution_params)
        elif source_type == 'excel':
            return self._extract_from_excel(source_config)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
    
    def _extract_from_database(self, config: Dict[str, Any], params: Dict[str, Any] = None) -> pd.DataFrame:
        """Extract data from database"""
        connection_string = config['connection_string']
        query = config['query']
        
        # Replace parameters in query
        if params:
            for key, value in params.items():
                query = query.replace(f"${{{key}}}", str(value))
        
        engine = create_engine(connection_string)
        return pd.read_sql(query, engine)
    
    def _extract_from_csv(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Extract data from CSV file"""
        file_path = config['file_path']
        options = config.get('options', {})
        return pd.read_csv(file_path, **options)
    
    def _extract_from_json(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Extract data from JSON file"""
        file_path = config['file_path']
        options = config.get('options', {})
        return pd.read_json(file_path, **options)
    
    def _extract_from_api(self, config: Dict[str, Any], params: Dict[str, Any] = None) -> pd.DataFrame:
        """Extract data from API"""
        import requests
        
        url = config['url']
        headers = config.get('headers', {})
        method = config.get('method', 'GET').upper()
        
        # Add parameters
        if params:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            else:
                response = requests.post(url, headers=headers, json=params)
        else:
            response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        data = response.json()
        
        # Convert to DataFrame
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict) and 'data' in data:
            return pd.DataFrame(data['data'])
        else:
            return pd.DataFrame([data])
    
    def _extract_from_excel(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Extract data from Excel file"""
        file_path = config['file_path']
        sheet_name = config.get('sheet_name', 0)
        options = config.get('options', {})
        return pd.read_excel(file_path, sheet_name=sheet_name, **options)
    
    def _transform_data(self, data: pd.DataFrame, transformation_steps: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Apply transformation steps to data
        تطبيق خطوات التحويل على البيانات
        """
        transformed_data = data.copy()
        
        for step in transformation_steps:
            step_type = step.get('type', '').lower()
            step_config = step.get('config', {})
            
            if step_type == 'filter':
                transformed_data = self._apply_filter(transformed_data, step_config)
            elif step_type == 'clean':
                transformed_data = self._apply_cleaning(transformed_data, step_config)
            elif step_type == 'aggregate':
                transformed_data = self._apply_aggregation(transformed_data, step_config)
            elif step_type == 'join':
                transformed_data = self._apply_join(transformed_data, step_config)
            elif step_type == 'custom':
                transformation_name = step_config.get('function')
                if transformation_name in self.transformations:
                    transformed_data = self.transformations[transformation_name](transformed_data, step_config)
            elif step_type == 'normalize':
                transformed_data = self._apply_normalization(transformed_data, step_config)
            elif step_type == 'encode':
                transformed_data = self._apply_encoding(transformed_data, step_config)
            
        return transformed_data
    
    def _apply_filter(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply filtering transformation"""
        conditions = config.get('conditions', [])
        
        for condition in conditions:
            column = condition['column']
            operator = condition['operator']
            value = condition['value']
            
            if operator == 'equals':
                data = data[data[column] == value]
            elif operator == 'not_equals':
                data = data[data[column] != value]
            elif operator == 'greater_than':
                data = data[data[column] > value]
            elif operator == 'less_than':
                data = data[data[column] < value]
            elif operator == 'in':
                data = data[data[column].isin(value)]
            elif operator == 'not_in':
                data = data[~data[column].isin(value)]
        
        return data
    
    def _apply_cleaning(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply data cleaning transformation"""
        # Remove duplicates
        if config.get('remove_duplicates', False):
            subset = config.get('duplicate_subset')
            data = data.drop_duplicates(subset=subset)
        
        # Handle missing values
        missing_strategy = config.get('missing_values_strategy', 'drop')
        if missing_strategy == 'drop':
            data = data.dropna()
        elif missing_strategy == 'fill':
            fill_value = config.get('fill_value', 0)
            data = data.fillna(fill_value)
        elif missing_strategy == 'forward_fill':
            data = data.fillna(method='ffill')
        elif missing_strategy == 'backward_fill':
            data = data.fillna(method='bfill')
        
        # Remove outliers
        if config.get('remove_outliers', False):
            columns = config.get('outlier_columns', data.select_dtypes(include=[np.number]).columns)
            for col in columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                data = data[(data[col] >= lower_bound) & (data[col] <= upper_bound)]
        
        return data
    
    def _apply_aggregation(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply aggregation transformation"""
        group_by = config.get('group_by', [])
        aggregations = config.get('aggregations', {})
        
        if group_by:
            return data.groupby(group_by).agg(aggregations).reset_index()
        else:
            return data.agg(aggregations).to_frame().T
    
    def _apply_join(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply join transformation"""
        right_data_source = config.get('right_source')
        join_type = config.get('join_type', 'inner')
        left_on = config.get('left_on')
        right_on = config.get('right_on')
        
        # Load right data (simplified - in practice, this would use the extraction logic)
        if isinstance(right_data_source, str):
            right_data = pd.read_csv(right_data_source)
        else:
            right_data = right_data_source
        
        return data.merge(right_data, left_on=left_on, right_on=right_on, how=join_type)
    
    def _apply_normalization(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply normalization transformation"""
        columns = config.get('columns', data.select_dtypes(include=[np.number]).columns)
        method = config.get('method', 'standard')
        
        if method == 'standard':
            scaler = StandardScaler()
        elif method == 'minmax':
            scaler = MinMaxScaler()
        else:
            return data
        
        data[columns] = scaler.fit_transform(data[columns])
        return data
    
    def _apply_encoding(self, data: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Apply encoding transformation"""
        columns = config.get('columns', data.select_dtypes(include=['object']).columns)
        method = config.get('method', 'label')
        
        for col in columns:
            if method == 'label':
                le = LabelEncoder()
                data[col] = le.fit_transform(data[col].astype(str))
            elif method == 'onehot':
                dummies = pd.get_dummies(data[col], prefix=col)
                data = pd.concat([data.drop(col, axis=1), dummies], axis=1)
        
        return data
    
    def _load_data(self, data: pd.DataFrame, target_config: Dict[str, Any]) -> int:
        """
        Load data to target destination
        تحميل البيانات إلى الوجهة المستهدفة
        """
        target_type = target_config.get('type', '').lower()
        
        if target_type == 'database':
            return self._load_to_database(data, target_config)
        elif target_type == 'csv':
            return self._load_to_csv(data, target_config)
        elif target_type == 'json':
            return self._load_to_json(data, target_config)
        elif target_type == 'parquet':
            return self._load_to_parquet(data, target_config)
        else:
            raise ValueError(f"Unsupported target type: {target_type}")
    
    def _load_to_database(self, data: pd.DataFrame, config: Dict[str, Any]) -> int:
        """Load data to database"""
        connection_string = config['connection_string']
        table_name = config['table_name']
        if_exists = config.get('if_exists', 'append')
        
        engine = create_engine(connection_string)
        data.to_sql(table_name, engine, if_exists=if_exists, index=False)
        return len(data)
    
    def _load_to_csv(self, data: pd.DataFrame, config: Dict[str, Any]) -> int:
        """Load data to CSV file"""
        file_path = config['file_path']
        options = config.get('options', {})
        data.to_csv(file_path, index=False, **options)
        return len(data)
    
    def _load_to_json(self, data: pd.DataFrame, config: Dict[str, Any]) -> int:
        """Load data to JSON file"""
        file_path = config['file_path']
        orient = config.get('orient', 'records')
        data.to_json(file_path, orient=orient, indent=2)
        return len(data)
    
    def _load_to_parquet(self, data: pd.DataFrame, config: Dict[str, Any]) -> int:
        """Load data to Parquet file"""
        file_path = config['file_path']
        data.to_parquet(file_path, index=False)
        return len(data)
    
    def _run_data_quality_checks(self, data: pd.DataFrame, checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run data quality checks
        تشغيل فحوصات جودة البيانات
        """
        quality_report = {
            'total_checks': len(checks),
            'passed_checks': 0,
            'failed_checks': 0,
            'check_results': [],
            'passed': True
        }
        
        for check in checks:
            check_type = check.get('type', '').lower()
            check_config = check.get('config', {})
            
            try:
                if check_type == 'completeness':
                    result = self._check_completeness(data, check_config)
                elif check_type == 'uniqueness':
                    result = self._check_uniqueness(data, check_config)
                elif check_type == 'range':
                    result = self._check_range(data, check_config)
                elif check_type == 'format':
                    result = self._check_format(data, check_config)
                else:
                    result = {'passed': False, 'message': f'Unknown check type: {check_type}'}
                
                quality_report['check_results'].append({
                    'type': check_type,
                    'config': check_config,
                    'result': result
                })
                
                if result['passed']:
                    quality_report['passed_checks'] += 1
                else:
                    quality_report['failed_checks'] += 1
                    quality_report['passed'] = False
                    
            except Exception as e:
                quality_report['check_results'].append({
                    'type': check_type,
                    'config': check_config,
                    'result': {'passed': False, 'message': f'Check failed: {str(e)}'}
                })
                quality_report['failed_checks'] += 1
                quality_report['passed'] = False
        
        return quality_report
    
    def _check_completeness(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check data completeness"""
        columns = config.get('columns', data.columns)
        threshold = config.get('threshold', 0.95)
        
        for col in columns:
            completeness = 1 - (data[col].isnull().sum() / len(data))
            if completeness < threshold:
                return {
                    'passed': False,
                    'message': f'Column {col} completeness {completeness:.2%} below threshold {threshold:.2%}'
                }
        
        return {'passed': True, 'message': 'All columns meet completeness requirements'}
    
    def _check_uniqueness(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check data uniqueness"""
        columns = config.get('columns', [])
        
        for col in columns:
            duplicates = data[col].duplicated().sum()
            if duplicates > 0:
                return {
                    'passed': False,
                    'message': f'Column {col} has {duplicates} duplicate values'
                }
        
        return {'passed': True, 'message': 'All columns meet uniqueness requirements'}
    
    def _check_range(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check data range"""
        column = config.get('column')
        min_value = config.get('min_value')
        max_value = config.get('max_value')
        
        if min_value is not None:
            violations = (data[column] < min_value).sum()
            if violations > 0:
                return {
                    'passed': False,
                    'message': f'Column {column} has {violations} values below minimum {min_value}'
                }
        
        if max_value is not None:
            violations = (data[column] > max_value).sum()
            if violations > 0:
                return {
                    'passed': False,
                    'message': f'Column {column} has {violations} values above maximum {max_value}'
                }
        
        return {'passed': True, 'message': f'Column {column} values within acceptable range'}
    
    def _check_format(self, data: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check data format"""
        column = config.get('column')
        pattern = config.get('pattern')
        
        import re
        violations = ~data[column].astype(str).str.match(pattern)
        violation_count = violations.sum()
        
        if violation_count > 0:
            return {
                'passed': False,
                'message': f'Column {column} has {violation_count} values not matching pattern {pattern}'
            }
        
        return {'passed': True, 'message': f'Column {column} values match required format'}
    
    def _register_builtin_transformations(self):
        """Register built-in transformation functions"""
        self.transformations['remove_duplicates'] = lambda df, config: df.drop_duplicates()
        self.transformations['fill_missing'] = lambda df, config: df.fillna(config.get('value', 0))
        self.transformations['uppercase'] = lambda df, config: df.apply(lambda x: x.str.upper() if x.dtype == 'object' else x)
    
    def _validate_pipeline_config(self, config: ETLConfig):
        """Validate pipeline configuration"""
        if not config.pipeline_name:
            raise ValueError("Pipeline name is required")
        
        if not config.source_config:
            raise ValueError("Source configuration is required")
        
        if not config.target_config:
            raise ValueError("Target configuration is required")
    
    def _log_execution(self, result: ETLResult):
        """Log pipeline execution"""
        log_file = self.logs_path / f"{result.pipeline_name}_{datetime.utcnow().strftime('%Y%m%d')}.log"
        
        log_entry = {
            'execution_id': result.execution_id,
            'status': result.status,
            'records_processed': result.records_processed,
            'records_loaded': result.records_loaded,
            'execution_time': result.execution_time,
            'errors': result.errors,
            'started_at': result.started_at,
            'completed_at': result.completed_at
        }
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """
        Get ETL pipeline statistics
        الحصول على إحصائيات خطوط أنابيب ETL
        """
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0,
                'average_execution_time': 0
            }
        
        total_executions = len(self.execution_history)
        successful_executions = len([r for r in self.execution_history if r.status == 'success'])
        success_rate = (successful_executions / total_executions) * 100
        
        execution_times = [r.execution_time for r in self.execution_history]
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        total_records_processed = sum([r.records_processed for r in self.execution_history])
        total_records_loaded = sum([r.records_loaded for r in self.execution_history])
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': total_executions - successful_executions,
            'success_rate': success_rate,
            'average_execution_time': avg_execution_time,
            'total_records_processed': total_records_processed,
            'total_records_loaded': total_records_loaded,
            'registered_pipelines': len(self.registered_pipelines),
            'generated_at': datetime.utcnow().isoformat()
        }
