# Service ID: ATS78 - Part 3
# Notification and System Monitoring Bots
# بوتات الإشعارات ومراقبة النظام

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import psutil
import subprocess
import threading
import schedule
from dataclasses import dataclass
import sqlite3
import hashlib

logger = logging.getLogger(__name__)

# Import base classes
from .automation_bots import AutomationBot, BotTask, BotExecution, BotStatus, BotType, TaskPriority

# ==================== SECTION 5: Notification Bot ====================

@dataclass
class NotificationConfig:
    """
    Notification configuration
    تكوين الإشعارات
    """
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    webhook_urls: List[str] = None
    slack_webhook_url: str = ""
    discord_webhook_url: str = ""

class NotificationBot(AutomationBot):
    """
    Notification and alerting automation bot
    بوت أتمتة الإشعارات والتنبيهات
    """
    
    def __init__(self, bot_id: str, name: str, workspace_path: str = "./bot_workspace"):
        super().__init__(bot_id, name, BotType.NOTIFICATION_BOT, workspace_path)
        self.notification_config = NotificationConfig()
        self.notification_history: List[Dict[str, Any]] = []
        self.notification_stats = {
            "total_notifications": 0,
            "successful_notifications": 0,
            "failed_notifications": 0,
            "email_notifications": 0,
            "webhook_notifications": 0
        }
    
    def configure_notifications(self, config: NotificationConfig) -> None:
        """
        Configure notification settings
        تكوين إعدادات الإشعارات
        """
        self.notification_config = config
        logger.info(f"Notification configuration updated for bot {self.bot_id}")
    
    def _perform_task_action(self, task: BotTask) -> Dict[str, Any]:
        """
        Perform notification task
        تنفيذ مهمة الإشعار
        """
        action_type = task.parameters.get('action_type')
        
        if action_type == 'send_email':
            return self._send_email_action(task.parameters)
        elif action_type == 'send_webhook':
            return self._send_webhook_action(task.parameters)
        elif action_type == 'send_slack_message':
            return self._send_slack_message_action(task.parameters)
        elif action_type == 'send_discord_message':
            return self._send_discord_message_action(task.parameters)
        elif action_type == 'send_system_alert':
            return self._send_system_alert_action(task.parameters)
        else:
            raise ValueError(f"Unknown notification action: {action_type}")
    
    def _send_email_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send email notification
        إرسال إشعار بريد إلكتروني
        """
        recipients = params.get('recipients', [])
        subject = params.get('subject', 'Automation Bot Notification')
        body = params.get('body', '')
        attachments = params.get('attachments', [])
        
        if not recipients:
            raise ValueError("Recipients list is required for email notification")
        
        if not self.notification_config.email_username:
            raise ValueError("Email configuration not set")
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.notification_config.email_username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Add attachments
            for attachment_path in attachments:
                if Path(attachment_path).exists():
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {Path(attachment_path).name}'
                        )
                        msg.attach(part)
            
            # Send email
            with smtplib.SMTP(self.notification_config.email_smtp_server, 
                            self.notification_config.email_smtp_port) as server:
                server.starttls()
                server.login(self.notification_config.email_username, 
                           self.notification_config.email_password)
                server.send_message(msg)
            
            # Update statistics
            self.notification_stats["total_notifications"] += 1
            self.notification_stats["successful_notifications"] += 1
            self.notification_stats["email_notifications"] += 1
            
            # Log notification
            notification_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "email",
                "recipients": recipients,
                "subject": subject,
                "status": "success"
            }
            self.notification_history.append(notification_record)
            
            return {
                "action": "send_email",
                "recipients": recipients,
                "subject": subject,
                "attachments_count": len(attachments),
                "status": "success"
            }
            
        except Exception as e:
            self.notification_stats["total_notifications"] += 1
            self.notification_stats["failed_notifications"] += 1
            
            notification_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "email",
                "recipients": recipients,
                "subject": subject,
                "status": "failed",
                "error": str(e)
            }
            self.notification_history.append(notification_record)
            
            raise Exception(f"Email notification failed: {str(e)}")
    
    def _send_webhook_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send webhook notification
        إرسال إشعار webhook
        """
        webhook_url = params.get('webhook_url')
        payload = params.get('payload', {})
        headers = params.get('headers', {'Content-Type': 'application/json'})
        
        if not webhook_url:
            raise ValueError("webhook_url is required")
        
        try:
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Update statistics
            self.notification_stats["total_notifications"] += 1
            self.notification_stats["successful_notifications"] += 1
            self.notification_stats["webhook_notifications"] += 1
            
            # Log notification
            notification_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "webhook",
                "webhook_url": webhook_url,
                "status": "success",
                "response_code": response.status_code
            }
            self.notification_history.append(notification_record)
            
            return {
                "action": "send_webhook",
                "webhook_url": webhook_url,
                "response_code": response.status_code,
                "status": "success"
            }
            
        except Exception as e:
            self.notification_stats["total_notifications"] += 1
            self.notification_stats["failed_notifications"] += 1
            
            notification_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "webhook",
                "webhook_url": webhook_url,
                "status": "failed",
                "error": str(e)
            }
            self.notification_history.append(notification_record)
            
            raise Exception(f"Webhook notification failed: {str(e)}")
    
    def _send_slack_message_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send Slack message notification
        إرسال إشعار رسالة Slack
        """
        message = params.get('message', '')
        channel = params.get('channel', '#general')
        username = params.get('username', 'Automation Bot')
        
        if not self.notification_config.slack_webhook_url:
            raise ValueError("Slack webhook URL not configured")
        
        payload = {
            "text": message,
            "channel": channel,
            "username": username,
            "icon_emoji": ":robot_face:"
        }
        
        try:
            response = requests.post(
                self.notification_config.slack_webhook_url,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            self.notification_stats["total_notifications"] += 1
            self.notification_stats["successful_notifications"] += 1
            
            return {
                "action": "send_slack_message",
                "channel": channel,
                "message": message[:100] + "..." if len(message) > 100 else message,
                "status": "success"
            }
            
        except Exception as e:
            self.notification_stats["total_notifications"] += 1
            self.notification_stats["failed_notifications"] += 1
            raise Exception(f"Slack notification failed: {str(e)}")
    
    def _send_system_alert_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send system alert with multiple channels
        إرسال تنبيه النظام بقنوات متعددة
        """
        alert_level = params.get('alert_level', 'info')  # info, warning, error, critical
        message = params.get('message', '')
        channels = params.get('channels', ['email'])  # email, webhook, slack, discord
        
        results = {}
        successful_channels = 0
        
        for channel in channels:
            try:
                if channel == 'email' and self.notification_config.email_username:
                    # Send email alert
                    email_params = {
                        'recipients': params.get('email_recipients', []),
                        'subject': f"[{alert_level.upper()}] System Alert",
                        'body': f"Alert Level: {alert_level}\nMessage: {message}\nTime: {datetime.utcnow()}"
                    }
                    email_result = self._send_email_action(email_params)
                    results[channel] = email_result
                    successful_channels += 1
                
                elif channel == 'slack' and self.notification_config.slack_webhook_url:
                    # Send Slack alert
                    slack_params = {
                        'message': f":warning: *{alert_level.upper()} Alert*\n{message}",
                        'channel': params.get('slack_channel', '#alerts')
                    }
                    slack_result = self._send_slack_message_action(slack_params)
                    results[channel] = slack_result
                    successful_channels += 1
                
                elif channel == 'webhook' and params.get('webhook_url'):
                    # Send webhook alert
                    webhook_params = {
                        'webhook_url': params.get('webhook_url'),
                        'payload': {
                            'alert_level': alert_level,
                            'message': message,
                            'timestamp': datetime.utcnow().isoformat(),
                            'bot_id': self.bot_id
                        }
                    }
                    webhook_result = self._send_webhook_action(webhook_params)
                    results[channel] = webhook_result
                    successful_channels += 1
                
            except Exception as e:
                results[channel] = {"status": "failed", "error": str(e)}
        
        return {
            "action": "send_system_alert",
            "alert_level": alert_level,
            "message": message,
            "channels_attempted": len(channels),
            "successful_channels": successful_channels,
            "results": results
        }

