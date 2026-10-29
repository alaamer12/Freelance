# Service ID: DBX53 - Part 2
# Database Backup and Recovery System
# نظام النسخ الاحتياطي واستعادة قواعد البيانات

import os
import shutil
import subprocess
import gzip
import tarfile
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import threading
import schedule

logger = logging.getLogger(__name__)

@dataclass
class BackupConfig:
    """
    Database backup configuration
    تكوين النسخ الاحتياطي لقاعدة البيانات
    """
    database_name: str
    backup_type: str  # full, incremental, differential
    schedule_pattern: str  # cron-like pattern
    retention_days: int = 30
    compression: bool = True
    encryption: bool = False
    remote_storage: Dict[str, str] = None

class DatabaseBackupRecoverySystem:
    """
    Advanced database backup and recovery system
    نظام النسخ الاحتياطي والاستعادة المتقدم لقواعد البيانات
    """
    
    def __init__(self, workspace_path: Path, db_manager):
        self.workspace_path = workspace_path
        self.db_manager = db_manager
        self.backups_path = workspace_path / "database_backups"
        self.recovery_logs_path = workspace_path / "recovery_logs"
        
        for path in [self.backups_path, self.recovery_logs_path]:
            path.mkdir(exist_ok=True)
        
        self.backup_configs: Dict[str, BackupConfig] = {}
        self.backup_history: List[Dict[str, Any]] = []
        self.scheduler_active = False
        self.scheduler_thread = None
    
    def create_backup(self, database_name: str, backup_type: str = "full", 
                     custom_name: str = None) -> Dict[str, Any]:
        """
        Create database backup
        إنشاء نسخة احتياطية لقاعدة البيانات
        """
        backup_start = time.time()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if custom_name:
            backup_name = f"{database_name}_{custom_name}_{timestamp}"
        else:
            backup_name = f"{database_name}_{backup_type}_{timestamp}"
        
        backup_path = self.backups_path / backup_name
        backup_path.mkdir(exist_ok=True)
        
        try:
            if database_name not in self.db_manager.database_configs:
                raise ValueError(f"Database not configured: {database_name}")
            
            config = self.db_manager.database_configs[database_name]
            
            if config.db_type == 'sqlite':
                result = self._backup_sqlite(config, backup_path)
            elif config.db_type == 'postgresql':
                result = self._backup_postgresql(config, backup_path)
            elif config.db_type == 'mysql':
                result = self._backup_mysql(config, backup_path)
            elif config.db_type == 'mongodb':
                result = self._backup_mongodb(config, backup_path)
            else:
                raise ValueError(f"Backup not supported for {config.db_type}")
            
            backup_time = time.time() - backup_start
            
            # Create backup metadata
            metadata = {
                'backup_name': backup_name,
                'database_name': database_name,
                'database_type': config.db_type,
                'backup_type': backup_type,
                'backup_time_seconds': round(backup_time, 2),
                'backup_size_mb': self._get_directory_size(backup_path),
                'created_at': datetime.utcnow().isoformat(),
                'backup_path': str(backup_path),
                'status': 'success'
            }
            
            metadata.update(result)
            
            # Save metadata
            metadata_file = backup_path / "backup_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Add to history
            self.backup_history.append(metadata)
            
            logger.info(f"Backup created successfully: {backup_name}")
            return metadata
            
        except Exception as e:
            backup_time = time.time() - backup_start
            
            error_metadata = {
                'backup_name': backup_name,
                'database_name': database_name,
                'backup_type': backup_type,
                'backup_time_seconds': round(backup_time, 2),
                'created_at': datetime.utcnow().isoformat(),
                'status': 'failed',
                'error': str(e)
            }
            
            self.backup_history.append(error_metadata)
            
            logger.error(f"Backup failed for {database_name}: {str(e)}")
            raise
    
    def _backup_sqlite(self, config, backup_path: Path) -> Dict[str, Any]:
        """Backup SQLite database"""
        db_file = Path(config.database)
        if not db_file.exists():
            raise FileNotFoundError(f"SQLite database not found: {db_file}")
        
        backup_file = backup_path / f"{db_file.name}"
        shutil.copy2(db_file, backup_file)
        
        return {
            'backup_method': 'file_copy',
            'original_file': str(db_file),
            'backup_file': str(backup_file),
            'file_size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2)
        }
    
    def _backup_postgresql(self, config, backup_path: Path) -> Dict[str, Any]:
        """Backup PostgreSQL database"""
        backup_file = backup_path / f"{config.database}.sql"
        
        cmd = [
            'pg_dump',
            '-h', config.host,
            '-p', str(config.port),
            '-U', config.username,
            '-d', config.database,
            '-f', str(backup_file),
            '--verbose'
        ]
        
        env = os.environ.copy()
        if config.password:
            env['PGPASSWORD'] = config.password
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        return {
            'backup_method': 'pg_dump',
            'backup_file': str(backup_file),
            'file_size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2),
            'dump_output': result.stdout
        }
    
    def _backup_mysql(self, config, backup_path: Path) -> Dict[str, Any]:
        """Backup MySQL database"""
        backup_file = backup_path / f"{config.database}.sql"
        
        cmd = [
            'mysqldump',
            f'--host={config.host}',
            f'--port={config.port}',
            f'--user={config.username}',
            f'--password={config.password}',
            '--single-transaction',
            '--routines',
            '--triggers',
            config.database
        ]
        
        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mysqldump failed: {result.stderr}")
        
        return {
            'backup_method': 'mysqldump',
            'backup_file': str(backup_file),
            'file_size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2)
        }
    
    def _backup_mongodb(self, config, backup_path: Path) -> Dict[str, Any]:
        """Backup MongoDB database"""
        cmd = [
            'mongodump',
            '--host', f"{config.host}:{config.port}",
            '--db', config.database,
            '--out', str(backup_path)
        ]
        
        if config.username and config.password:
            cmd.extend(['--username', config.username, '--password', config.password])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mongodump failed: {result.stderr}")
        
        return {
            'backup_method': 'mongodump',
            'backup_directory': str(backup_path),
            'directory_size_mb': self._get_directory_size(backup_path)
        }
    
    def restore_backup(self, backup_name: str, target_database: str = None) -> Dict[str, Any]:
        """
        Restore database from backup
        استعادة قاعدة البيانات من النسخة الاحتياطية
        """
        backup_path = self.backups_path / backup_name
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_name}")
        
        metadata_file = backup_path / "backup_metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Backup metadata not found: {backup_name}")
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        database_name = target_database or metadata['database_name']
        database_type = metadata['database_type']
        
        restore_start = time.time()
        
        try:
            if database_type == 'sqlite':
                result = self._restore_sqlite(backup_path, database_name, metadata)
            elif database_type == 'postgresql':
                result = self._restore_postgresql(backup_path, database_name, metadata)
            elif database_type == 'mysql':
                result = self._restore_mysql(backup_path, database_name, metadata)
            elif database_type == 'mongodb':
                result = self._restore_mongodb(backup_path, database_name, metadata)
            else:
                raise ValueError(f"Restore not supported for {database_type}")
            
            restore_time = time.time() - restore_start
            
            restore_result = {
                'status': 'success',
                'backup_name': backup_name,
                'target_database': database_name,
                'database_type': database_type,
                'restore_time_seconds': round(restore_time, 2),
                'restored_at': datetime.utcnow().isoformat()
            }
            
            restore_result.update(result)
            
            # Log restore operation
            log_file = self.recovery_logs_path / f"restore_{int(time.time())}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(restore_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Database restored successfully: {backup_name} -> {database_name}")
            return restore_result
            
        except Exception as e:
            restore_time = time.time() - restore_start
            
            error_result = {
                'status': 'failed',
                'backup_name': backup_name,
                'target_database': database_name,
                'database_type': database_type,
                'restore_time_seconds': round(restore_time, 2),
                'error': str(e),
                'restored_at': datetime.utcnow().isoformat()
            }
            
            # Log failed restore
            log_file = self.recovery_logs_path / f"restore_failed_{int(time.time())}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, indent=2, ensure_ascii=False)
            
            logger.error(f"Database restore failed: {str(e)}")
            raise
    
    def _restore_sqlite(self, backup_path: Path, database_name: str, metadata: Dict) -> Dict[str, Any]:
        """Restore SQLite database"""
        config = self.db_manager.database_configs[database_name]
        backup_file = backup_path / Path(metadata['backup_file']).name
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        # Create backup of current database if it exists
        current_db = Path(config.database)
        if current_db.exists():
            backup_current = current_db.with_suffix(f".backup_{int(time.time())}.db")
            shutil.copy2(current_db, backup_current)
        
        # Restore from backup
        shutil.copy2(backup_file, config.database)
        
        return {
            'restore_method': 'file_copy',
            'backup_file': str(backup_file),
            'restored_to': config.database
        }
    
    def _restore_postgresql(self, backup_path: Path, database_name: str, metadata: Dict) -> Dict[str, Any]:
        """Restore PostgreSQL database"""
        config = self.db_manager.database_configs[database_name]
        backup_file = backup_path / f"{metadata['database_name']}.sql"
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        cmd = [
            'psql',
            '-h', config.host,
            '-p', str(config.port),
            '-U', config.username,
            '-d', config.database,
            '-f', str(backup_file)
        ]
        
        env = os.environ.copy()
        if config.password:
            env['PGPASSWORD'] = config.password
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"psql restore failed: {result.stderr}")
        
        return {
            'restore_method': 'psql',
            'backup_file': str(backup_file),
            'restore_output': result.stdout
        }
    
    def _restore_mysql(self, backup_path: Path, database_name: str, metadata: Dict) -> Dict[str, Any]:
        """Restore MySQL database"""
        config = self.db_manager.database_configs[database_name]
        backup_file = backup_path / f"{metadata['database_name']}.sql"
        
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        cmd = [
            'mysql',
            f'--host={config.host}',
            f'--port={config.port}',
            f'--user={config.username}',
            f'--password={config.password}',
            config.database
        ]
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mysql restore failed: {result.stderr}")
        
        return {
            'restore_method': 'mysql',
            'backup_file': str(backup_file)
        }
    
    def _restore_mongodb(self, backup_path: Path, database_name: str, metadata: Dict) -> Dict[str, Any]:
        """Restore MongoDB database"""
        config = self.db_manager.database_configs[database_name]
        
        cmd = [
            'mongorestore',
            '--host', f"{config.host}:{config.port}",
            '--db', config.database,
            str(backup_path / metadata['database_name'])
        ]
        
        if config.username and config.password:
            cmd.extend(['--username', config.username, '--password', config.password])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"mongorestore failed: {result.stderr}")
        
        return {
            'restore_method': 'mongorestore',
            'backup_directory': str(backup_path)
        }
    
    def list_backups(self, database_name: str = None) -> List[Dict[str, Any]]:
        """
        List available backups
        قائمة النسخ الاحتياطية المتاحة
        """
        backups = []
        
        for backup_dir in self.backups_path.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backup_metadata.json"
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        if database_name is None or metadata.get('database_name') == database_name:
                            backups.append(metadata)
                    
                    except Exception as e:
                        logger.warning(f"Failed to read backup metadata: {metadata_file} - {str(e)}")
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return backups
    
    def cleanup_old_backups(self, retention_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old backups based on retention policy
        تنظيف النسخ الاحتياطية القديمة بناءً على سياسة الاحتفاظ
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        removed_backups = []
        total_space_freed = 0
        
        for backup_dir in self.backups_path.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "backup_metadata.json"
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        created_at = datetime.fromisoformat(metadata.get('created_at', ''))
                        
                        if created_at < cutoff_date:
                            backup_size = self._get_directory_size(backup_dir)
                            shutil.rmtree(backup_dir)
                            
                            removed_backups.append({
                                'backup_name': metadata.get('backup_name'),
                                'database_name': metadata.get('database_name'),
                                'created_at': metadata.get('created_at'),
                                'size_mb': backup_size
                            })
                            
                            total_space_freed += backup_size
                    
                    except Exception as e:
                        logger.warning(f"Failed to process backup for cleanup: {backup_dir} - {str(e)}")
        
        cleanup_result = {
            'retention_days': retention_days,
            'removed_backups_count': len(removed_backups),
            'total_space_freed_mb': round(total_space_freed, 2),
            'removed_backups': removed_backups,
            'cleanup_timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Backup cleanup completed: {len(removed_backups)} backups removed, {total_space_freed:.2f} MB freed")
        return cleanup_result
    
    def _get_directory_size(self, path: Path) -> float:
        """Get directory size in MB"""
        total_size = 0
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Failed to calculate directory size: {str(e)}")
        
        return round(total_size / (1024 * 1024), 2)
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """
        Get backup system statistics
        الحصول على إحصائيات نظام النسخ الاحتياطي
        """
        backups = self.list_backups()
        
        if not backups:
            return {
                'total_backups': 0,
                'total_size_mb': 0,
                'databases_backed_up': 0
            }
        
        # Group by database
        db_stats = {}
        total_size = 0
        
        for backup in backups:
            db_name = backup.get('database_name', 'unknown')
            backup_size = backup.get('backup_size_mb', 0)
            
            if db_name not in db_stats:
                db_stats[db_name] = {
                    'backup_count': 0,
                    'total_size_mb': 0,
                    'latest_backup': None,
                    'oldest_backup': None
                }
            
            db_stats[db_name]['backup_count'] += 1
            db_stats[db_name]['total_size_mb'] += backup_size
            total_size += backup_size
            
            # Track latest and oldest
            created_at = backup.get('created_at')
            if not db_stats[db_name]['latest_backup'] or created_at > db_stats[db_name]['latest_backup']:
                db_stats[db_name]['latest_backup'] = created_at
            
            if not db_stats[db_name]['oldest_backup'] or created_at < db_stats[db_name]['oldest_backup']:
                db_stats[db_name]['oldest_backup'] = created_at
        
        return {
            'total_backups': len(backups),
            'total_size_mb': round(total_size, 2),
            'databases_backed_up': len(db_stats),
            'database_statistics': db_stats,
            'generated_at': datetime.utcnow().isoformat()
        }
