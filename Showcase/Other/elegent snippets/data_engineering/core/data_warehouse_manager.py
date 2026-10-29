# Service ID: DSE42 - Data Warehouse Management Engine
# محرك إدارة مستودع البيانات المتقدم

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json
import yaml
from concurrent.futures import ThreadPoolExecutor
import threading

# Data modeling and schema management
from sqlalchemy.schema import CreateTable, DropTable
from sqlalchemy.types import TypeDecorator, VARCHAR
import sqlalchemy.dialects.postgresql as postgresql
import sqlalchemy.dialects.mysql as mysql

# Data quality and profiling
import pandas_profiling
from great_expectations import DataContext
from great_expectations.core.batch import RuntimeBatchRequest

logger = logging.getLogger(__name__)

@dataclass
class WarehouseConfig:
    """
    Data warehouse configuration
    تكوين مستودع البيانات
    """
    warehouse_name: str
    connection_config: Dict[str, Any]
    schema_config: Dict[str, Any]
    etl_config: Dict[str, Any] = None
    backup_config: Dict[str, Any] = None
    monitoring_config: Dict[str, Any] = None

@dataclass
class TableSchema:
    """
    Table schema definition
    تعريف مخطط الجدول
    """
    table_name: str
    columns: List[Dict[str, Any]]
    primary_key: List[str] = None
    foreign_keys: List[Dict[str, Any]] = None
    indexes: List[Dict[str, Any]] = None
    partitioning: Dict[str, Any] = None

@dataclass
class DataQualityReport:
    """
    Data quality assessment report
    تقرير تقييم جودة البيانات
    """
    table_name: str
    total_records: int
    quality_score: float
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    consistency_score: float
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: str