# ==================== SECTION 6: System Monitor Bot ====================

class SystemMonitorBot(AutomationBot):
    """
    System monitoring and performance tracking bot
    بوت مراقبة النظام وتتبع الأداء
    """
    
    def __init__(self, bot_id: str, name: str, workspace_path: str = "./bot_workspace"):
        super().__init__(bot_id, name, BotType.SYSTEM_MONITOR, workspace_path)
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_interval = 60  # seconds
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "network_errors": 100
        }
        self.monitoring_data: List[Dict[str, Any]] = []
        self.alert_history: List[Dict[str, Any]] = []
    
    def _perform_task_action(self, task: BotTask) -> Dict[str, Any]:
        """
        Perform system monitoring task
        تنفيذ مهمة مراقبة النظام
        """
        action_type = task.parameters.get('action_type')
        
        if action_type == 'start_monitoring':
            return self._start_monitoring_action(task.parameters)
        elif action_type == 'stop_monitoring':
            return self._stop_monitoring_action(task.parameters)
        elif action_type == 'get_system_info':
            return self._get_system_info_action(task.parameters)
        elif action_type == 'check_processes':
            return self._check_processes_action(task.parameters)
        elif action_type == 'monitor_disk_space':
            return self._monitor_disk_space_action(task.parameters)
        elif action_type == 'generate_report':
            return self._generate_report_action(task.parameters)
        else:
            raise ValueError(f"Unknown system monitoring action: {action_type}")
    
    def _start_monitoring_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start system monitoring
        بدء مراقبة النظام
        """
        self.monitoring_interval = params.get('interval', 60)
        custom_thresholds = params.get('alert_thresholds', {})
        self.alert_thresholds.update(custom_thresholds)
        
        if self.monitoring_active:
            return {
                "action": "start_monitoring",
                "status": "already_running",
                "message": "System monitoring is already active"
            }
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        return {
            "action": "start_monitoring",
            "status": "started",
            "interval": self.monitoring_interval,
            "alert_thresholds": self.alert_thresholds
        }
    
    def _stop_monitoring_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stop system monitoring
        إيقاف مراقبة النظام
        """
        if not self.monitoring_active:
            return {
                "action": "stop_monitoring",
                "status": "not_running",
                "message": "System monitoring is not active"
            }
        
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        return {
            "action": "stop_monitoring",
            "status": "stopped",
            "data_points_collected": len(self.monitoring_data),
            "alerts_generated": len(self.alert_history)
        }
    
    def _get_system_info_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get current system information
        الحصول على معلومات النظام الحالية
        """
        try:
            # CPU information
            cpu_info = {
                "usage_percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
            }
            
            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            }
            
            # Disk information
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100
                    })
                except PermissionError:
                    continue
            
            # Network information
            network = psutil.net_io_counters()
            network_info = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
                "errin": network.errin,
                "errout": network.errout
            }
            
            # Boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            
            system_info = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "network": network_info,
                "boot_time": boot_time.isoformat(),
                "uptime_seconds": (datetime.utcnow() - boot_time).total_seconds()
            }
            
            return {
                "action": "get_system_info",
                "system_info": system_info
            }
            
        except Exception as e:
            raise Exception(f"Failed to get system info: {str(e)}")
    
    def _check_processes_action(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check running processes
        فحص العمليات الجارية
        """
        process_filter = params.get('process_filter', {})
        sort_by = params.get('sort_by', 'cpu_percent')
        limit = params.get('limit', 10)
        
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    proc_info = proc.info
                    
                    # Apply filters
                    if process_filter:
                        if 'name_contains' in process_filter:
                            if process_filter['name_contains'].lower() not in proc_info['name'].lower():
                                continue
                        
                        if 'min_cpu_percent' in process_filter:
                            if proc_info['cpu_percent'] < process_filter['min_cpu_percent']:
                                continue
                        
                        if 'min_memory_percent' in process_filter:
                            if proc_info['memory_percent'] < process_filter['min_memory_percent']:
                                continue
                    
                    processes.append(proc_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort processes
            if sort_by in ['cpu_percent', 'memory_percent']:
                processes.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
            
            # Limit results
            processes = processes[:limit]
            
            return {
                "action": "check_processes",
                "total_processes": len(processes),
                "processes": processes,
                "sort_by": sort_by,
                "filter_applied": bool(process_filter)
            }
            
        except Exception as e:
            raise Exception(f"Failed to check processes: {str(e)}")
    
    def _monitoring_loop(self) -> None:
        """
        Main monitoring loop
        حلقة المراقبة الرئيسية
        """
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                self.monitoring_data.append(metrics)
                
                # Check for alerts
                alerts = self._check_alert_conditions(metrics)
                if alerts:
                    self.alert_history.extend(alerts)
                    logger.warning(f"System alerts generated: {len(alerts)}")
                
                # Keep only recent data (last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.monitoring_data = [
                    data for data in self.monitoring_data
                    if datetime.fromisoformat(data['timestamp']) > cutoff_time
                ]
                
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}")
                time.sleep(60)  # Wait before retrying
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """
        Collect current system metrics
        جمع مقاييس النظام الحالية
        """
        timestamp = datetime.utcnow()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk_usage = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage.append({
                    "device": partition.device,
                    "percent": (usage.used / usage.total) * 100
                })
            except PermissionError:
                continue
        
        # Network metrics
        network = psutil.net_io_counters()
        
        return {
            "timestamp": timestamp.isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_usage": disk_usage,
            "network_bytes_sent": network.bytes_sent,
            "network_bytes_recv": network.bytes_recv,
            "network_errors": network.errin + network.errout
        }
    
    def _check_alert_conditions(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check if any alert conditions are met
        فحص ما إذا كانت أي شروط التنبيه مستوفاة
        """
        alerts = []
        timestamp = metrics['timestamp']
        
        # CPU alert
        if metrics['cpu_percent'] > self.alert_thresholds['cpu_percent']:
            alerts.append({
                "timestamp": timestamp,
                "type": "cpu_high",
                "severity": "warning",
                "message": f"High CPU usage: {metrics['cpu_percent']:.1f}%",
                "value": metrics['cpu_percent'],
                "threshold": self.alert_thresholds['cpu_percent']
            })
        
        # Memory alert
        if metrics['memory_percent'] > self.alert_thresholds['memory_percent']:
            alerts.append({
                "timestamp": timestamp,
                "type": "memory_high",
                "severity": "warning",
                "message": f"High memory usage: {metrics['memory_percent']:.1f}%",
                "value": metrics['memory_percent'],
                "threshold": self.alert_thresholds['memory_percent']
            })
        
        # Disk alerts
        for disk in metrics['disk_usage']:
            if disk['percent'] > self.alert_thresholds['disk_percent']:
                alerts.append({
                    "timestamp": timestamp,
                    "type": "disk_high",
                    "severity": "critical",
                    "message": f"High disk usage on {disk['device']}: {disk['percent']:.1f}%",
                    "value": disk['percent'],
                    "threshold": self.alert_thresholds['disk_percent'],
                    "device": disk['device']
                })
        
        return alerts
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        Get monitoring summary and statistics
        الحصول على ملخص المراقبة والإحصائيات
        """
        if not self.monitoring_data:
            return {
                "status": "no_data",
                "message": "No monitoring data available"
            }
        
        # Calculate averages from recent data
        recent_data = self.monitoring_data[-60:]  # Last 60 data points
        
        avg_cpu = sum(d['cpu_percent'] for d in recent_data) / len(recent_data)
        avg_memory = sum(d['memory_percent'] for d in recent_data) / len(recent_data)
        
        return {
            "monitoring_active": self.monitoring_active,
            "data_points": len(self.monitoring_data),
            "monitoring_duration_hours": len(self.monitoring_data) * self.monitoring_interval / 3600,
            "recent_averages": {
                "cpu_percent": round(avg_cpu, 2),
                "memory_percent": round(avg_memory, 2)
            },
            "total_alerts": len(self.alert_history),
            "recent_alerts": len([a for a in self.alert_history 
                                if datetime.fromisoformat(a['timestamp']) > datetime.utcnow() - timedelta(hours=1)]),
            "alert_thresholds": self.alert_thresholds
        }
