# Service ID: ATS66 - Part 1
# Docker Container Management and Orchestration
# إدارة وتنسيق حاويات Docker

import docker
import time
import logging
import json
import yaml
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import psutil
import pandas as pd

logger = logging.getLogger(__name__)

# ==================== SECTION 1: Container Management ====================

@dataclass
class ContainerConfig:
    """
    Container configuration settings
    إعدادات تكوين الحاوية
    """
    name: str
    image: str
    ports: Dict[str, str] = None
    volumes: Dict[str, str] = None
    environment: Dict[str, str] = None
    command: str = None
    working_dir: str = None
    restart_policy: str = "unless-stopped"
    memory_limit: str = None
    cpu_limit: float = None
    network_mode: str = "bridge"
    labels: Dict[str, str] = None
    health_check: Dict[str, Any] = None

@dataclass
class ContainerStatus:
    """
    Container status information
    معلومات حالة الحاوية
    """
    container_id: str
    name: str
    status: str
    image: str
    created: str
    ports: List[Dict[str, Any]]
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    network_io: Dict[str, int] = None
    disk_io: Dict[str, int] = None

class AdvancedContainerManager:
    """
    Advanced Docker container management with monitoring and optimization
    إدارة حاويات Docker المتقدمة مع المراقبة والتحسين
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.configs_path = workspace_path / "docker_configs"
        self.logs_path = workspace_path / "container_logs"
        self.configs_path.mkdir(exist_ok=True)
        self.logs_path.mkdir(exist_ok=True)
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            raise
        
        self.managed_containers: Dict[str, ContainerConfig] = {}
        self.monitoring_active = False
        self.monitoring_thread = None
        self.container_stats: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_container(self, config: ContainerConfig, start_immediately: bool = True) -> str:
        """
        Create and optionally start a Docker container
        إنشاء وبدء تشغيل حاوية Docker اختياريًا
        """
        try:
            # Prepare container arguments
            container_args = {
                'image': config.image,
                'name': config.name,
                'detach': True,
                'restart_policy': {"Name": config.restart_policy}
            }
            
            # Add optional configurations
            if config.ports:
                container_args['ports'] = config.ports
            
            if config.volumes:
                container_args['volumes'] = config.volumes
            
            if config.environment:
                container_args['environment'] = config.environment
            
            if config.command:
                container_args['command'] = config.command
            
            if config.working_dir:
                container_args['working_dir'] = config.working_dir
            
            if config.memory_limit:
                container_args['mem_limit'] = config.memory_limit
            
            if config.cpu_limit:
                container_args['cpu_quota'] = int(config.cpu_limit * 100000)
                container_args['cpu_period'] = 100000
            
            if config.network_mode:
                container_args['network_mode'] = config.network_mode
            
            if config.labels:
                container_args['labels'] = config.labels
            
            if config.health_check:
                container_args['healthcheck'] = config.health_check
            
            # Create container
            container = self.docker_client.containers.create(**container_args)
            
            # Start if requested
            if start_immediately:
                container.start()
                logger.info(f"Container created and started: {config.name} ({container.short_id})")
            else:
                logger.info(f"Container created: {config.name} ({container.short_id})")
            
            # Store configuration
            self.managed_containers[config.name] = config
            
            # Save configuration to file
            self._save_container_config(config)
            
            return container.id
            
        except Exception as e:
            logger.error(f"Failed to create container {config.name}: {str(e)}")
            raise
    
    def start_container(self, container_name: str) -> bool:
        """
        Start a container by name
        بدء تشغيل حاوية بالاسم
        """
        try:
            container = self.docker_client.containers.get(container_name)
            container.start()
            logger.info(f"Container started: {container_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start container {container_name}: {str(e)}")
            return False
    
    def stop_container(self, container_name: str, timeout: int = 30) -> bool:
        """
        Stop a container gracefully
        إيقاف حاوية بلطف
        """
        try:
            container = self.docker_client.containers.get(container_name)
            container.stop(timeout=timeout)
            logger.info(f"Container stopped: {container_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {str(e)}")
            return False
    
    def restart_container(self, container_name: str, timeout: int = 30) -> bool:
        """
        Restart a container
        إعادة تشغيل حاوية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            container.restart(timeout=timeout)
            logger.info(f"Container restarted: {container_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to restart container {container_name}: {str(e)}")
            return False
    
    def remove_container(self, container_name: str, force: bool = False, 
                        remove_volumes: bool = False) -> bool:
        """
        Remove a container
        إزالة حاوية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            container.remove(force=force, v=remove_volumes)
            
            # Remove from managed containers
            if container_name in self.managed_containers:
                del self.managed_containers[container_name]
            
            # Remove configuration file
            config_file = self.configs_path / f"{container_name}.json"
            if config_file.exists():
                config_file.unlink()
            
            logger.info(f"Container removed: {container_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove container {container_name}: {str(e)}")
            return False
    
    def get_container_status(self, container_name: str) -> Optional[ContainerStatus]:
        """
        Get detailed container status
        الحصول على حالة الحاوية التفصيلية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            container.reload()
            
            # Get basic info
            status = ContainerStatus(
                container_id=container.id,
                name=container.name,
                status=container.status,
                image=container.image.tags[0] if container.image.tags else container.image.id,
                created=container.attrs['Created'],
                ports=container.attrs.get('NetworkSettings', {}).get('Ports', {})
            )
            
            # Get resource usage stats
            try:
                stats = container.stats(stream=False)
                
                # Calculate CPU usage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                if system_delta > 0:
                    cpu_count = len(stats['cpu_stats']['cpu_usage']['percpu_usage'])
                    status.cpu_usage = (cpu_delta / system_delta) * cpu_count * 100.0
                
                # Calculate memory usage
                memory_usage = stats['memory_stats']['usage']
                memory_limit = stats['memory_stats']['limit']
                status.memory_usage = (memory_usage / memory_limit) * 100.0
                
                # Network I/O
                networks = stats.get('networks', {})
                if networks:
                    total_rx = sum(net['rx_bytes'] for net in networks.values())
                    total_tx = sum(net['tx_bytes'] for net in networks.values())
                    status.network_io = {'rx_bytes': total_rx, 'tx_bytes': total_tx}
                
                # Disk I/O
                blkio_stats = stats.get('blkio_stats', {})
                if blkio_stats.get('io_service_bytes_recursive'):
                    read_bytes = sum(item['value'] for item in blkio_stats['io_service_bytes_recursive'] 
                                   if item['op'] == 'Read')
                    write_bytes = sum(item['value'] for item in blkio_stats['io_service_bytes_recursive'] 
                                    if item['op'] == 'Write')
                    status.disk_io = {'read_bytes': read_bytes, 'write_bytes': write_bytes}
                
            except Exception as e:
                logger.warning(f"Failed to get stats for container {container_name}: {str(e)}")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get status for container {container_name}: {str(e)}")
            return None
    
    def list_containers(self, all_containers: bool = False) -> List[ContainerStatus]:
        """
        List all containers with their status
        قائمة جميع الحاويات مع حالتها
        """
        containers_status = []
        
        try:
            containers = self.docker_client.containers.list(all=all_containers)
            
            for container in containers:
                status = self.get_container_status(container.name)
                if status:
                    containers_status.append(status)
            
        except Exception as e:
            logger.error(f"Failed to list containers: {str(e)}")
        
        return containers_status
    
    def execute_command(self, container_name: str, command: str, 
                       working_dir: str = None) -> Dict[str, Any]:
        """
        Execute command inside container
        تنفيذ أمر داخل الحاوية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            
            exec_args = {
                'cmd': command,
                'stdout': True,
                'stderr': True,
                'stream': False
            }
            
            if working_dir:
                exec_args['workdir'] = working_dir
            
            result = container.exec_run(**exec_args)
            
            return {
                'exit_code': result.exit_code,
                'output': result.output.decode('utf-8'),
                'command': command,
                'container': container_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to execute command in container {container_name}: {str(e)}")
            return {
                'exit_code': -1,
                'output': f"Error: {str(e)}",
                'command': command,
                'container': container_name,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_container_logs(self, container_name: str, tail: int = 100, 
                          since: str = None) -> str:
        """
        Get container logs
        الحصول على سجلات الحاوية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            
            log_args = {
                'stdout': True,
                'stderr': True,
                'tail': tail,
                'timestamps': True
            }
            
            if since:
                log_args['since'] = since
            
            logs = container.logs(**log_args)
            return logs.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to get logs for container {container_name}: {str(e)}")
            return f"Error retrieving logs: {str(e)}"
    
    def copy_file_to_container(self, container_name: str, src_path: str, 
                              dest_path: str) -> bool:
        """
        Copy file to container
        نسخ ملف إلى الحاوية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Create tar archive of the file
            import tarfile
            import io
            
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tar.add(src_path, arcname=Path(dest_path).name)
            
            tar_stream.seek(0)
            
            # Copy to container
            container.put_archive(Path(dest_path).parent, tar_stream)
            
            logger.info(f"File copied to container {container_name}: {src_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file to container {container_name}: {str(e)}")
            return False
    
    def copy_file_from_container(self, container_name: str, src_path: str, 
                                dest_path: str) -> bool:
        """
        Copy file from container
        نسخ ملف من الحاوية
        """
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Get file from container
            tar_stream, _ = container.get_archive(src_path)
            
            # Extract file
            import tarfile
            import io
            
            tar_data = b''.join(tar_stream)
            tar_stream = io.BytesIO(tar_data)
            
            with tarfile.open(fileobj=tar_stream, mode='r') as tar:
                tar.extractall(Path(dest_path).parent)
            
            logger.info(f"File copied from container {container_name}: {src_path} -> {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy file from container {container_name}: {str(e)}")
            return False
    
    def start_monitoring(self, interval_seconds: int = 30):
        """
        Start container monitoring
        بدء مراقبة الحاويات
        """
        if self.monitoring_active:
            logger.warning("Container monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Container monitoring started with {interval_seconds}s interval")
    
    def stop_monitoring(self):
        """
        Stop container monitoring
        إيقاف مراقبة الحاويات
        """
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Container monitoring stopped")
    
    def _monitoring_loop(self, interval_seconds: int):
        """
        Container monitoring loop
        حلقة مراقبة الحاويات
        """
        while self.monitoring_active:
            try:
                containers = self.list_containers(all_containers=False)
                
                for container_status in containers:
                    container_name = container_status.name
                    
                    # Store stats
                    if container_name not in self.container_stats:
                        self.container_stats[container_name] = []
                    
                    stats_entry = {
                        'timestamp': datetime.utcnow().isoformat(),
                        'cpu_usage': container_status.cpu_usage,
                        'memory_usage': container_status.memory_usage,
                        'network_io': container_status.network_io,
                        'disk_io': container_status.disk_io,
                        'status': container_status.status
                    }
                    
                    self.container_stats[container_name].append(stats_entry)
                    
                    # Keep only last 1000 entries per container
                    if len(self.container_stats[container_name]) > 1000:
                        self.container_stats[container_name] = self.container_stats[container_name][-1000:]
                    
                    # Check for alerts
                    self._check_container_alerts(container_status)
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(interval_seconds)
    
    def _check_container_alerts(self, status: ContainerStatus):
        """
        Check container for alert conditions
        فحص الحاوية لشروط التنبيه
        """
        alerts = []
        
        # High CPU usage
        if status.cpu_usage > 80:
            alerts.append(f"High CPU usage: {status.cpu_usage:.1f}%")
        
        # High memory usage
        if status.memory_usage > 85:
            alerts.append(f"High memory usage: {status.memory_usage:.1f}%")
        
        # Container not running
        if status.status != 'running':
            alerts.append(f"Container not running: {status.status}")
        
        # Log alerts
        for alert in alerts:
            logger.warning(f"ALERT - Container {status.name}: {alert}")
    
    def _save_container_config(self, config: ContainerConfig):
        """
        Save container configuration to file
        حفظ تكوين الحاوية في ملف
        """
        config_file = self.configs_path / f"{config.name}.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(config), f, indent=2, ensure_ascii=False)
    
    def load_container_config(self, container_name: str) -> Optional[ContainerConfig]:
        """
        Load container configuration from file
        تحميل تكوين الحاوية من ملف
        """
        config_file = self.configs_path / f"{container_name}.json"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return ContainerConfig(**config_data)
            
        except Exception as e:
            logger.error(f"Failed to load config for {container_name}: {str(e)}")
            return None
    
    def get_monitoring_stats(self, container_name: str, 
                           hours_back: int = 24) -> Dict[str, Any]:
        """
        Get monitoring statistics for container
        الحصول على إحصائيات المراقبة للحاوية
        """
        if container_name not in self.container_stats:
            return {"error": f"No stats available for container: {container_name}"}
        
        stats = self.container_stats[container_name]
        
        # Filter by time range
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        filtered_stats = [
            s for s in stats 
            if datetime.fromisoformat(s['timestamp']) >= cutoff_time
        ]
        
        if not filtered_stats:
            return {"error": "No stats in specified time range"}
        
        # Calculate statistics
        cpu_values = [s['cpu_usage'] for s in filtered_stats if s['cpu_usage'] is not None]
        memory_values = [s['memory_usage'] for s in filtered_stats if s['memory_usage'] is not None]
        
        return {
            "container_name": container_name,
            "time_range_hours": hours_back,
            "total_data_points": len(filtered_stats),
            "cpu_stats": {
                "average": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "maximum": max(cpu_values) if cpu_values else 0,
                "minimum": min(cpu_values) if cpu_values else 0
            },
            "memory_stats": {
                "average": sum(memory_values) / len(memory_values) if memory_values else 0,
                "maximum": max(memory_values) if memory_values else 0,
                "minimum": min(memory_values) if memory_values else 0
            },
            "status_changes": len(set(s['status'] for s in filtered_stats)),
            "first_timestamp": filtered_stats[0]['timestamp'],
            "last_timestamp": filtered_stats[-1]['timestamp']
        }
