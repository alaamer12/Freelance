# Service ID: ATS66 - Part 3
# Docker Orchestration and Compose Management
# تنسيق Docker وإدارة Compose

import docker
import yaml
import os
import time
import logging
import json
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

# ==================== SECTION 3: Orchestration and Compose Management ====================

@dataclass
class ServiceConfig:
    """
    Docker Compose service configuration
    تكوين خدمة Docker Compose
    """
    name: str
    image: str
    ports: List[str] = None
    volumes: List[str] = None
    environment: Dict[str, str] = None
    depends_on: List[str] = None
    restart: str = "unless-stopped"
    networks: List[str] = None
    command: str = None
    healthcheck: Dict[str, Any] = None
    deploy: Dict[str, Any] = None
    labels: Dict[str, str] = None

@dataclass
class ComposeProject:
    """
    Docker Compose project configuration
    تكوين مشروع Docker Compose
    """
    name: str
    version: str = "3.8"
    services: Dict[str, ServiceConfig] = None
    networks: Dict[str, Dict[str, Any]] = None
    volumes: Dict[str, Dict[str, Any]] = None
    secrets: Dict[str, Dict[str, Any]] = None
    configs: Dict[str, Dict[str, Any]] = None

class DockerOrchestrationManager:
    """
    Advanced Docker orchestration and compose management
    إدارة تنسيق Docker المتقدم و compose
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.compose_projects_path = workspace_path / "compose_projects"
        self.orchestration_logs_path = workspace_path / "orchestration_logs"
        self.compose_projects_path.mkdir(exist_ok=True)
        self.orchestration_logs_path.mkdir(exist_ok=True)
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized for orchestration")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            raise
        
        self.active_projects: Dict[str, ComposeProject] = {}
        self.deployment_history: List[Dict[str, Any]] = []
        self.monitoring_active = False
        self.monitoring_thread = None
    
    def create_compose_project(self, project: ComposeProject) -> str:
        """
        Create Docker Compose project configuration
        إنشاء تكوين مشروع Docker Compose
        """
        try:
            project_path = self.compose_projects_path / project.name
            project_path.mkdir(exist_ok=True)
            
            # Generate docker-compose.yml
            compose_config = self._generate_compose_config(project)
            
            compose_file_path = project_path / "docker-compose.yml"
            with open(compose_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(compose_config, f, default_flow_style=False, allow_unicode=True)
            
            # Generate .env file if environment variables exist
            env_vars = self._extract_env_variables(project)
            if env_vars:
                env_file_path = project_path / ".env"
                with open(env_file_path, 'w', encoding='utf-8') as f:
                    for key, value in env_vars.items():
                        f.write(f"{key}={value}\n")
            
            # Store project configuration
            self.active_projects[project.name] = project
            
            # Save project metadata
            metadata = {
                'name': project.name,
                'created_at': datetime.utcnow().isoformat(),
                'services_count': len(project.services) if project.services else 0,
                'compose_file': str(compose_file_path),
                'project_path': str(project_path)
            }
            
            metadata_file = project_path / "project_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Compose project created: {project.name}")
            return str(project_path)
            
        except Exception as e:
            logger.error(f"Failed to create compose project {project.name}: {str(e)}")
            raise
    
    def _generate_compose_config(self, project: ComposeProject) -> Dict[str, Any]:
        """
        Generate Docker Compose configuration dictionary
        إنشاء قاموس تكوين Docker Compose
        """
        config = {
            'version': project.version,
            'services': {}
        }
        
        # Add services
        if project.services:
            for service_name, service_config in project.services.items():
                service_dict = {
                    'image': service_config.image,
                    'restart': service_config.restart
                }
                
                if service_config.ports:
                    service_dict['ports'] = service_config.ports
                
                if service_config.volumes:
                    service_dict['volumes'] = service_config.volumes
                
                if service_config.environment:
                    service_dict['environment'] = service_config.environment
                
                if service_config.depends_on:
                    service_dict['depends_on'] = service_config.depends_on
                
                if service_config.networks:
                    service_dict['networks'] = service_config.networks
                
                if service_config.command:
                    service_dict['command'] = service_config.command
                
                if service_config.healthcheck:
                    service_dict['healthcheck'] = service_config.healthcheck
                
                if service_config.deploy:
                    service_dict['deploy'] = service_config.deploy
                
                if service_config.labels:
                    service_dict['labels'] = service_config.labels
                
                config['services'][service_name] = service_dict
        
        # Add networks
        if project.networks:
            config['networks'] = project.networks
        
        # Add volumes
        if project.volumes:
            config['volumes'] = project.volumes
        
        # Add secrets
        if project.secrets:
            config['secrets'] = project.secrets
        
        # Add configs
        if project.configs:
            config['configs'] = project.configs
        
        return config
    
    def _extract_env_variables(self, project: ComposeProject) -> Dict[str, str]:
        """
        Extract environment variables from project services
        استخراج متغيرات البيئة من خدمات المشروع
        """
        env_vars = {}
        
        if project.services:
            for service_config in project.services.values():
                if service_config.environment:
                    env_vars.update(service_config.environment)
        
        return env_vars
    
    def deploy_project(self, project_name: str, build_images: bool = False, 
                      detached: bool = True) -> Dict[str, Any]:
        """
        Deploy Docker Compose project
        نشر مشروع Docker Compose
        """
        if project_name not in self.active_projects:
            raise ValueError(f"Project not found: {project_name}")
        
        project_path = self.compose_projects_path / project_name
        compose_file = project_path / "docker-compose.yml"
        
        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {compose_file}")
        
        deployment_start = time.time()
        deployment_id = f"deploy_{project_name}_{int(time.time())}"
        
        try:
            # Prepare docker-compose command
            cmd = ['docker-compose', '-f', str(compose_file), '-p', project_name]
            
            if build_images:
                # Build images first
                build_cmd = cmd + ['build']
                build_result = subprocess.run(
                    build_cmd, 
                    cwd=project_path,
                    capture_output=True, 
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if build_result.returncode != 0:
                    raise Exception(f"Build failed: {build_result.stderr}")
            
            # Deploy services
            deploy_cmd = cmd + ['up']
            if detached:
                deploy_cmd.append('-d')
            
            deploy_result = subprocess.run(
                deploy_cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if deploy_result.returncode != 0:
                raise Exception(f"Deployment failed: {deploy_result.stderr}")
            
            deployment_time = time.time() - deployment_start
            
            # Get deployed services status
            services_status = self.get_project_status(project_name)
            
            deployment_result = {
                'deployment_id': deployment_id,
                'project_name': project_name,
                'status': 'success',
                'deployment_time': round(deployment_time, 2),
                'services_deployed': len(services_status.get('services', [])),
                'services_status': services_status,
                'build_images': build_images,
                'detached': detached,
                'deploy_output': deploy_result.stdout,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store deployment history
            self.deployment_history.append(deployment_result)
            
            logger.info(f"Project deployed successfully: {project_name} in {deployment_time:.2f}s")
            return deployment_result
            
        except Exception as e:
            deployment_time = time.time() - deployment_start
            
            deployment_result = {
                'deployment_id': deployment_id,
                'project_name': project_name,
                'status': 'failed',
                'deployment_time': round(deployment_time, 2),
                'error': str(e),
                'build_images': build_images,
                'detached': detached,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.deployment_history.append(deployment_result)
            
            logger.error(f"Project deployment failed: {project_name} - {str(e)}")
            raise
    
    def stop_project(self, project_name: str, remove_containers: bool = False) -> Dict[str, Any]:
        """
        Stop Docker Compose project
        إيقاف مشروع Docker Compose
        """
        project_path = self.compose_projects_path / project_name
        compose_file = project_path / "docker-compose.yml"
        
        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {compose_file}")
        
        try:
            # Prepare docker-compose command
            cmd = ['docker-compose', '-f', str(compose_file), '-p', project_name]
            
            if remove_containers:
                cmd.extend(['down', '--remove-orphans'])
            else:
                cmd.append('stop')
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Stop failed: {result.stderr}")
            
            logger.info(f"Project stopped: {project_name}")
            
            return {
                'status': 'success',
                'project_name': project_name,
                'remove_containers': remove_containers,
                'output': result.stdout,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to stop project {project_name}: {str(e)}")
            return {
                'status': 'failed',
                'project_name': project_name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def scale_service(self, project_name: str, service_name: str, 
                     replicas: int) -> Dict[str, Any]:
        """
        Scale service in Docker Compose project
        توسيع الخدمة في مشروع Docker Compose
        """
        project_path = self.compose_projects_path / project_name
        compose_file = project_path / "docker-compose.yml"
        
        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found: {compose_file}")
        
        try:
            cmd = [
                'docker-compose', '-f', str(compose_file), '-p', project_name,
                'up', '-d', '--scale', f"{service_name}={replicas}"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Scaling failed: {result.stderr}")
            
            logger.info(f"Service scaled: {service_name} to {replicas} replicas")
            
            return {
                'status': 'success',
                'project_name': project_name,
                'service_name': service_name,
                'replicas': replicas,
                'output': result.stdout,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to scale service {service_name}: {str(e)}")
            return {
                'status': 'failed',
                'project_name': project_name,
                'service_name': service_name,
                'replicas': replicas,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_project_status(self, project_name: str) -> Dict[str, Any]:
        """
        Get Docker Compose project status
        الحصول على حالة مشروع Docker Compose
        """
        project_path = self.compose_projects_path / project_name
        compose_file = project_path / "docker-compose.yml"
        
        if not compose_file.exists():
            return {'error': f"Compose file not found: {compose_file}"}
        
        try:
            # Get services status
            cmd = ['docker-compose', '-f', str(compose_file), '-p', project_name, 'ps', '--format', 'json']
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {'error': f"Failed to get status: {result.stderr}"}
            
            # Parse JSON output
            services = []
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    try:
                        service_info = json.loads(line)
                        services.append(service_info)
                    except json.JSONDecodeError:
                        continue
            
            # Get project metadata
            metadata_file = project_path / "project_metadata.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            return {
                'project_name': project_name,
                'services': services,
                'services_count': len(services),
                'running_services': len([s for s in services if s.get('State') == 'running']),
                'metadata': metadata,
                'status_timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get project status {project_name}: {str(e)}")
            return {
                'error': str(e),
                'project_name': project_name,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_service_logs(self, project_name: str, service_name: str, 
                        tail: int = 100, follow: bool = False) -> str:
        """
        Get service logs from Docker Compose project
        الحصول على سجلات الخدمة من مشروع Docker Compose
        """
        project_path = self.compose_projects_path / project_name
        compose_file = project_path / "docker-compose.yml"
        
        if not compose_file.exists():
            return f"Error: Compose file not found: {compose_file}"
        
        try:
            cmd = [
                'docker-compose', '-f', str(compose_file), '-p', project_name,
                'logs', '--tail', str(tail)
            ]
            
            if follow:
                cmd.append('-f')
            
            cmd.append(service_name)
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30 if not follow else None
            )
            
            return result.stdout if result.returncode == 0 else result.stderr
            
        except Exception as e:
            logger.error(f"Failed to get service logs: {str(e)}")
            return f"Error retrieving logs: {str(e)}"
    
    def update_service(self, project_name: str, service_name: str, 
                      new_image: str = None, new_env: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Update service configuration and redeploy
        تحديث تكوين الخدمة وإعادة النشر
        """
        if project_name not in self.active_projects:
            raise ValueError(f"Project not found: {project_name}")
        
        project = self.active_projects[project_name]
        
        if not project.services or service_name not in project.services:
            raise ValueError(f"Service not found: {service_name}")
        
        try:
            # Update service configuration
            service_config = project.services[service_name]
            
            if new_image:
                service_config.image = new_image
            
            if new_env:
                if service_config.environment:
                    service_config.environment.update(new_env)
                else:
                    service_config.environment = new_env
            
            # Regenerate compose file
            project_path = self.create_compose_project(project)
            
            # Redeploy specific service
            compose_file = Path(project_path) / "docker-compose.yml"
            
            cmd = [
                'docker-compose', '-f', str(compose_file), '-p', project_name,
                'up', '-d', '--no-deps', service_name
            ]
            
            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=180
            )
            
            if result.returncode != 0:
                raise Exception(f"Service update failed: {result.stderr}")
            
            logger.info(f"Service updated: {service_name} in project {project_name}")
            
            return {
                'status': 'success',
                'project_name': project_name,
                'service_name': service_name,
                'updated_image': new_image,
                'updated_env': new_env,
                'output': result.stdout,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update service {service_name}: {str(e)}")
            return {
                'status': 'failed',
                'project_name': project_name,
                'service_name': service_name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def backup_project(self, project_name: str, include_volumes: bool = True) -> Dict[str, Any]:
        """
        Backup Docker Compose project
        نسخ احتياطي لمشروع Docker Compose
        """
        project_path = self.compose_projects_path / project_name
        
        if not project_path.exists():
            raise ValueError(f"Project path not found: {project_path}")
        
        try:
            backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{project_name}_backup_{backup_timestamp}"
            backup_path = self.workspace_path / "backups" / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy project files
            import shutil
            shutil.copytree(project_path, backup_path / "project_files")
            
            # Backup volumes if requested
            volume_backups = []
            if include_volumes:
                compose_file = project_path / "docker-compose.yml"
                
                if compose_file.exists():
                    cmd = [
                        'docker-compose', '-f', str(compose_file), '-p', project_name,
                        'config', '--volumes'
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        volumes = result.stdout.strip().split('\n')
                        
                        for volume in volumes:
                            if volume.strip():
                                volume_backup = self._backup_volume(volume.strip(), backup_path)
                                volume_backups.append(volume_backup)
            
            # Create backup metadata
            backup_metadata = {
                'project_name': project_name,
                'backup_name': backup_name,
                'backup_timestamp': backup_timestamp,
                'backup_path': str(backup_path),
                'include_volumes': include_volumes,
                'volume_backups': volume_backups,
                'created_at': datetime.utcnow().isoformat()
            }
            
            metadata_file = backup_path / "backup_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(backup_metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Project backup created: {backup_name}")
            
            return {
                'status': 'success',
                'backup_name': backup_name,
                'backup_path': str(backup_path),
                'backup_size_mb': self._get_directory_size(backup_path),
                'volume_backups_count': len(volume_backups),
                'metadata': backup_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to backup project {project_name}: {str(e)}")
            return {
                'status': 'failed',
                'project_name': project_name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _backup_volume(self, volume_name: str, backup_path: Path) -> Dict[str, Any]:
        """
        Backup Docker volume
        نسخ احتياطي لمجلد Docker
        """
        try:
            volume_backup_path = backup_path / "volumes" / volume_name
            volume_backup_path.mkdir(parents=True, exist_ok=True)
            
            # Create temporary container to access volume
            cmd = [
                'docker', 'run', '--rm',
                '-v', f"{volume_name}:/volume",
                '-v', f"{volume_backup_path}:/backup",
                'alpine',
                'tar', 'czf', '/backup/volume_data.tar.gz', '-C', '/volume', '.'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Volume backup failed: {result.stderr}")
            
            backup_file = volume_backup_path / "volume_data.tar.gz"
            backup_size = backup_file.stat().st_size if backup_file.exists() else 0
            
            return {
                'volume_name': volume_name,
                'backup_file': str(backup_file),
                'backup_size_bytes': backup_size,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to backup volume {volume_name}: {str(e)}")
            return {
                'volume_name': volume_name,
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_directory_size(self, path: Path) -> float:
        """
        Get directory size in MB
        الحصول على حجم الدليل بالميجابايت
        """
        total_size = 0
        try:
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Failed to calculate directory size: {str(e)}")
        
        return round(total_size / (1024 * 1024), 2)
    
    def get_deployment_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get deployment history
        الحصول على سجل النشر
        """
        return self.deployment_history[-limit:] if self.deployment_history else []
    
    def cleanup_unused_resources(self) -> Dict[str, Any]:
        """
        Clean up unused Docker resources
        تنظيف موارد Docker غير المستخدمة
        """
        try:
            cleanup_results = {}
            
            # Remove unused containers
            containers_result = self.docker_client.containers.prune()
            cleanup_results['containers'] = {
                'removed_count': len(containers_result.get('ContainersDeleted', [])),
                'space_reclaimed_mb': round(containers_result.get('SpaceReclaimed', 0) / (1024 * 1024), 2)
            }
            
            # Remove unused images
            images_result = self.docker_client.images.prune(filters={'dangling': False})
            cleanup_results['images'] = {
                'removed_count': len(images_result.get('ImagesDeleted', [])),
                'space_reclaimed_mb': round(images_result.get('SpaceReclaimed', 0) / (1024 * 1024), 2)
            }
            
            # Remove unused volumes
            volumes_result = self.docker_client.volumes.prune()
            cleanup_results['volumes'] = {
                'removed_count': len(volumes_result.get('VolumesDeleted', [])),
                'space_reclaimed_mb': round(volumes_result.get('SpaceReclaimed', 0) / (1024 * 1024), 2)
            }
            
            # Remove unused networks
            networks_result = self.docker_client.networks.prune()
            cleanup_results['networks'] = {
                'removed_count': len(networks_result.get('NetworksDeleted', []))
            }
            
            total_space_reclaimed = (
                cleanup_results['containers']['space_reclaimed_mb'] +
                cleanup_results['images']['space_reclaimed_mb'] +
                cleanup_results['volumes']['space_reclaimed_mb']
            )
            
            logger.info(f"Docker cleanup completed - {total_space_reclaimed:.2f} MB reclaimed")
            
            return {
                'status': 'success',
                'total_space_reclaimed_mb': total_space_reclaimed,
                'cleanup_details': cleanup_results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Docker cleanup failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
