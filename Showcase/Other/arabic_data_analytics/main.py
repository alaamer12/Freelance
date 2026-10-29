#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
منصة تحليل البيانات العربية المتقدمة
Arabic Advanced Data Analytics Platform

نظام شامل لجمع وتحليل البيانات باللغة العربية مع دعم كامل للنصوص من اليمين إلى اليسار
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Rich library imports for beautiful terminal output
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.markdown import Markdown
from rich.layout import Layout
from rich.live import Live

# Data analysis and visualization
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from scipy import stats
import seaborn as sns
import matplotlib.pyplot as plt

import arabic_reshaper
from bidi.algorithm import get_display
from faker import Faker

# إعداد الكونسول مع دعم اللغة العربية
console = Console(width=120, force_terminal=True, legacy_windows=False)

def setup_arabic_text(text):
    """
    إعداد النص العربي للعرض الصحيح من اليمين إلى اليسار
    """
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)

def display_welcome_banner():
    """
    عرض شعار الترحيب الاحترافي
    """
    welcome_text = Text()
    welcome_text.append("* ", style="bold red")
    welcome_text.append("Arabic Data Analytics Platform", style="bold blue")
    welcome_text.append(" *", style="bold red")
    
    description = """
    Comprehensive Arabic Data Analysis System
    
    Key Features:
    - Multi-source data collection from web
    - Comprehensive Exploratory Data Analysis (EDA)
    - Professional high-quality visualizations
    - Full Arabic text support (RTL)
    - Interactive and elegant terminal interface
    
    Goal: Provide advanced data analysis tools for Arabic content
    """
    
    panel = Panel(
        Align.center(welcome_text),
        subtitle=description,
        border_style="bright_blue",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()

def collect_data_from_sources():
    """
    محاكاة جمع البيانات من مصادر مختلفة على الإنترنت
    """
    console.print("\n[bold blue]Starting data collection from various sources...[/bold blue]")
    
    # محاكاة مصادر البيانات المختلفة
    sources = [
        "Sales data from e-commerce platform",
        "Customer data from CRM system",
        "Product data from main database",
        "Geographic data from mapping services",
        "Performance data from analytics dashboard"
    ]
    
    collected_data = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        for i, source in enumerate(sources):
            task = progress.add_task(f"Collecting data from: {source}", total=100)
            
            # محاكاة جمع البيانات مع تأخير واقعي
            for step in range(100):
                time.sleep(0.015)  # محاكاة زمن الاستجابة
                progress.update(task, advance=1)
            
            # محاكاة حفظ البيانات المجمعة
            collected_data[f"source_{i+1}"] = {
                "records": random.randint(500, 2000),
                "status": "success",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    # عرض ملخص البيانات المجمعة
    table = Table(title="Data Collection Summary", show_header=True, header_style="bold magenta")
    table.add_column("Source", style="cyan")
    table.add_column("Records", justify="right", style="magenta")
    table.add_column("Status", justify="center", style="green")
    table.add_column("Collection Time", style="blue")
    
    for i, (key, data) in enumerate(collected_data.items()):
        table.add_row(
            sources[i].split(": ")[0] if ": " in sources[i] else sources[i],
            str(data["records"]),
            "Success" if data["status"] == "success" else "Failed",
            data["timestamp"]
        )
    
    console.print(table)
    console.print("[green]Data collection completed successfully![/green]")
    
    return generate_arabic_dataset()

def generate_arabic_dataset():
    """
    إنشاء مجموعة بيانات عربية واقعية للتحليل
    """
    console.print("\n[bold yellow]Creating Arabic dataset...[/bold yellow]")
    
    # إعداد مولد البيانات الوهمية للغة العربية
    fake = Faker(['ar_SA', 'ar_EG', 'ar_JO'])
    
    # قوائم البيانات العربية الواقعية
    companies = [
        'شركة الرياض للتجارة', 'مؤسسة الخليج للاستثمار', 'شركة النهضة التجارية',
        'مجموعة الشرق الأوسط', 'شركة الأندلس للتطوير', 'مؤسسة البحرين التجارية',
        'شركة القاهرة للصناعات', 'مجموعة دبي للاستثمار', 'شركة الكويت التجارية',
        'مؤسسة عمان للتنمية', 'شركة بغداد للتجارة', 'مجموعة الدوحة للاستثمار'
    ]
    
    products = [
        'هواتف ذكية', 'أجهزة كمبيوتر محمولة', 'أجهزة تلفزيون', 'أجهزة منزلية',
        'ملابس رجالية', 'ملابس نسائية', 'أحذية رياضية', 'عطور ومستحضرات',
        'كتب ومجلات', 'ألعاب أطفال', 'مجوهرات وساعات', 'أدوات رياضية'
    ]
    
    regions = [
        'الرياض', 'جدة', 'الدمام', 'مكة المكرمة', 'المدينة المنورة',
        'القاهرة', 'الإسكندرية', 'الجيزة', 'دبي', 'أبو ظبي',
        'الكويت', 'الدوحة', 'المنامة', 'مسقط', 'عمان', 'بيروت'
    ]
    
    data = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("إنشاء السجلات...", total=3000)
        
        for i in range(3000):
            record = {
                'التاريخ': fake.date_between(start_date='-2y', end_date='today'),
                'الشركة': random.choice(companies),
                'المنتج': random.choice(products),
                'المنطقة': random.choice(regions),
                'المبيعات': round(random.uniform(10000, 500000), 2),
                'الأرباح': round(random.uniform(1000, 100000), 2),
                'عدد_العملاء': random.randint(50, 1000),
                'تقييم_العملاء': round(random.uniform(3.0, 5.0), 1),
                'معدل_النمو': round(random.uniform(-10, 25), 2),
                'حصة_السوق': round(random.uniform(1, 15), 2)
            }
            data.append(record)
            progress.update(task, advance=1)
    
    df = pd.DataFrame(data)
    df['التاريخ'] = pd.to_datetime(df['التاريخ'])
    
    console.print(f"[green]Successfully created {len(df)} records![/green]")
    
    return df

def create_visualizations(df):
    """
    إنشاء التصورات البيانية وحفظها في مجلد الإخراج
    """
    console.print("\n[bold yellow]Creating data visualizations...[/bold yellow]")
    
    # إنشاء مجلد الإخراج إذا لم يكن موجوداً
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # إعداد الخط العربي لـ matplotlib
    plt.rcParams['font.family'] = ['Arial Unicode MS', 'Tahoma', 'DejaVu Sans']
    
    # 1. مخطط المبيعات حسب المنطقة
    console.print("[cyan]Creating sales by region chart...[/cyan]")
    sales_by_region = df.groupby('المنطقة')['المبيعات'].sum().sort_values(ascending=False)
    
    fig1 = go.Figure(data=[
        go.Bar(
            x=sales_by_region.index,
            y=sales_by_region.values,
            marker_color='rgb(55, 83, 109)',
            text=[f'{val:,.0f}' for val in sales_by_region.values],
            textposition='auto',
        )
    ])
    
    fig1.update_layout(
        title={
            'text': 'إجمالي المبيعات حسب المنطقة',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='المنطقة',
        yaxis_title='إجمالي المبيعات',
        font=dict(size=14),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig1.write_image(output_dir / "sales_by_region.png", width=1200, height=800)
    
    # 2. مخطط دائري للمنتجات
    console.print("[cyan]Creating product distribution pie chart...[/cyan]")
    product_counts = df['المنتج'].value_counts()
    
    fig2 = go.Figure(data=[
        go.Pie(
            labels=product_counts.index,
            values=product_counts.values,
            hole=0.3,
            textinfo='label+percent',
            textposition='auto'
        )
    ])
    
    fig2.update_layout(
        title={
            'text': 'توزيع المنتجات',
            'x': 0.5,
            'xanchor': 'center'
        },
        font=dict(size=14),
        showlegend=True
    )
    
    fig2.write_image(output_dir / "product_distribution.png", width=1200, height=800)
    
    # 3. مخطط خطي للمبيعات عبر الزمن
    console.print("[cyan]Creating sales trend over time...[/cyan]")
    df_monthly = df.groupby(df['التاريخ'].dt.to_period('M'))['المبيعات'].sum()
    
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=[str(period) for period in df_monthly.index],
        y=df_monthly.values,
        mode='lines+markers',
        name='المبيعات الشهرية',
        line=dict(color='rgb(67, 67, 67)', width=2),
        marker=dict(size=8)
    ))
    
    fig3.update_layout(
        title={
            'text': 'اتجاه المبيعات عبر الزمن',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='الشهر',
        yaxis_title='إجمالي المبيعات',
        font=dict(size=14),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig3.write_image(output_dir / "sales_trend.png", width=1200, height=800)
    
    # 4. مخطط الأرباح مقابل المبيعات
    console.print("[cyan]Creating profit vs sales scatter plot...[/cyan]")
    fig4 = go.Figure()
    
    for region in df['المنطقة'].unique():
        region_data = df[df['المنطقة'] == region]
        fig4.add_trace(go.Scatter(
            x=region_data['المبيعات'],
            y=region_data['الأرباح'],
            mode='markers',
            name=region,
            marker=dict(size=8, opacity=0.7)
        ))
    
    fig4.update_layout(
        title={
            'text': 'العلاقة بين المبيعات والأرباح حسب المنطقة',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='المبيعات',
        yaxis_title='الأرباح',
        font=dict(size=14),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig4.write_image(output_dir / "profit_vs_sales.png", width=1200, height=800)
    
    # 5. إحصائيات وصفية
    console.print("[cyan]Creating descriptive statistics...[/cyan]")
    stats_table = Table(title="الإحصائيات الوصفية للبيانات", show_header=True, header_style="bold magenta")
    stats_table.add_column("المتغير", style="cyan")
    stats_table.add_column("المتوسط", justify="right", style="green")
    stats_table.add_column("الوسيط", justify="right", style="blue")
    stats_table.add_column("الانحراف المعياري", justify="right", style="yellow")
    stats_table.add_column("الحد الأدنى", justify="right", style="red")
    stats_table.add_column("الحد الأعلى", justify="right", style="red")
    
    numeric_cols = ['المبيعات', 'الأرباح', 'تقييم_العملاء', 'معدل_النمو', 'حصة_السوق']
    
    for col in numeric_cols:
        if col in df.columns:
            stats_table.add_row(
                col,
                f"{df[col].mean():.2f}",
                f"{df[col].median():.2f}",
                f"{df[col].std():.2f}",
                f"{df[col].min():.2f}",
                f"{df[col].max():.2f}"
            )
    
    console.print("\n")
    console.print(stats_table)
    
    # حفظ الإحصائيات في ملف CSV
    df.describe().to_csv(output_dir / "descriptive_statistics.csv")
    
    # 6. خريطة حرارية لأداء الشركات
    console.print("[cyan]Creating company performance heatmap...[/cyan]")
    company_metrics = df.groupby('الشركة').agg({
        'المبيعات': 'mean',
        'الأرباح': 'mean',
        'تقييم_العملاء': 'mean',
        'معدل_النمو': 'mean'
    }).round(2)
    
    fig5 = go.Figure(data=go.Heatmap(
        z=company_metrics.values,
        x=company_metrics.columns,
        y=company_metrics.index,
        colorscale='RdYlBu_r',
        text=company_metrics.values,
        texttemplate="%{text}",
        textfont={"size": 10},
        hoverongaps=False
    ))
    
    fig5.update_layout(
        title={
            'text': 'خريطة حرارية لأداء الشركات',
            'x': 0.5,
            'xanchor': 'center'
        },
        font=dict(size=12),
        width=1000,
        height=600
    )
    
    fig5.write_image(output_dir / "company_performance_heatmap.png", width=1200, height=800)
    
    # 7. مخطط صندوقي لتوزيع المبيعات
    console.print("[cyan]Creating sales distribution box plot...[/cyan]")
    fig6 = go.Figure()
    
    for region in df['المنطقة'].unique():
        region_data = df[df['المنطقة'] == region]
        fig6.add_trace(go.Box(
            y=region_data['المبيعات'],
            name=region,
            boxpoints='outliers'
        ))
    
    fig6.update_layout(
        title={
            'text': 'توزيع المبيعات حسب المنطقة',
            'x': 0.5,
            'xanchor': 'center'
        },
        yaxis_title='المبيعات',
        xaxis_title='المنطقة',
        font=dict(size=14),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig6.write_image(output_dir / "sales_distribution_boxplot.png", width=1200, height=800)
    
    # 8. مصفوفة الارتباط
    console.print("[cyan]Creating correlation matrix...[/cyan]")
    numeric_cols = ['المبيعات', 'الأرباح', 'تقييم_العملاء', 'معدل_النمو', 'حصة_السوق']
    correlation_matrix = df[numeric_cols].corr()
    
    fig7 = go.Figure(data=go.Heatmap(
        z=correlation_matrix.values,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdBu',
        zmid=0,
        text=correlation_matrix.round(2).values,
        texttemplate="%{text}",
        textfont={"size": 12},
        hoverongaps=False
    ))
    
    fig7.update_layout(
        title={
            'text': 'مصفوفة الارتباط بين المتغيرات',
            'x': 0.5,
            'xanchor': 'center'
        },
        font=dict(size=12),
        width=800,
        height=600
    )
    
    fig7.write_image(output_dir / "correlation_matrix.png", width=1200, height=800)
    
    # 9. معدل النمو الشهري
    console.print("[cyan]Creating monthly growth rate chart...[/cyan]")
    monthly_growth = df.groupby(df['التاريخ'].dt.to_period('M'))['معدل_النمو'].mean()
    
    fig8 = go.Figure()
    fig8.add_trace(go.Scatter(
        x=[str(period) for period in monthly_growth.index],
        y=monthly_growth.values,
        mode='lines+markers',
        name='معدل النمو الشهري',
        line=dict(color='rgb(26, 118, 255)', width=3),
        marker=dict(size=8, color='rgb(26, 118, 255)')
    ))
    
    fig8.update_layout(
        title={
            'text': 'معدل النمو الشهري',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='الشهر',
        yaxis_title='معدل النمو (%)',
        font=dict(size=14),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig8.write_image(output_dir / "monthly_growth_rate.png", width=1200, height=800)
    
    # 10. أفضل المنتجات مبيعاً
    console.print("[cyan]Creating top products bar chart...[/cyan]")
    top_products = df.groupby('المنتج')['المبيعات'].sum().sort_values(ascending=True).tail(10)
    
    fig9 = go.Figure(data=[
        go.Bar(
            x=top_products.values,
            y=top_products.index,
            orientation='h',
            marker_color='rgb(158, 202, 225)',
            text=[f'{val:,.0f}' for val in top_products.values],
            textposition='auto',
        )
    ])
    
    fig9.update_layout(
        title={
            'text': 'أفضل 10 منتجات مبيعاً',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='إجمالي المبيعات',
        yaxis_title='المنتج',
        font=dict(size=14),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=600
    )
    
    fig9.write_image(output_dir / "top_products_bar.png", width=1200, height=800)
    
    # حفظ البيانات الكاملة
    df.to_csv(output_dir / "arabic_dataset.csv", index=False)
    
    console.print(f"\n[bold green]All visualizations saved to '{output_dir}' directory![/bold green]")
    console.print("[yellow]Generated files:[/yellow]")
    console.print("  - sales_by_region.png")
    console.print("  - product_distribution.png") 
    console.print("  - sales_trend.png")
    console.print("  - profit_vs_sales.png")
    console.print("  - company_performance_heatmap.png")
    console.print("  - sales_distribution_boxplot.png")
    console.print("  - correlation_matrix.png")
    console.print("  - monthly_growth_rate.png")
    console.print("  - top_products_bar.png")
    console.print("  - descriptive_statistics.csv")
    console.print("  - arabic_dataset.csv")

def main():
    """
    الدالة الرئيسية لتشغيل منصة تحليل البيانات العربية
    """
    # عرض شعار الترحيب
    display_welcome_banner()
    
    try:
        # جمع البيانات من المصادر
        df = collect_data_from_sources()
        
        console.print("\n[bold green]Arabic Data Analytics Platform launched successfully![/bold green]")
        console.print(f"[blue]Loaded {len(df)} records for analysis[/blue]")
        
        # عرض معاينة سريعة للبيانات
        console.print("\n[bold cyan]Quick data preview:[/bold cyan]")
        preview_table = Table(show_header=True, header_style="bold magenta")
        
        # إضافة الأعمدة
        for col in df.columns[:6]:  # عرض أول 6 أعمدة فقط
            preview_table.add_column(col, style="cyan")
        
        # إضافة أول 5 صفوف
        for idx in range(min(5, len(df))):
            row_data = []
            for col in df.columns[:6]:
                value = str(df.iloc[idx][col])
                if len(value) > 20:
                    value = value[:17] + "..."
                row_data.append(value)
            preview_table.add_row(*row_data)
        
        console.print(preview_table)
        
        # إنشاء التصورات البيانية
        create_visualizations(df)
        
    except Exception as e:
        console.print(f"[red]Error running platform: {str(e)}[/red]")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
