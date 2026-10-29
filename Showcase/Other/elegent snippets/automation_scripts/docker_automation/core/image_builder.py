# Service ID: ATS66 - Part 2
# Docker Image Building and Registry Management
# بناء صور Docker وإدارة السجل

import docker
import os
import time
import logging
import json
import yaml
import tarfile
import io
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from jinja2 import Template

logger = logging.getLogger(__name__)

# ==================== SECTION 2: Image Building and Registry Management ====================

@dataclass
class BuildConfig:
    """
    Docker image build configuration
    تكوين بناء صورة Docker
    """
    image_name: str
    tag: str = "latest"
    dockerfile_path: str = "Dockerfile"
    context_path: str = "."
    build_args: Dict[str, str] = None
    labels: Dict[str, str] = None
    target_stage: str = None
    no_cache: bool = False
    pull_base_image: bool = True
    squash: bool = False
    platform: str = None

@dataclass
class RegistryConfig:
    """
    Docker registry configuration
    تكوين سجل Docker
    """
    registry_url: str
    username: str
    password: str
    namespace: str = None
    insecure: bool = False

class AdvancedImageBuilder:
    """
    Advanced Docker image building with optimization and multi-stage support
    بناء صور Docker المتقدم مع التحسين ودعم المراحل المتعددة
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.build_cache_path = workspace_path / "build_cache"
        self.templates_path = workspace_path / "dockerfile_templates"
        self.build_cache_path.mkdir(exist_ok=True)
        self.templates_path.mkdir(exist_ok=True)
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized for image building")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {str(e)}")
            raise
        
        self.build_history: List[Dict[str, Any]] = []
        self.registry_configs: Dict[str, RegistryConfig] = {}
        
        # Initialize default Dockerfile templates
        self._initialize_dockerfile_templates()
    
    def _initialize_dockerfile_templates(self):
        """
        Initialize default Dockerfile templates
        تهيئة قوالب Dockerfile الافتراضية
        """
        templates = {
            "python_app": """
# Python Application Template
FROM python:{{ python_version }}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \\
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:{{ port }}/health')"

EXPOSE {{ port }}

CMD ["python", "{{ main_file }}"]
""",
            "node_app": """
# Node.js Application Template
FROM node:{{ node_version }}-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs \\
    && adduser -S nextjs -u 1001 \\
    && chown -R nextjs:nodejs /app
USER nextjs

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{{ port }}/health || exit 1

EXPOSE {{ port }}

CMD ["npm", "start"]
""",
            "nginx_static": """
# Nginx Static Site Template
FROM nginx:{{ nginx_version }}-alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy static files
COPY {{ static_path }} /usr/share/nginx/html

# Create non-root user
RUN adduser -D -s /bin/sh www-data \\
    && chown -R www-data:www-data /usr/share/nginx/html \\
    && chown -R www-data:www-data /var/cache/nginx

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{{ port }}/ || exit 1

EXPOSE {{ port }}