class AdvancedDataWarehouseManager:
    """
    Advanced data warehouse management engine
    محرك إدارة مستودع البيانات المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.schemas_path = workspace_path / "warehouse_schemas"
        self.backups_path = workspace_path / "warehouse_backups"
        self.reports_path = workspace_path / "warehouse_reports"
        self.logs_path = workspace_path / "warehouse_logs"
        
        for path in [self.schemas_path, self.backups_path, self.reports_path, self.logs_path]:
            path.mkdir(exist_ok=True)
        
        self.warehouses: Dict[str, WarehouseConfig] = {}
        self.engines: Dict[str, Any] = {}
        self.metadata_objects: Dict[str, MetaData] = {}
        self.table_schemas: Dict[str, List[TableSchema]] = {}
        self.monitoring_stats: Dict[str, Dict[str, Any]] = {}
    
    def register_warehouse(self, config: WarehouseConfig) -> bool:
        """
        Register data warehouse configuration
        تسجيل تكوين مستودع البيانات
        """
        try:
            # Validate configuration
            self._validate_warehouse_config(config)
            
            # Create database engine
            engine = self._create_engine(config.connection_config)
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Store configuration and engine
            self.warehouses[config.warehouse_name] = config
            self.engines[config.warehouse_name] = engine
            self.metadata_objects[config.warehouse_name] = MetaData()
            self.table_schemas[config.warehouse_name] = []
            
            # Initialize monitoring
            self.monitoring_stats[config.warehouse_name] = {
                'created_at': datetime.utcnow().isoformat(),
                'total_tables': 0,
                'total_records': 0,
                'last_backup': None,
                'last_quality_check': None
            }
            
            logger.info(f"Data warehouse registered successfully: {config.warehouse_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register warehouse {config.warehouse_name}: {str(e)}")
            return False
    
    def create_schema(self, warehouse_name: str, schema_definition: TableSchema) -> bool:
        """
        Create table schema in data warehouse
        إنشاء مخطط الجدول في مستودع البيانات
        """
        try:
            if warehouse_name not in self.warehouses:
                raise ValueError(f"Warehouse not found: {warehouse_name}")
            
            engine = self.engines[warehouse_name]
            metadata = self.metadata_objects[warehouse_name]
            
            # Build SQLAlchemy table definition
            columns = []
            for col_def in schema_definition.columns:
                col_type = self._get_sqlalchemy_type(col_def['type'], col_def.get('length'))
                column = Column(
                    col_def['name'],
                    col_type,
                    nullable=col_def.get('nullable', True),
                    default=col_def.get('default'),
                    unique=col_def.get('unique', False)
                )
                columns.append(column)
            
            # Create table object
            table = Table(
                schema_definition.table_name,
                metadata,
                *columns,
                extend_existing=True
            )
            
            # Add primary key
            if schema_definition.primary_key:
                table.primary_key.columns.update([table.c[col] for col in schema_definition.primary_key])
            
            # Create table in database
            table.create(engine, checkfirst=True)
            
            # Create indexes
            if schema_definition.indexes:
                self._create_indexes(engine, schema_definition)
            
            # Store schema definition
            self.table_schemas[warehouse_name].append(schema_definition)
            
            # Update monitoring stats
            self.monitoring_stats[warehouse_name]['total_tables'] += 1
            
            # Save schema to file
            self._save_schema_definition(warehouse_name, schema_definition)
            
            logger.info(f"Schema created successfully: {schema_definition.table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create schema {schema_definition.table_name}: {str(e)}")
            return False
    
    def load_data(self, warehouse_name: str, table_name: str, data: pd.DataFrame, 
                  load_method: str = "append") -> bool:
        """
        Load data into warehouse table
        تحميل البيانات في جدول المستودع
        """
        try:
            if warehouse_name not in self.warehouses:
                raise ValueError(f"Warehouse not found: {warehouse_name}")
            
            engine = self.engines[warehouse_name]
            
            # Validate data against schema
            schema = self._get_table_schema(warehouse_name, table_name)
            if schema:
                validated_data = self._validate_data_against_schema(data, schema)
            else:
                validated_data = data
            
            # Load data
            if load_method == "replace":
                validated_data.to_sql(table_name, engine, if_exists="replace", index=False)
            elif load_method == "append":
                validated_data.to_sql(table_name, engine, if_exists="append", index=False)
            elif load_method == "upsert":
                self._upsert_data(engine, table_name, validated_data, schema)
            
            # Update monitoring stats
            self.monitoring_stats[warehouse_name]['total_records'] += len(validated_data)
            
            logger.info(f"Data loaded successfully: {len(validated_data)} records to {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data to {table_name}: {str(e)}")
            return False
    
    def query_data(self, warehouse_name: str, query: str, params: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Execute query against warehouse
        تنفيذ استعلام ضد المستودع
        """
        try:
            if warehouse_name not in self.warehouses:
                raise ValueError(f"Warehouse not found: {warehouse_name}")
            
            engine = self.engines[warehouse_name]
            
            # Execute query
            if params:
                result = pd.read_sql(text(query), engine, params=params)
            else:
                result = pd.read_sql(query, engine)
            
            logger.info(f"Query executed successfully: {len(result)} records returned")
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return pd.DataFrame()
    
    def analyze_data_quality(self, warehouse_name: str, table_name: str) -> DataQualityReport:
        """
        Analyze data quality for a table
        تحليل جودة البيانات لجدول
        """
        try:
            if warehouse_name not in self.warehouses:
                raise ValueError(f"Warehouse not found: {warehouse_name}")
            
            # Load table data
            data = self.query_data(warehouse_name, f"SELECT * FROM {table_name}")
            
            if data.empty:
                return DataQualityReport(
                    table_name=table_name,
                    total_records=0,
                    quality_score=0.0,
                    completeness_score=0.0,
                    uniqueness_score=0.0,
                    validity_score=0.0,
                    consistency_score=0.0,
                    issues_found=[],
                    recommendations=["Table is empty"],
                    generated_at=datetime.utcnow().isoformat()
                )
            
            # Calculate quality metrics
            total_records = len(data)
            issues_found = []
            recommendations = []
            
            # Completeness analysis
            completeness_scores = []
            for col in data.columns:
                null_count = data[col].isnull().sum()
                completeness = 1 - (null_count / total_records)
                completeness_scores.append(completeness)
                
                if completeness < 0.95:
                    issues_found.append({
                        'type': 'completeness',
                        'column': col,
                        'issue': f'High null rate: {null_count}/{total_records} ({(1-completeness)*100:.1f}%)',
                        'severity': 'high' if completeness < 0.8 else 'medium'
                    })
                    recommendations.append(f"Investigate missing values in column '{col}'")
            
            completeness_score = np.mean(completeness_scores)
            
            # Uniqueness analysis
            uniqueness_scores = []
            for col in data.columns:
                unique_count = data[col].nunique()
                uniqueness = unique_count / total_records
                uniqueness_scores.append(uniqueness)
                
                # Check for unexpected duplicates in key columns
                if col.lower() in ['id', 'key', 'code'] and uniqueness < 0.95:
                    issues_found.append({
                        'type': 'uniqueness',
                        'column': col,
                        'issue': f'Duplicate values in key column: {total_records - unique_count} duplicates',
                        'severity': 'high'
                    })
                    recommendations.append(f"Remove or investigate duplicate values in '{col}'")
            
            uniqueness_score = np.mean(uniqueness_scores)
            
            # Validity analysis (data type consistency)
            validity_scores = []
            schema = self._get_table_schema(warehouse_name, table_name)
            
            if schema:
                for col_def in schema.columns:
                    col_name = col_def['name']
                    expected_type = col_def['type']
                    
                    if col_name in data.columns:
                        validity = self._check_data_type_validity(data[col_name], expected_type)
                        validity_scores.append(validity)
                        
                        if validity < 0.95:
                            issues_found.append({
                                'type': 'validity',
                                'column': col_name,
                                'issue': f'Data type inconsistency: expected {expected_type}',
                                'severity': 'medium'
                            })
                            recommendations.append(f"Validate data types for column '{col_name}'")
            
            validity_score = np.mean(validity_scores) if validity_scores else 1.0
            
            # Consistency analysis (outliers and anomalies)
            consistency_scores = []
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for col in numeric_columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = ((data[col] < lower_bound) | (data[col] > upper_bound)).sum()
                consistency = 1 - (outliers / total_records)
                consistency_scores.append(consistency)
                
                if outliers > total_records * 0.05:  # More than 5% outliers
                    issues_found.append({
                        'type': 'consistency',
                        'column': col,
                        'issue': f'High outlier rate: {outliers} outliers ({outliers/total_records*100:.1f}%)',
                        'severity': 'medium'
                    })
                    recommendations.append(f"Investigate outliers in column '{col}'")
            
            consistency_score = np.mean(consistency_scores) if consistency_scores else 1.0
            
            # Calculate overall quality score
            quality_score = (completeness_score + uniqueness_score + validity_score + consistency_score) / 4
            
            # Create report
            report = DataQualityReport(
                table_name=table_name,
                total_records=total_records,
                quality_score=quality_score,
                completeness_score=completeness_score,
                uniqueness_score=uniqueness_score,
                validity_score=validity_score,
                consistency_score=consistency_score,
                issues_found=issues_found,
                recommendations=recommendations,
                generated_at=datetime.utcnow().isoformat()
            )
            
            # Save report
            self._save_quality_report(warehouse_name, report)
            
            # Update monitoring stats
            self.monitoring_stats[warehouse_name]['last_quality_check'] = datetime.utcnow().isoformat()
            
            logger.info(f"Data quality analysis completed for {table_name}: {quality_score:.2%} quality score")
            return report
            
        except Exception as e:
            logger.error(f"Data quality analysis failed for {table_name}: {str(e)}")
            raise
    
    def create_backup(self, warehouse_name: str, backup_type: str = "full") -> bool:
        """
        Create warehouse backup
        إنشاء نسخة احتياطية من المستودع
        """
        try:
            if warehouse_name not in self.warehouses:
                raise ValueError(f"Warehouse not found: {warehouse_name}")
            
            backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_dir = self.backups_path / f"{warehouse_name}_{backup_timestamp}"
            backup_dir.mkdir(exist_ok=True)
            
            engine = self.engines[warehouse_name]
            
            if backup_type == "full":
                # Export all tables
                tables = self._get_all_tables(warehouse_name)
                
                for table_name in tables:
                    data = self.query_data(warehouse_name, f"SELECT * FROM {table_name}")
                    
                    # Save as parquet for efficiency
                    backup_file = backup_dir / f"{table_name}.parquet"
                    data.to_parquet(backup_file, index=False)
                
                # Save schema definitions
                schema_file = backup_dir / "schemas.json"
                schemas_data = [schema.__dict__ for schema in self.table_schemas[warehouse_name]]
                with open(schema_file, 'w', encoding='utf-8') as f:
                    json.dump(schemas_data, f, indent=2, ensure_ascii=False, default=str)
            
            elif backup_type == "schema_only":
                # Export only schema definitions
                schema_file = backup_dir / "schemas.json"
                schemas_data = [schema.__dict__ for schema in self.table_schemas[warehouse_name]]
                with open(schema_file, 'w', encoding='utf-8') as f:
                    json.dump(schemas_data, f, indent=2, ensure_ascii=False, default=str)
            
            # Create backup metadata
            metadata = {
                'warehouse_name': warehouse_name,
                'backup_type': backup_type,
                'backup_timestamp': backup_timestamp,
                'created_at': datetime.utcnow().isoformat(),
                'tables_backed_up': len(self.table_schemas[warehouse_name]),
                'backup_size_mb': sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file()) / (1024 * 1024)
            }
            
            metadata_file = backup_dir / "backup_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Update monitoring stats
            self.monitoring_stats[warehouse_name]['last_backup'] = datetime.utcnow().isoformat()
            
            logger.info(f"Backup created successfully: {backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Backup creation failed for {warehouse_name}: {str(e)}")
            return False
    
    def optimize_warehouse(self, warehouse_name: str) -> Dict[str, Any]:
        """
        Optimize warehouse performance
        تحسين أداء المستودع
        """
        try:
            if warehouse_name not in self.warehouses:
                raise ValueError(f"Warehouse not found: {warehouse_name}")
            
            engine = self.engines[warehouse_name]
            optimization_results = {
                'warehouse_name': warehouse_name,
                'optimizations_applied': [],
                'performance_improvements': {},
                'recommendations': [],
                'optimized_at': datetime.utcnow().isoformat()
            }
            
            # Analyze table statistics
            tables = self._get_all_tables(warehouse_name)
            
            for table_name in tables:
                # Get table statistics
                stats_query = f"""
                SELECT 
                    COUNT(*) as row_count,
                    COUNT(DISTINCT *) as distinct_rows
                FROM {table_name}
                """
                
                try:
                    stats = self.query_data(warehouse_name, stats_query)
                    row_count = stats.iloc[0]['row_count']
                    
                    # Suggest partitioning for large tables
                    if row_count > 1000000:
                        optimization_results['recommendations'].append(
                            f"Consider partitioning table '{table_name}' (contains {row_count:,} rows)"
                        )
                    
                    # Check for missing indexes on large tables
                    if row_count > 100000:
                        schema = self._get_table_schema(warehouse_name, table_name)
                        if schema and not schema.indexes:
                            optimization_results['recommendations'].append(
                                f"Add indexes to table '{table_name}' for better query performance"
                            )
                
                except Exception as e:
                    logger.warning(f"Could not analyze table {table_name}: {str(e)}")
            
            # Database-specific optimizations
            db_type = self._get_database_type(engine)
            
            if db_type == 'postgresql':
                # PostgreSQL specific optimizations
                try:
                    # Analyze tables for better query planning
                    with engine.connect() as conn:
                        for table_name in tables:
                            conn.execute(text(f"ANALYZE {table_name}"))
                    
                    optimization_results['optimizations_applied'].append("PostgreSQL ANALYZE executed")
                    
                except Exception as e:
                    logger.warning(f"PostgreSQL optimization failed: {str(e)}")
            
            elif db_type == 'mysql':
                # MySQL specific optimizations
                try:
                    with engine.connect() as conn:
                        for table_name in tables:
                            conn.execute(text(f"OPTIMIZE TABLE {table_name}"))
                    
                    optimization_results['optimizations_applied'].append("MySQL OPTIMIZE TABLE executed")
                    
                except Exception as e:
                    logger.warning(f"MySQL optimization failed: {str(e)}")
            
            # General recommendations
            optimization_results['recommendations'].extend([
                "Regularly update table statistics",
                "Monitor query performance and add indexes as needed",
                "Consider archiving old data to improve performance",
                "Implement data compression for large tables"
            ])
            
            logger.info(f"Warehouse optimization completed for {warehouse_name}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Warehouse optimization failed for {warehouse_name}: {str(e)}")
            return {}
    
    def _create_engine(self, connection_config: Dict[str, Any]):
        """Create SQLAlchemy engine from configuration"""
        db_type = connection_config.get('type', 'postgresql')
        host = connection_config.get('host', 'localhost')
        port = connection_config.get('port', 5432)
        database = connection_config.get('database')
        username = connection_config.get('username')
        password = connection_config.get('password')
        
        if db_type == 'postgresql':
            connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'mysql':
            connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'sqlite':
            connection_string = f"sqlite:///{database}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        return create_engine(connection_string, pool_pre_ping=True)
    
    def _get_sqlalchemy_type(self, type_name: str, length: int = None):
        """Convert string type to SQLAlchemy type"""
        type_mapping = {
            'integer': Integer,
            'string': String(length) if length else String(255),
            'text': Text,
            'float': Float,
            'boolean': Boolean,
            'datetime': DateTime
        }
        
        return type_mapping.get(type_name.lower(), String(255))
    
    def _get_table_schema(self, warehouse_name: str, table_name: str) -> Optional[TableSchema]:
        """Get table schema definition"""
        schemas = self.table_schemas.get(warehouse_name, [])
        for schema in schemas:
            if schema.table_name == table_name:
                return schema
        return None
    
    def _get_all_tables(self, warehouse_name: str) -> List[str]:
        """Get list of all tables in warehouse"""
        engine = self.engines[warehouse_name]
        metadata = MetaData()
        metadata.reflect(bind=engine)
        return list(metadata.tables.keys())
    
    def _get_database_type(self, engine) -> str:
        """Get database type from engine"""
        dialect_name = engine.dialect.name.lower()
        if 'postgresql' in dialect_name:
            return 'postgresql'
        elif 'mysql' in dialect_name:
            return 'mysql'
        elif 'sqlite' in dialect_name:
            return 'sqlite'
        else:
            return 'unknown'
    
    def _validate_warehouse_config(self, config: WarehouseConfig):
        """Validate warehouse configuration"""
        if not config.warehouse_name:
            raise ValueError("Warehouse name is required")
        
        if not config.connection_config:
            raise ValueError("Connection configuration is required")
        
        required_conn_fields = ['type', 'database']
        for field in required_conn_fields:
            if field not in config.connection_config:
                raise ValueError(f"Connection configuration missing required field: {field}")
    
    def _validate_data_against_schema(self, data: pd.DataFrame, schema: TableSchema) -> pd.DataFrame:
        """Validate data against table schema"""
        validated_data = data.copy()
        
        # Check required columns
        schema_columns = [col['name'] for col in schema.columns]
        missing_columns = set(schema_columns) - set(data.columns)
        
        if missing_columns:
            logger.warning(f"Missing columns in data: {missing_columns}")
            # Add missing columns with default values
            for col_name in missing_columns:
                col_def = next(col for col in schema.columns if col['name'] == col_name)
                default_value = col_def.get('default')
                validated_data[col_name] = default_value
        
        # Remove extra columns not in schema
        extra_columns = set(data.columns) - set(schema_columns)
        if extra_columns:
            logger.warning(f"Extra columns in data (will be removed): {extra_columns}")
            validated_data = validated_data.drop(columns=extra_columns)
        
        return validated_data
    
    def _check_data_type_validity(self, series: pd.Series, expected_type: str) -> float:
        """Check data type validity for a series"""
        try:
            if expected_type.lower() == 'integer':
                # Check if values can be converted to integer
                valid_count = pd.to_numeric(series, errors='coerce').notna().sum()
            elif expected_type.lower() == 'float':
                # Check if values can be converted to float
                valid_count = pd.to_numeric(series, errors='coerce').notna().sum()
            elif expected_type.lower() == 'datetime':
                # Check if values can be converted to datetime
                valid_count = pd.to_datetime(series, errors='coerce').notna().sum()
            else:
                # For string types, all non-null values are valid
                valid_count = series.notna().sum()
            
            return valid_count / len(series) if len(series) > 0 else 1.0
            
        except Exception:
            return 0.0
    
    def _save_schema_definition(self, warehouse_name: str, schema: TableSchema):
        """Save schema definition to file"""
        schema_file = self.schemas_path / f"{warehouse_name}_{schema.table_name}.json"
        
        with open(schema_file, 'w', encoding='utf-8') as f:
            json.dump(schema.__dict__, f, indent=2, ensure_ascii=False, default=str)
    
    def _save_quality_report(self, warehouse_name: str, report: DataQualityReport):
        """Save data quality report to file"""
        report_file = self.reports_path / f"{warehouse_name}_{report.table_name}_quality_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report.__dict__, f, indent=2, ensure_ascii=False, default=str)
    
    def get_warehouse_statistics(self) -> Dict[str, Any]:
        """
        Get data warehouse management statistics
        الحصول على إحصائيات إدارة مستودع البيانات
        """
        total_warehouses = len(self.warehouses)
        total_tables = sum(stats.get('total_tables', 0) for stats in self.monitoring_stats.values())
        total_records = sum(stats.get('total_records', 0) for stats in self.monitoring_stats.values())
        
        # Calculate average quality scores from recent reports
        quality_scores = []
        for report_file in self.reports_path.glob("*_quality_*.json"):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    quality_scores.append(report_data.get('quality_score', 0))
            except Exception:
                continue
        
        avg_quality_score = np.mean(quality_scores) if quality_scores else 0
        
        return {
            'total_warehouses': total_warehouses,
            'total_tables': total_tables,
            'total_records': total_records,
            'average_quality_score': avg_quality_score,
            'warehouses_with_recent_backups': len([
                w for w, stats in self.monitoring_stats.items() 
                if stats.get('last_backup')
            ]),
            'warehouses_with_recent_quality_checks': len([
                w for w, stats in self.monitoring_stats.items() 
                if stats.get('last_quality_check')
            ]),
            'generated_at': datetime.utcnow().isoformat()
        }
