# Service ID: AIQ82 - Data Visualization and Reporting Engine
# محرك تصور البيانات والتقارير المتقدم

import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json
import base64
from io import BytesIO

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

logger = logging.getLogger(__name__)

@dataclass
class VisualizationConfig:
    """
    Data visualization configuration
    تكوين تصور البيانات
    """
    chart_type: str
    title: str
    x_column: str = None
    y_column: str = None
    color_column: str = None
    size_column: str = None
    theme: str = "default"
    width: int = 800
    height: int = 600
    interactive: bool = True
    export_format: str = "html"

@dataclass
class ReportConfig:
    """
    Report generation configuration
    تكوين إنشاء التقارير
    """
    title: str
    author: str = "Data Analysis System"
    template: str = "standard"
    include_charts: bool = True
    include_statistics: bool = True
    include_raw_data: bool = False
    export_format: str = "pdf"

class VisualizationEngine:
    """
    Advanced data visualization and reporting engine
    محرك تصور البيانات والتقارير المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.charts_path = workspace_path / "charts"
        self.reports_path = workspace_path / "reports"
        self.templates_path = workspace_path / "report_templates"
        
        for path in [self.charts_path, self.reports_path, self.templates_path]:
            path.mkdir(exist_ok=True)
        
        self.chart_history: List[Dict[str, Any]] = []
        self.report_history: List[Dict[str, Any]] = []
        
        # Set visualization themes
        self._setup_themes()
    
    def _setup_themes(self):
        """
        Setup visualization themes
        إعداد موضوعات التصور
        """
        # Seaborn themes
        sns.set_style("whitegrid")
        
        # Custom color palettes
        self.color_palettes = {
            "business": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
            "modern": ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"],
            "professional": ["#2c3e50", "#34495e", "#7f8c8d", "#95a5a6", "#bdc3c7"],
            "vibrant": ["#e91e63", "#9c27b0", "#673ab7", "#3f51b5", "#2196f3"]
        }
    
    def create_chart(self, data: pd.DataFrame, config: VisualizationConfig) -> Dict[str, Any]:
        """
        Create interactive or static chart
        إنشاء مخطط تفاعلي أو ثابت
        """
        chart_start = datetime.utcnow()
        chart_id = f"chart_{int(chart_start.timestamp())}"
        
        try:
            if config.interactive:
                chart_result = self._create_plotly_chart(data, config, chart_id)
            else:
                chart_result = self._create_matplotlib_chart(data, config, chart_id)
            
            # Record chart creation
            chart_info = {
                'chart_id': chart_id,
                'chart_type': config.chart_type,
                'title': config.title,
                'data_rows': len(data),
                'data_columns': len(data.columns),
                'interactive': config.interactive,
                'created_at': chart_start.isoformat(),
                'file_path': chart_result.get('file_path'),
                'file_size_kb': chart_result.get('file_size_kb', 0)
            }
            
            self.chart_history.append(chart_info)
            
            logger.info(f"Chart created successfully: {chart_id}")
            return {
                'status': 'success',
                'chart_info': chart_info,
                **chart_result
            }
            
        except Exception as e:
            logger.error(f"Chart creation failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'chart_id': chart_id
            }
    
    def _create_plotly_chart(self, data: pd.DataFrame, config: VisualizationConfig, chart_id: str) -> Dict[str, Any]:
        """
        Create interactive Plotly chart
        إنشاء مخطط Plotly تفاعلي
        """
        fig = None
        
        if config.chart_type == "scatter":
            fig = px.scatter(
                data, x=config.x_column, y=config.y_column,
                color=config.color_column, size=config.size_column,
                title=config.title,
                width=config.width, height=config.height
            )
        
        elif config.chart_type == "line":
            fig = px.line(
                data, x=config.x_column, y=config.y_column,
                color=config.color_column,
                title=config.title,
                width=config.width, height=config.height
            )
        
        elif config.chart_type == "bar":
            fig = px.bar(
                data, x=config.x_column, y=config.y_column,
                color=config.color_column,
                title=config.title,
                width=config.width, height=config.height
            )
        
        elif config.chart_type == "histogram":
            fig = px.histogram(
                data, x=config.x_column,
                color=config.color_column,
                title=config.title,
                width=config.width, height=config.height
            )
        
        elif config.chart_type == "box":
            fig = px.box(
                data, x=config.x_column, y=config.y_column,
                color=config.color_column,
                title=config.title,
                width=config.width, height=config.height
            )
        
        elif config.chart_type == "heatmap":
            # Create correlation heatmap for numeric columns
            numeric_data = data.select_dtypes(include=[np.number])
            correlation_matrix = numeric_data.corr()
            
            fig = px.imshow(
                correlation_matrix,
                title=config.title,
                color_continuous_scale="RdBu_r",
                width=config.width, height=config.height
            )
        
        elif config.chart_type == "pie":
            value_counts = data[config.x_column].value_counts()
            fig = px.pie(
                values=value_counts.values,
                names=value_counts.index,
                title=config.title,
                width=config.width, height=config.height
            )
        
        else:
            raise ValueError(f"Unsupported chart type: {config.chart_type}")
        
        # Apply theme
        if config.theme in self.color_palettes:
            fig.update_layout(colorway=self.color_palettes[config.theme])
        
        # Save chart
        if config.export_format == "html":
            file_path = self.charts_path / f"{chart_id}.html"
            fig.write_html(str(file_path))
        elif config.export_format == "png":
            file_path = self.charts_path / f"{chart_id}.png"
            fig.write_image(str(file_path))
        elif config.export_format == "pdf":
            file_path = self.charts_path / f"{chart_id}.pdf"
            fig.write_image(str(file_path))
        else:
            file_path = self.charts_path / f"{chart_id}.html"
            fig.write_html(str(file_path))
        
        file_size_kb = round(file_path.stat().st_size / 1024, 2) if file_path.exists() else 0
        
        return {
            'file_path': str(file_path),
            'file_size_kb': file_size_kb,
            'chart_html': fig.to_html() if config.export_format == "html" else None
        }
    
    def _create_matplotlib_chart(self, data: pd.DataFrame, config: VisualizationConfig, chart_id: str) -> Dict[str, Any]:
        """
        Create static Matplotlib chart
        إنشاء مخطط Matplotlib ثابت
        """
        plt.figure(figsize=(config.width/100, config.height/100))
        
        # Apply theme colors
        colors = self.color_palettes.get(config.theme, self.color_palettes["business"])
        
        if config.chart_type == "scatter":
            plt.scatter(data[config.x_column], data[config.y_column], 
                       c=colors[0], alpha=0.7)
            plt.xlabel(config.x_column)
            plt.ylabel(config.y_column)
        
        elif config.chart_type == "line":
            plt.plot(data[config.x_column], data[config.y_column], 
                    color=colors[0], linewidth=2)
            plt.xlabel(config.x_column)
            plt.ylabel(config.y_column)
        
        elif config.chart_type == "bar":
            plt.bar(data[config.x_column], data[config.y_column], 
                   color=colors[0])
            plt.xlabel(config.x_column)
            plt.ylabel(config.y_column)
            plt.xticks(rotation=45)
        
        elif config.chart_type == "histogram":
            plt.hist(data[config.x_column], bins=30, color=colors[0], alpha=0.7)
            plt.xlabel(config.x_column)
            plt.ylabel("Frequency")
        
        elif config.chart_type == "heatmap":
            numeric_data = data.select_dtypes(include=[np.number])
            correlation_matrix = numeric_data.corr()
            sns.heatmap(correlation_matrix, annot=True, cmap="RdBu_r", center=0)
        
        else:
            raise ValueError(f"Unsupported chart type for matplotlib: {config.chart_type}")
        
        plt.title(config.title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        # Save chart
        file_path = self.charts_path / f"{chart_id}.png"
        plt.savefig(str(file_path), dpi=300, bbox_inches='tight')
        plt.close()
        
        file_size_kb = round(file_path.stat().st_size / 1024, 2)
        
        return {
            'file_path': str(file_path),
            'file_size_kb': file_size_kb
        }
    
    def create_dashboard(self, data: pd.DataFrame, charts_config: List[VisualizationConfig]) -> Dict[str, Any]:
        """
        Create interactive dashboard with multiple charts
        إنشاء لوحة معلومات تفاعلية مع مخططات متعددة
        """
        dashboard_start = datetime.utcnow()
        dashboard_id = f"dashboard_{int(dashboard_start.timestamp())}"
        
        try:
            # Create subplot layout
            rows = int(np.ceil(len(charts_config) / 2))
            cols = 2 if len(charts_config) > 1 else 1
            
            fig = make_subplots(
                rows=rows, cols=cols,
                subplot_titles=[config.title for config in charts_config],
                specs=[[{"secondary_y": False} for _ in range(cols)] for _ in range(rows)]
            )
            
            # Add charts to subplots
            for i, config in enumerate(charts_config):
                row = (i // cols) + 1
                col = (i % cols) + 1
                
                if config.chart_type == "scatter":
                    fig.add_trace(
                        go.Scatter(
                            x=data[config.x_column],
                            y=data[config.y_column],
                            mode='markers',
                            name=config.title
                        ),
                        row=row, col=col
                    )
                
                elif config.chart_type == "line":
                    fig.add_trace(
                        go.Scatter(
                            x=data[config.x_column],
                            y=data[config.y_column],
                            mode='lines',
                            name=config.title
                        ),
                        row=row, col=col
                    )
                
                elif config.chart_type == "bar":
                    fig.add_trace(
                        go.Bar(
                            x=data[config.x_column],
                            y=data[config.y_column],
                            name=config.title
                        ),
                        row=row, col=col
                    )
            
            # Update layout
            fig.update_layout(
                height=600 * rows,
                showlegend=True,
                title_text=f"Data Analysis Dashboard - {dashboard_start.strftime('%Y-%m-%d %H:%M')}"
            )
            
            # Save dashboard
            dashboard_path = self.charts_path / f"{dashboard_id}.html"
            fig.write_html(str(dashboard_path))
            
            file_size_kb = round(dashboard_path.stat().st_size / 1024, 2)
            
            dashboard_info = {
                'dashboard_id': dashboard_id,
                'charts_count': len(charts_config),
                'data_rows': len(data),
                'created_at': dashboard_start.isoformat(),
                'file_path': str(dashboard_path),
                'file_size_kb': file_size_kb
            }
            
            logger.info(f"Dashboard created successfully: {dashboard_id}")
            return {
                'status': 'success',
                'dashboard_info': dashboard_info
            }
            
        except Exception as e:
            logger.error(f"Dashboard creation failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'dashboard_id': dashboard_id
            }
    
    def generate_report(self, data: pd.DataFrame, config: ReportConfig, 
                       charts: List[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive data analysis report
        إنشاء تقرير تحليل البيانات الشامل
        """
        report_start = datetime.utcnow()
        report_id = f"report_{int(report_start.timestamp())}"
        
        try:
            if config.export_format == "pdf":
                report_result = self._generate_pdf_report(data, config, report_id, charts)
            elif config.export_format == "html":
                report_result = self._generate_html_report(data, config, report_id, charts)
            else:
                raise ValueError(f"Unsupported report format: {config.export_format}")
            
            report_info = {
                'report_id': report_id,
                'title': config.title,
                'author': config.author,
                'data_rows': len(data),
                'data_columns': len(data.columns),
                'include_charts': config.include_charts,
                'include_statistics': config.include_statistics,
                'created_at': report_start.isoformat(),
                'file_path': report_result.get('file_path'),
                'file_size_kb': report_result.get('file_size_kb', 0)
            }
            
            self.report_history.append(report_info)
            
            logger.info(f"Report generated successfully: {report_id}")
            return {
                'status': 'success',
                'report_info': report_info,
                **report_result
            }
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'report_id': report_id
            }
    
    def _generate_pdf_report(self, data: pd.DataFrame, config: ReportConfig, 
                           report_id: str, charts: List[str] = None) -> Dict[str, Any]:
        """
        Generate PDF report using ReportLab
        إنشاء تقرير PDF باستخدام ReportLab
        """
        report_path = self.reports_path / f"{report_id}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(str(report_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(config.title, title_style))
        story.append(Spacer(1, 12))
        
        # Report metadata
        story.append(Paragraph(f"<b>Author:</b> {config.author}", styles['Normal']))
        story.append(Paragraph(f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Paragraph(f"<b>Data Rows:</b> {len(data):,}", styles['Normal']))
        story.append(Paragraph(f"<b>Data Columns:</b> {len(data.columns)}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Data overview
        story.append(Paragraph("Data Overview", styles['Heading2']))
        
        # Column information
        column_info = []
        column_info.append(['Column Name', 'Data Type', 'Non-Null Count', 'Unique Values'])
        
        for col in data.columns:
            column_info.append([
                col,
                str(data[col].dtype),
                str(data[col].count()),
                str(data[col].nunique())
            ])
        
        # Create table
        table = Table(column_info)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Statistics
        if config.include_statistics:
            story.append(Paragraph("Statistical Summary", styles['Heading2']))
            
            numeric_data = data.select_dtypes(include=[np.number])
            if not numeric_data.empty:
                stats = numeric_data.describe()
                
                stats_info = []
                stats_info.append(['Statistic'] + list(stats.columns))
                
                for stat in stats.index:
                    row = [stat] + [f"{val:.2f}" if isinstance(val, (int, float)) else str(val) 
                                   for val in stats.loc[stat]]
                    stats_info.append(row)
                
                stats_table = Table(stats_info)
                stats_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(stats_table)
                story.append(Spacer(1, 20))
        
        # Add charts if provided
        if config.include_charts and charts:
            story.append(Paragraph("Data Visualizations", styles['Heading2']))
            
            for chart_path in charts:
                if Path(chart_path).exists():
                    try:
                        img = Image(chart_path, width=6*inch, height=4*inch)
                        story.append(img)
                        story.append(Spacer(1, 12))
                    except Exception as e:
                        logger.warning(f"Failed to add chart to report: {str(e)}")
        
        # Raw data sample
        if config.include_raw_data:
            story.append(Paragraph("Data Sample (First 10 Rows)", styles['Heading2']))
            
            sample_data = data.head(10)
            data_table_info = []
            data_table_info.append(list(sample_data.columns))
            
            for _, row in sample_data.iterrows():
                data_table_info.append([str(val)[:20] + "..." if len(str(val)) > 20 else str(val) 
                                      for val in row])
            
            data_table = Table(data_table_info)
            data_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(data_table)
        
        # Build PDF
        doc.build(story)
        
        file_size_kb = round(report_path.stat().st_size / 1024, 2)
        
        return {
            'file_path': str(report_path),
            'file_size_kb': file_size_kb
        }
    
    def _generate_html_report(self, data: pd.DataFrame, config: ReportConfig, 
                            report_id: str, charts: List[str] = None) -> Dict[str, Any]:
        """
        Generate HTML report
        إنشاء تقرير HTML
        """
        report_path = self.reports_path / f"{report_id}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{config.title}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #2c3e50; text-align: center; }}
                h2 {{ color: #34495e; border-bottom: 2px solid #3498db; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metadata {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; }}
                .chart {{ text-align: center; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>{config.title}</h1>
            
            <div class="metadata">
                <p><strong>Author:</strong> {config.author}</p>
                <p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Data Rows:</strong> {len(data):,}</p>
                <p><strong>Data Columns:</strong> {len(data.columns)}</p>
            </div>
            
            <h2>Data Overview</h2>
            {data.info(buf=None)}
            
            <h2>Column Information</h2>
            {self._generate_column_info_html(data)}
        """
        
        if config.include_statistics:
            html_content += f"""
            <h2>Statistical Summary</h2>
            {data.describe().to_html(classes='table')}
            """
        
        if config.include_charts and charts:
            html_content += "<h2>Data Visualizations</h2>"
            for chart_path in charts:
                if Path(chart_path).exists() and chart_path.endswith('.html'):
                    with open(chart_path, 'r') as f:
                        chart_html = f.read()
                    html_content += f'<div class="chart">{chart_html}</div>'
        
        if config.include_raw_data:
            html_content += f"""
            <h2>Data Sample (First 10 Rows)</h2>
            {data.head(10).to_html(classes='table')}
            """
        
        html_content += """
        </body>
        </html>
        """
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        file_size_kb = round(report_path.stat().st_size / 1024, 2)
        
        return {
            'file_path': str(report_path),
            'file_size_kb': file_size_kb
        }
    
    def _generate_column_info_html(self, data: pd.DataFrame) -> str:
        """Generate HTML table for column information"""
        html = "<table><tr><th>Column Name</th><th>Data Type</th><th>Non-Null Count</th><th>Unique Values</th></tr>"
        
        for col in data.columns:
            html += f"""
            <tr>
                <td>{col}</td>
                <td>{data[col].dtype}</td>
                <td>{data[col].count()}</td>
                <td>{data[col].nunique()}</td>
            </tr>
            """
        
        html += "</table>"
        return html
    
    def get_chart_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get chart creation history"""
        return self.chart_history[-limit:] if self.chart_history else []
    
    def get_report_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get report generation history"""
        return self.report_history[-limit:] if self.report_history else []
    
    def get_visualization_statistics(self) -> Dict[str, Any]:
        """Get visualization engine statistics"""
        return {
            'total_charts_created': len(self.chart_history),
            'total_reports_generated': len(self.report_history),
            'chart_types_used': list(set(chart['chart_type'] for chart in self.chart_history)),
            'total_storage_mb': sum(chart.get('file_size_kb', 0) for chart in self.chart_history) / 1024,
            'generated_at': datetime.utcnow().isoformat()
        }