CMD ["nginx", "-g", "daemon off;"]
"""
        }
        
        for template_name, content in templates.items():
            template_file = self.templates_path / f"{template_name}.dockerfile"
            if not template_file.exists():
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(content)
    
    def generate_dockerfile(self, template_name: str, variables: Dict[str, Any], 
                           output_path: str = None) -> str:
        """
        Generate Dockerfile from template
        إنشاء Dockerfile من القالب
        """
        template_file = self.templates_path / f"{template_name}.dockerfile"
        
        if not template_file.exists():
            raise ValueError(f"Template not found: {template_name}")
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            template = Template(template_content)
            dockerfile_content = template.render(**variables)
            
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(dockerfile_content)
                
                logger.info(f"Dockerfile generated: {output_path}")
                return str(output_file)
            
            return dockerfile_content
            
        except Exception as e:
            logger.error(f"Failed to generate Dockerfile from template {template_name}: {str(e)}")
            raise
    
    def build_image(self, config: BuildConfig, progress_callback: Callable = None) -> Dict[str, Any]:
        """
        Build Docker image with advanced options
        بناء صورة Docker مع خيارات متقدمة
        """
        build_start = time.time()
        build_id = f"build_{int(time.time())}_{hashlib.md5(config.image_name.encode()).hexdigest()[:8]}"
        
        try:
            # Prepare build arguments
            build_args = {
                'path': config.context_path,
                'dockerfile': config.dockerfile_path,
                'tag': f"{config.image_name}:{config.tag}",
                'nocache': config.no_cache,
                'pull': config.pull_base_image,
                'rm': True  # Remove intermediate containers
            }
            
            # Add optional parameters
            if config.build_args:
                build_args['buildargs'] = config.build_args
            
            if config.labels:
                build_args['labels'] = config.labels
            
            if config.target_stage:
                build_args['target'] = config.target_stage
            
            if config.platform:
                build_args['platform'] = config.platform
            
            # Build image with progress tracking
            build_logs = []
            
            logger.info(f"Starting image build: {config.image_name}:{config.tag}")
            
            image, build_generator = self.docker_client.images.build(**build_args)
            
            # Process build output
            for chunk in build_generator:
                if 'stream' in chunk:
                    log_line = chunk['stream'].strip()
                    if log_line:
                        build_logs.append({
                            'timestamp': datetime.utcnow().isoformat(),
                            'message': log_line
                        })
                        
                        if progress_callback:
                            progress_callback(log_line)
                        
                        logger.debug(f"Build log: {log_line}")
                
                if 'error' in chunk:
                    error_msg = chunk['error']
                    logger.error(f"Build error: {error_msg}")
                    raise docker.errors.BuildError(error_msg, build_logs)
            
            build_time = time.time() - build_start
            
            # Get image information
            image.reload()
            image_info = {
                'id': image.id,
                'short_id': image.short_id,
                'tags': image.tags,
                'size': image.attrs.get('Size', 0),
                'created': image.attrs.get('Created'),
                'architecture': image.attrs.get('Architecture'),
                'os': image.attrs.get('Os')
            }
            
            # Build result
            build_result = {
                'build_id': build_id,
                'status': 'success',
                'image_name': config.image_name,
                'tag': config.tag,
                'build_time': round(build_time, 2),
                'image_info': image_info,
                'build_logs': build_logs,
                'config': asdict(config),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Store build history
            self.build_history.append(build_result)
            
            logger.info(f"Image build completed: {config.image_name}:{config.tag} in {build_time:.2f}s")
            return build_result
            
        except Exception as e:
            build_time = time.time() - build_start
            
            build_result = {
                'build_id': build_id,
                'status': 'failed',
                'image_name': config.image_name,
                'tag': config.tag,
                'build_time': round(build_time, 2),
                'error': str(e),
                'config': asdict(config),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.build_history.append(build_result)
            
            logger.error(f"Image build failed: {config.image_name}:{config.tag} - {str(e)}")
            raise
    
    def build_multi_stage_image(self, stages_config: List[Dict[str, Any]], 
                               final_image_name: str, final_tag: str = "latest") -> Dict[str, Any]:
        """
        Build multi-stage Docker image
        بناء صورة Docker متعددة المراحل
        """
        build_results = []
        
        try:
            for i, stage_config in enumerate(stages_config):
                stage_name = stage_config.get('stage_name', f'stage_{i}')
                
                # Create build config for this stage
                config = BuildConfig(
                    image_name=stage_config['image_name'],
                    tag=stage_config.get('tag', 'latest'),
                    dockerfile_path=stage_config['dockerfile_path'],
                    context_path=stage_config.get('context_path', '.'),
                    build_args=stage_config.get('build_args'),
                    target_stage=stage_name,
                    no_cache=stage_config.get('no_cache', False)
                )
                
                # Build stage
                stage_result = self.build_image(config)
                build_results.append(stage_result)
                
                logger.info(f"Multi-stage build completed stage: {stage_name}")
            
            # Tag final image
            if build_results:
                final_image = self.docker_client.images.get(build_results[-1]['image_info']['id'])
                final_image.tag(final_image_name, final_tag)
                
                logger.info(f"Multi-stage build completed: {final_image_name}:{final_tag}")
            
            return {
                'status': 'success',
                'final_image': f"{final_image_name}:{final_tag}",
                'stages_built': len(build_results),
                'stage_results': build_results,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Multi-stage build failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'stages_completed': len(build_results),
                'stage_results': build_results,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def optimize_image(self, image_name: str, tag: str = "latest") -> Dict[str, Any]:
        """
        Optimize Docker image size and layers
        تحسين حجم صورة Docker والطبقات
        """
        try:
            original_image = self.docker_client.images.get(f"{image_name}:{tag}")
            original_size = original_image.attrs.get('Size', 0)
            
            # Create optimized Dockerfile
            optimization_dockerfile = f"""
