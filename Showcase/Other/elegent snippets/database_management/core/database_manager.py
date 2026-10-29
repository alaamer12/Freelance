# Service ID: DBX53 - Part 1
# Advanced Database Management and Optimization
# إدارة وتحسين قواعد البيانات المتقدمة

import sqlite3
import psycopg2
import pymongo
import redis
import mysql.connector
import time
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.orm import sessionmaker
import schedule

logger = logging.getLogger(__name__)

# ==================== SECTION 1: Database Connection Management ====================

@dataclass
class DatabaseConfig:
    """
    Database connection configuration
    تكوين اتصال قاعدة البيانات
    """
    name: str
    db_type: str  # sqlite, postgresql, mysql, mongodb, redis
    host: str = "localhost"
    port: int = None
    database: str = None
    username: str = None
    password: str = None
    connection_params: Dict[str, Any] = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    ssl_enabled: bool = False
    ssl_cert_path: str = None

@dataclass
class QueryResult:
    """
    Database query result wrapper
    غلاف نتيجة استعلام قاعدة البيانات
    """
    success: bool
    data: Any = None
    rows_affected: int = 0
    execution_time: float = 0.0
    error_message: str = None
    query: str = None
    timestamp: str = None

class DatabaseManager:
    """
    Advanced multi-database management system with connection pooling and optimization
    نظام إدارة قواعد البيانات المتعددة المتقدم مع تجميع الاتصالات والتحسين
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.configs_path = workspace_path / "database_configs"
        self.backups_path = workspace_path / "database_backups"
        self.logs_path = workspace_path / "database_logs"
        
        # Create directories
        for path in [self.configs_path, self.backups_path, self.logs_path]:
            path.mkdir(exist_ok=True)
        
        self.database_configs: Dict[str, DatabaseConfig] = {}
        self.connection_pools: Dict[str, Any] = {}
        self.query_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, List[Dict[str, Any]]] = {}
        
        # Monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Query cache
        self.query_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes default TTL
    
    def add_database_config(self, config: DatabaseConfig) -> bool:
        """
        Add database configuration
        إضافة تكوين قاعدة البيانات
        """
        try:
            # Validate configuration
            self._validate_config(config)
            
            # Store configuration
            self.database_configs[config.name] = config
            
            # Save to file
            self._save_config(config)
            
            # Initialize connection pool
            self._initialize_connection_pool(config)
            
            logger.info(f"Database configuration added: {config.name} ({config.db_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add database config {config.name}: {str(e)}")
            return False
    
    def _validate_config(self, config: DatabaseConfig):
        """
        Validate database configuration
        التحقق من صحة تكوين قاعدة البيانات
        """
        if not config.name:
            raise ValueError("Database name is required")
        
        if config.db_type not in ['sqlite', 'postgresql', 'mysql', 'mongodb', 'redis']:
            raise ValueError(f"Unsupported database type: {config.db_type}")
        
        # Set default ports
        if config.port is None:
            default_ports = {
                'postgresql': 5432,
                'mysql': 3306,
                'mongodb': 27017,
                'redis': 6379
            }
            config.port = default_ports.get(config.db_type)
        
        # Validate required fields for each database type
        if config.db_type in ['postgresql', 'mysql']:
            if not all([config.host, config.database, config.username]):
                raise ValueError(f"Host, database, and username required for {config.db_type}")
        
        elif config.db_type == 'sqlite':
            if not config.database:
                raise ValueError("Database file path required for SQLite")
    
    def _initialize_connection_pool(self, config: DatabaseConfig):
        """
        Initialize connection pool for database
        تهيئة مجموعة الاتصالات لقاعدة البيانات
        """
        try:
            if config.db_type == 'sqlite':
                # SQLite doesn't use connection pooling in the traditional sense
                self.connection_pools[config.name] = {
                    'type': 'sqlite',
                    'database_path': config.database
                }
            
            elif config.db_type == 'postgresql':
                connection_string = self._build_connection_string(config)
                engine = create_engine(
                    connection_string,
                    pool_size=config.pool_size,
                    max_overflow=config.max_overflow,
                    pool_timeout=config.pool_timeout,
                    pool_pre_ping=True
                )
                
                self.connection_pools[config.name] = {
                    'type': 'postgresql',
                    'engine': engine,
                    'session_factory': sessionmaker(bind=engine)
                }
            
            elif config.db_type == 'mysql':
                connection_string = self._build_connection_string(config)
                engine = create_engine(
                    connection_string,
                    pool_size=config.pool_size,
                    max_overflow=config.max_overflow,
                    pool_timeout=config.pool_timeout,
                    pool_pre_ping=True
                )
                
                self.connection_pools[config.name] = {
                    'type': 'mysql',
                    'engine': engine,
                    'session_factory': sessionmaker(bind=engine)
                }
            
            elif config.db_type == 'mongodb':
                from pymongo import MongoClient
                
                connection_string = f"mongodb://{config.host}:{config.port}/"
                if config.username and config.password:
                    connection_string = f"mongodb://{config.username}:{config.password}@{config.host}:{config.port}/"
                
                client = MongoClient(
                    connection_string,
                    maxPoolSize=config.pool_size,
                    serverSelectionTimeoutMS=config.pool_timeout * 1000
                )
                
                self.connection_pools[config.name] = {
                    'type': 'mongodb',
                    'client': client,
                    'database': client[config.database] if config.database else None
                }
            
            elif config.db_type == 'redis':
                import redis
                
                pool = redis.ConnectionPool(
                    host=config.host,
                    port=config.port,
                    password=config.password,
                    max_connections=config.pool_size,
                    socket_timeout=config.pool_timeout
                )
                
                self.connection_pools[config.name] = {
                    'type': 'redis',
                    'pool': pool,
                    'client': redis.Redis(connection_pool=pool)
                }
            
            logger.info(f"Connection pool initialized for {config.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool for {config.name}: {str(e)}")
            raise
    
    def _build_connection_string(self, config: DatabaseConfig) -> str:
        """
        Build database connection string
        بناء سلسلة اتصال قاعدة البيانات
        """
        if config.db_type == 'postgresql':
            conn_str = f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        elif config.db_type == 'mysql':
            conn_str = f"mysql+pymysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
        else:
            raise ValueError(f"Connection string not supported for {config.db_type}")
        
        # Add SSL parameters if enabled
        if config.ssl_enabled:
            conn_str += "?sslmode=require"
            if config.ssl_cert_path:
                conn_str += f"&sslcert={config.ssl_cert_path}"
        
        return conn_str
    
    @contextmanager
    def get_connection(self, database_name: str):
        """
        Get database connection with context manager
        الحصول على اتصال قاعدة البيانات مع مدير السياق
        """
        if database_name not in self.connection_pools:
            raise ValueError(f"Database not configured: {database_name}")
        
        pool_info = self.connection_pools[database_name]
        connection = None
        
        try:
            if pool_info['type'] == 'sqlite':
                connection = sqlite3.connect(pool_info['database_path'])
                connection.row_factory = sqlite3.Row  # Enable column access by name
                yield connection
            
            elif pool_info['type'] in ['postgresql', 'mysql']:
                connection = pool_info['engine'].connect()
                yield connection
            
            elif pool_info['type'] == 'mongodb':
                yield pool_info['database']
            
            elif pool_info['type'] == 'redis':
                yield pool_info['client']
            
        except Exception as e:
            logger.error(f"Database connection error for {database_name}: {str(e)}")
            raise
        
        finally:
            if connection and pool_info['type'] in ['sqlite', 'postgresql', 'mysql']:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {str(e)}")
    
    def execute_query(self, database_name: str, query: str, 
                     parameters: Dict[str, Any] = None, 
                     fetch_results: bool = True) -> QueryResult:
        """
        Execute SQL query with performance tracking
        تنفيذ استعلام SQL مع تتبع الأداء
        """
        start_time = time.time()
        query_hash = hashlib.md5(f"{query}{parameters}".encode()).hexdigest()
        
        # Check cache first
        if fetch_results and query_hash in self.query_cache:
            cache_entry = self.query_cache[query_hash]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                logger.debug(f"Query result served from cache: {query_hash[:8]}")
                return cache_entry['result']
        
        try:
            with self.get_connection(database_name) as conn:
                pool_info = self.connection_pools[database_name]
                
                if pool_info['type'] == 'sqlite':
                    cursor = conn.cursor()
                    
                    if parameters:
                        cursor.execute(query, parameters)
                    else:
                        cursor.execute(query)
                    
                    if fetch_results:
                        data = [dict(row) for row in cursor.fetchall()]
                        rows_affected = len(data)
                    else:
                        data = None
                        rows_affected = cursor.rowcount
                    
                    conn.commit()
                
                elif pool_info['type'] in ['postgresql', 'mysql']:
                    if parameters:
                        result = conn.execute(text(query), parameters)
                    else:
                        result = conn.execute(text(query))
                    
                    if fetch_results:
                        data = [dict(row) for row in result.fetchall()]
                        rows_affected = len(data)
                    else:
                        data = None
                        rows_affected = result.rowcount
                    
                    conn.commit()
                
                else:
                    raise ValueError(f"SQL queries not supported for {pool_info['type']}")
                
                execution_time = time.time() - start_time
                
                # Create result
                result = QueryResult(
                    success=True,
                    data=data,
                    rows_affected=rows_affected,
                    execution_time=execution_time,
                    query=query,
                    timestamp=datetime.utcnow().isoformat()
                )
                
                # Cache result if it's a SELECT query
                if fetch_results and query.strip().upper().startswith('SELECT'):
                    self.query_cache[query_hash] = {
                        'result': result,
                        'timestamp': time.time()
                    }
                
                # Record query history
                self._record_query_history(database_name, query, parameters, result)
                
                logger.debug(f"Query executed successfully in {execution_time:.3f}s")
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            
            result = QueryResult(
                success=False,
                execution_time=execution_time,
                error_message=str(e),
                query=query,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Record failed query
            self._record_query_history(database_name, query, parameters, result)
            
            logger.error(f"Query execution failed: {str(e)}")
            return result
    
    def execute_batch_queries(self, database_name: str, 
                            queries: List[Dict[str, Any]]) -> List[QueryResult]:
        """
        Execute multiple queries in batch
        تنفيذ عدة استعلامات في دفعة واحدة
        """
        results = []
        
        try:
            with self.get_connection(database_name) as conn:
                pool_info = self.connection_pools[database_name]
                
                if pool_info['type'] == 'sqlite':
                    cursor = conn.cursor()
                    
                    for query_info in queries:
                        query = query_info.get('query')
                        parameters = query_info.get('parameters')
                        fetch_results = query_info.get('fetch_results', True)
                        
                        try:
                            start_time = time.time()
                            
                            if parameters:
                                cursor.execute(query, parameters)
                            else:
                                cursor.execute(query)
                            
                            if fetch_results:
                                data = [dict(row) for row in cursor.fetchall()]
                                rows_affected = len(data)
                            else:
                                data = None
                                rows_affected = cursor.rowcount
                            
                            execution_time = time.time() - start_time
                            
                            result = QueryResult(
                                success=True,
                                data=data,
                                rows_affected=rows_affected,
                                execution_time=execution_time,
                                query=query,
                                timestamp=datetime.utcnow().isoformat()
                            )
                            
                            results.append(result)
                            
                        except Exception as e:
                            execution_time = time.time() - start_time
                            
                            result = QueryResult(
                                success=False,
                                execution_time=execution_time,
                                error_message=str(e),
                                query=query,
                                timestamp=datetime.utcnow().isoformat()
                            )
                            
                            results.append(result)
                    
                    conn.commit()
                
                elif pool_info['type'] in ['postgresql', 'mysql']:
                    for query_info in queries:
                        query = query_info.get('query')
                        parameters = query_info.get('parameters')
                        fetch_results = query_info.get('fetch_results', True)
                        
                        try:
                            start_time = time.time()
                            
                            if parameters:
                                result_set = conn.execute(text(query), parameters)
                            else:
                                result_set = conn.execute(text(query))
                            
                            if fetch_results:
                                data = [dict(row) for row in result_set.fetchall()]
                                rows_affected = len(data)
                            else:
                                data = None
                                rows_affected = result_set.rowcount
                            
                            execution_time = time.time() - start_time
                            
                            result = QueryResult(
                                success=True,
                                data=data,
                                rows_affected=rows_affected,
                                execution_time=execution_time,
                                query=query,
                                timestamp=datetime.utcnow().isoformat()
                            )
                            
                            results.append(result)
                            
                        except Exception as e:
                            execution_time = time.time() - start_time
                            
                            result = QueryResult(
                                success=False,
                                execution_time=execution_time,
                                error_message=str(e),
                                query=query,
                                timestamp=datetime.utcnow().isoformat()
                            )
                            
                            results.append(result)
                    
                    conn.commit()
                
                logger.info(f"Batch execution completed: {len(results)} queries")
                return results
                
        except Exception as e:
            logger.error(f"Batch query execution failed: {str(e)}")
            raise
    
    def get_table_info(self, database_name: str, table_name: str = None) -> Dict[str, Any]:
        """
        Get database table information and schema
        الحصول على معلومات جدول قاعدة البيانات والمخطط
        """
        try:
            with self.get_connection(database_name) as conn:
                pool_info = self.connection_pools[database_name]
                
                if pool_info['type'] in ['postgresql', 'mysql']:
                    inspector = inspect(pool_info['engine'])
                    
                    if table_name:
                        # Get specific table info
                        columns = inspector.get_columns(table_name)
                        indexes = inspector.get_indexes(table_name)
                        foreign_keys = inspector.get_foreign_keys(table_name)
                        primary_key = inspector.get_pk_constraint(table_name)
                        
                        return {
                            'table_name': table_name,
                            'columns': columns,
                            'indexes': indexes,
                            'foreign_keys': foreign_keys,
                            'primary_key': primary_key,
                            'column_count': len(columns)
                        }
                    else:
                        # Get all tables info
                        table_names = inspector.get_table_names()
                        tables_info = {}
                        
                        for tbl_name in table_names:
                            columns = inspector.get_columns(tbl_name)
                            tables_info[tbl_name] = {
                                'column_count': len(columns),
                                'columns': [col['name'] for col in columns]
                            }
                        
                        return {
                            'database_name': database_name,
                            'table_count': len(table_names),
                            'tables': tables_info
                        }
                
                elif pool_info['type'] == 'sqlite':
                    cursor = conn.cursor()
                    
                    if table_name:
                        # Get table schema
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = cursor.fetchall()
                        
                        cursor.execute(f"PRAGMA index_list({table_name})")
                        indexes = cursor.fetchall()
                        
                        return {
                            'table_name': table_name,
                            'columns': [dict(col) for col in columns],
                            'indexes': [dict(idx) for idx in indexes],
                            'column_count': len(columns)
                        }
                    else:
                        # Get all tables
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        
                        tables_info = {}
                        for table in tables:
                            tbl_name = table[0]
                            cursor.execute(f"PRAGMA table_info({tbl_name})")
                            columns = cursor.fetchall()
                            
                            tables_info[tbl_name] = {
                                'column_count': len(columns),
                                'columns': [col[1] for col in columns]  # Column names
                            }
                        
                        return {
                            'database_name': database_name,
                            'table_count': len(tables),
                            'tables': tables_info
                        }
                
                else:
                    return {'error': f'Table info not supported for {pool_info["type"]}'}
                    
        except Exception as e:
            logger.error(f"Failed to get table info: {str(e)}")
            return {'error': str(e)}
    
    def optimize_database(self, database_name: str) -> Dict[str, Any]:
        """
        Perform database optimization operations
        تنفيذ عمليات تحسين قاعدة البيانات
        """
        try:
            optimization_results = {}
            pool_info = self.connection_pools[database_name]
            
            if pool_info['type'] == 'sqlite':
                with self.get_connection(database_name) as conn:
                    cursor = conn.cursor()
                    
                    # Analyze database
                    cursor.execute("ANALYZE")
                    
                    # Vacuum database
                    cursor.execute("VACUUM")
                    
                    # Reindex
                    cursor.execute("REINDEX")
                    
                    # Get database size
                    cursor.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    
                    db_size_mb = (page_count * page_size) / (1024 * 1024)
                    
                    optimization_results = {
                        'database_type': 'sqlite',
                        'operations_performed': ['ANALYZE', 'VACUUM', 'REINDEX'],
                        'database_size_mb': round(db_size_mb, 2),
                        'page_count': page_count,
                        'page_size': page_size
                    }
            
            elif pool_info['type'] == 'postgresql':
                with self.get_connection(database_name) as conn:
                    # Analyze tables
                    conn.execute(text("ANALYZE"))
                    
                    # Get database size
                    result = conn.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
                    db_size = result.fetchone()[0]
                    
                    optimization_results = {
                        'database_type': 'postgresql',
                        'operations_performed': ['ANALYZE'],
                        'database_size': db_size
                    }
            
            elif pool_info['type'] == 'mysql':
                with self.get_connection(database_name) as conn:
                    # Optimize tables
                    tables_result = conn.execute(text("SHOW TABLES"))
                    tables = [row[0] for row in tables_result.fetchall()]
                    
                    optimized_tables = []
                    for table in tables:
                        conn.execute(text(f"OPTIMIZE TABLE {table}"))
                        optimized_tables.append(table)
                    
                    optimization_results = {
                        'database_type': 'mysql',
                        'operations_performed': ['OPTIMIZE TABLE'],
                        'optimized_tables': optimized_tables,
                        'tables_count': len(optimized_tables)
                    }
            
            optimization_results['timestamp'] = datetime.utcnow().isoformat()
            optimization_results['status'] = 'success'
            
            logger.info(f"Database optimization completed for {database_name}")
            return optimization_results
            
        except Exception as e:
            logger.error(f"Database optimization failed for {database_name}: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _record_query_history(self, database_name: str, query: str, 
                            parameters: Dict[str, Any], result: QueryResult):
        """
        Record query execution in history
        تسجيل تنفيذ الاستعلام في السجل
        """
        history_entry = {
            'database_name': database_name,
            'query': query[:500],  # Truncate long queries
            'parameters': parameters,
            'success': result.success,
            'execution_time': result.execution_time,
            'rows_affected': result.rows_affected,
            'error_message': result.error_message,
            'timestamp': result.timestamp
        }
        
        self.query_history.append(history_entry)
        
        # Keep only last 1000 entries
        if len(self.query_history) > 1000:
            self.query_history = self.query_history[-1000:]
        
        # Record performance metrics
        if database_name not in self.performance_metrics:
            self.performance_metrics[database_name] = []
        
        self.performance_metrics[database_name].append({
            'execution_time': result.execution_time,
            'success': result.success,
            'timestamp': result.timestamp
        })
        
        # Keep only last 500 metrics per database
        if len(self.performance_metrics[database_name]) > 500:
            self.performance_metrics[database_name] = self.performance_metrics[database_name][-500:]
    
    def _save_config(self, config: DatabaseConfig):
        """
        Save database configuration to file
        حفظ تكوين قاعدة البيانات في ملف
        """
        config_file = self.configs_path / f"{config.name}.json"
        
        # Don't save sensitive information in plain text
        safe_config = asdict(config)
        if safe_config.get('password'):
            safe_config['password'] = '***ENCRYPTED***'
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(safe_config, f, indent=2, ensure_ascii=False)
    
    def get_performance_report(self, database_name: str = None, 
                             hours_back: int = 24) -> Dict[str, Any]:
        """
        Generate database performance report
        إنشاء تقرير أداء قاعدة البيانات
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            if database_name:
                databases_to_analyze = [database_name] if database_name in self.performance_metrics else []
            else:
                databases_to_analyze = list(self.performance_metrics.keys())
            
            report = {
                'report_period_hours': hours_back,
                'generated_at': datetime.utcnow().isoformat(),
                'databases_analyzed': len(databases_to_analyze),
                'database_reports': {}
            }
            
            for db_name in databases_to_analyze:
                metrics = self.performance_metrics[db_name]
                
                # Filter by time range
                recent_metrics = [
                    m for m in metrics 
                    if datetime.fromisoformat(m['timestamp']) >= cutoff_time
                ]
                
                if not recent_metrics:
                    continue
                
                # Calculate statistics
                execution_times = [m['execution_time'] for m in recent_metrics]
                successful_queries = [m for m in recent_metrics if m['success']]
                failed_queries = [m for m in recent_metrics if not m['success']]
                
                db_report = {
                    'total_queries': len(recent_metrics),
                    'successful_queries': len(successful_queries),
                    'failed_queries': len(failed_queries),
                    'success_rate': (len(successful_queries) / len(recent_metrics)) * 100,
                    'avg_execution_time': sum(execution_times) / len(execution_times),
                    'min_execution_time': min(execution_times),
                    'max_execution_time': max(execution_times),
                    'total_execution_time': sum(execution_times)
                }
                
                report['database_reports'][db_name] = db_report
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def clear_query_cache(self):
        """
        Clear query result cache
        مسح ذاكرة التخزين المؤقت للاستعلامات
        """
        cache_size = len(self.query_cache)
        self.query_cache.clear()
        logger.info(f"Query cache cleared: {cache_size} entries removed")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get status of all database connections
        الحصول على حالة جميع اتصالات قاعدة البيانات
        """
        status_report = {
            'total_databases': len(self.database_configs),
            'active_pools': len(self.connection_pools),
            'cache_entries': len(self.query_cache),
            'query_history_size': len(self.query_history),
            'databases': {}
        }
        
        for db_name, config in self.database_configs.items():
            try:
                # Test connection
                with self.get_connection(db_name) as conn:
                    connection_test = True
            except Exception as e:
                connection_test = False
                connection_error = str(e)
            
            db_status = {
                'type': config.db_type,
                'host': config.host,
                'port': config.port,
                'connection_available': connection_test,
                'pool_initialized': db_name in self.connection_pools
            }
            
            if not connection_test:
                db_status['connection_error'] = connection_error
            
            status_report['databases'][db_name] = db_status
        
        return status_report