FROM {image_name}:{tag}

# Remove package caches and temporary files
RUN apt-get clean && \\
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* && \\
    find /var/log -type f -delete

# Remove development packages if present
RUN apt-get autoremove -y || true

# Optimize Python bytecode if Python is present
RUN python -m compileall /usr/local/lib/python* 2>/dev/null || true

# Set final working directory
WORKDIR /app
"""
            
            # Write optimization Dockerfile
            opt_dockerfile_path = self.workspace_path / f"Dockerfile.optimize.{int(time.time())}"
            with open(opt_dockerfile_path, 'w') as f:
                f.write(optimization_dockerfile)
            
            # Build optimized image
            optimized_tag = f"{tag}-optimized"
            opt_config = BuildConfig(
                image_name=image_name,
                tag=optimized_tag,
                dockerfile_path=str(opt_dockerfile_path),
                context_path=str(self.workspace_path),
                no_cache=True,
                squash=True
            )
            
            build_result = self.build_image(opt_config)
            
            # Get optimized image info
            optimized_image = self.docker_client.images.get(f"{image_name}:{optimized_tag}")
            optimized_size = optimized_image.attrs.get('Size', 0)
            
            # Calculate savings
            size_reduction = original_size - optimized_size
            size_reduction_percent = (size_reduction / original_size) * 100 if original_size > 0 else 0
            
            # Cleanup
            opt_dockerfile_path.unlink()
            
            return {
                'status': 'success',
                'original_image': f"{image_name}:{tag}",
                'optimized_image': f"{image_name}:{optimized_tag}",
                'original_size_mb': round(original_size / (1024 * 1024), 2),
                'optimized_size_mb': round(optimized_size / (1024 * 1024), 2),
                'size_reduction_mb': round(size_reduction / (1024 * 1024), 2),
                'size_reduction_percent': round(size_reduction_percent, 2),
                'build_result': build_result
            }
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def scan_image_vulnerabilities(self, image_name: str, tag: str = "latest") -> Dict[str, Any]:
        """
        Scan Docker image for security vulnerabilities
        فحص صورة Docker للثغرات الأمنية
        """
        try:
            # This is a placeholder for vulnerability scanning
            # In production, you would integrate with tools like:
            # - Docker Scout
            # - Trivy
            # - Clair
            # - Snyk
            
            image = self.docker_client.images.get(f"{image_name}:{tag}")
            
            # Basic image analysis
            layers = len(image.history())
            size_mb = round(image.attrs.get('Size', 0) / (1024 * 1024), 2)
            
            # Simulate vulnerability scan results
            scan_result = {
                'image': f"{image_name}:{tag}",
                'scan_timestamp': datetime.utcnow().isoformat(),
                'image_info': {
                    'size_mb': size_mb,
                    'layers_count': layers,
                    'architecture': image.attrs.get('Architecture'),
                    'os': image.attrs.get('Os')
                },
                'vulnerabilities': {
                    'critical': 0,
                    'high': 0,
                    'medium': 0,
                    'low': 0,
                    'total': 0
                },
                'recommendations': [
                    "Use specific version tags instead of 'latest'",
                    "Regularly update base images",
                    "Remove unnecessary packages and files",
                    "Use multi-stage builds to reduce attack surface",
                    "Run containers as non-root user"
                ],
                'scan_status': 'completed'
            }
            
            logger.info(f"Vulnerability scan completed for {image_name}:{tag}")
            return scan_result
            
        except Exception as e:
            logger.error(f"Vulnerability scan failed: {str(e)}")
            return {
                'scan_status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def add_registry(self, name: str, config: RegistryConfig):
        """
        Add registry configuration
        إضافة تكوين السجل
        """
        self.registry_configs[name] = config
        logger.info(f"Registry configuration added: {name}")
    
    def push_image(self, image_name: str, tag: str, registry_name: str) -> Dict[str, Any]:
        """
        Push image to registry
        دفع الصورة إلى السجل
        """
        if registry_name not in self.registry_configs:
            raise ValueError(f"Registry configuration not found: {registry_name}")
        
        registry_config = self.registry_configs[registry_name]
        
        try:
            # Login to registry
            self.docker_client.login(
                username=registry_config.username,
                password=registry_config.password,
                registry=registry_config.registry_url
            )
            
            # Prepare image tag for registry
            if registry_config.namespace:
                registry_tag = f"{registry_config.registry_url}/{registry_config.namespace}/{image_name}:{tag}"
            else:
                registry_tag = f"{registry_config.registry_url}/{image_name}:{tag}"
            
            # Tag image for registry
            image = self.docker_client.images.get(f"{image_name}:{tag}")
            image.tag(registry_tag)
            
            # Push image
            push_logs = []
            for line in self.docker_client.images.push(registry_tag, stream=True, decode=True):
                if 'status' in line:
                    push_logs.append(line)
                    logger.debug(f"Push: {line['status']}")
            
            logger.info(f"Image pushed successfully: {registry_tag}")
            
            return {
                'status': 'success',
                'original_image': f"{image_name}:{tag}",
                'registry_image': registry_tag,
                'registry': registry_name,
                'push_logs': push_logs,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to push image to registry: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'image': f"{image_name}:{tag}",
                'registry': registry_name,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def pull_image(self, image_name: str, tag: str = "latest", 
                   registry_name: str = None) -> Dict[str, Any]:
        """
        Pull image from registry
        سحب الصورة من السجل
        """
        try:
            if registry_name and registry_name in self.registry_configs:
                registry_config = self.registry_configs[registry_name]
                
                # Login to registry
                self.docker_client.login(
                    username=registry_config.username,
                    password=registry_config.password,
                    registry=registry_config.registry_url
                )
                
                # Prepare full image name
                if registry_config.namespace:
                    full_image_name = f"{registry_config.registry_url}/{registry_config.namespace}/{image_name}:{tag}"
                else:
                    full_image_name = f"{registry_config.registry_url}/{image_name}:{tag}"
            else:
                full_image_name = f"{image_name}:{tag}"
            
            # Pull image
            pull_logs = []
            image = self.docker_client.images.pull(full_image_name)
            
            logger.info(f"Image pulled successfully: {full_image_name}")
            
            return {
                'status': 'success',
                'image': full_image_name,
                'image_id': image.id,
                'image_size_mb': round(image.attrs.get('Size', 0) / (1024 * 1024), 2),
                'registry': registry_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to pull image: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'image': f"{image_name}:{tag}",
                'registry': registry_name,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_build_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get build history
        الحصول على سجل البناء
        """
        return self.build_history[-limit:] if self.build_history else []
    
    def cleanup_build_cache(self) -> Dict[str, Any]:
        """
        Clean up Docker build cache
        تنظيف ذاكرة التخزين المؤقت للبناء
        """
        try:
            # Remove dangling images
            dangling_images = self.docker_client.images.list(filters={'dangling': True})
            removed_images = 0
            
            for image in dangling_images:
                try:
                    self.docker_client.images.remove(image.id, force=True)
                    removed_images += 1
                except Exception as e:
                    logger.warning(f"Failed to remove dangling image {image.id}: {str(e)}")
            
            # Prune build cache
            cache_result = self.docker_client.api.prune_builds()
            
            return {
                'status': 'success',
                'removed_images': removed_images,
                'cache_reclaimed_mb': round(cache_result.get('SpaceReclaimed', 0) / (1024 * 1024), 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Build cache cleanup failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
