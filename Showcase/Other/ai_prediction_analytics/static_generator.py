#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
منصة التنبؤ بالنتائج وتحليل البيانات باستخدام الذكاء الاصطناعي - مولد الصور الثابتة
AI Prediction and Data Analysis Platform - Static Image Generator
تم التطوير بواسطة: عمرو محمد
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import seaborn as sns
import matplotlib.pyplot as plt
from faker import Faker
import warnings
import os
from plotly.subplots import make_subplots
warnings.filterwarnings('ignore')

# إنشاء مجلد للصور
output_dir = "static_plots"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def generate_business_data():
    """إنشاء بيانات تجارية واقعية باللغة العربية"""
    fake = Faker('ar_SA')
    
    companies = [
        "شركة الرياض للتجارة", "مؤسسة جدة التقنية", "شركة الدمام للصناعات",
        "مجموعة المدينة التجارية", "شركة مكة للاستثمار", "مؤسسة الخبر للتطوير",
        "شركة الطائف للخدمات", "مجموعة أبها التقنية", "شركة تبوك للتجارة",
        "مؤسسة الجوف للاستثمار", "شركة حائل للصناعات", "مجموعة القصيم التجارية"
    ]
    
    products = [
        "أجهزة إلكترونية", "منتجات غذائية", "مواد بناء", "أدوات منزلية",
        "ملابس وأزياء", "معدات طبية", "قطع غيار", "مستحضرات تجميل",
        "أثاث مكتبي", "أدوات رياضية", "كتب ومجلات", "ألعاب أطفال"
    ]
    
    regions = ["الرياض", "جدة", "الدمام", "مكة المكرمة", "المدينة المنورة", "الطائف", "أبها", "تبوك"]
    
    data = []
    for i in range(2000):
        date = fake.date_between(start_date='-2y', end_date='today')
        company = random.choice(companies)
        product = random.choice(products)
        region = random.choice(regions)
        
        base_sales = random.uniform(50000, 500000)
        seasonal_factor = 1 + 0.3 * np.sin(2 * np.pi * date.month / 12)
        sales = base_sales * seasonal_factor * random.uniform(0.8, 1.2)
        
        profit_margin = random.uniform(0.15, 0.35)
        profit = sales * profit_margin
        
        data.append({
            'التاريخ': date,
            'الشركة': company,
            'المنتج': product,
            'المنطقة': region,
            'المبيعات': round(sales, 2),
            'الأرباح': round(profit, 2),
            'هامش_الربح': round(profit_margin * 100, 2),
            'عدد_العملاء': random.randint(100, 1000),
            'تقييم_العملاء': round(random.uniform(3.5, 5.0), 1),
            'مؤشر_النمو': round(random.uniform(-10, 25), 2),
            'قناة_البيع': random.choice(['متجر إلكتروني', 'متجر تقليدي', 'موزع', 'مبيعات مباشرة'])
        })
    
    df = pd.DataFrame(data)
    # تحويل عمود التاريخ إلى datetime
    df['التاريخ'] = pd.to_datetime(df['التاريخ'])
    return df
    

def create_visualization_1(df):
    """الرسم البياني 1: الاتجاهات المالية متعددة الأبعاد"""
    monthly_data = df.groupby([df['التاريخ'].dt.to_period('M'), 'المنطقة']).agg({
        'المبيعات': 'sum',
        'الأرباح': 'sum',
        'عدد_العملاء': 'sum'
    }).reset_index()
    monthly_data['التاريخ'] = monthly_data['التاريخ'].dt.to_timestamp()
    
    fig1 = go.Figure()
    
    regions = monthly_data['المنطقة'].unique()
    colors = px.colors.qualitative.Set3
    
    for i, region in enumerate(regions):
        region_data = monthly_data[monthly_data['المنطقة'] == region]
        fig1.add_trace(go.Scatter(
            x=region_data['التاريخ'],
            y=region_data['المبيعات'],
            mode='lines+markers',
            name=f'مبيعات {region}',
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(size=8)
        ))
    
    fig1.update_layout(
        title=dict(
            text="📈 الاتجاهات المالية متعددة الأبعاد حسب المنطقة",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        xaxis_title="الفترة الزمنية",
        yaxis_title="المبيعات (ريال سعودي)",
        font=dict(size=16, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        xaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8', 
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False,
            tickfont=dict(size=14)
        )
    )
    
    fig1.write_image(f"{output_dir}/01_financial_trends.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 1: الاتجاهات المالية")

def create_visualization_2(df):
    """الرسم البياني 2: مصفوفة الأداء الاستراتيجي"""
    product_performance = df.groupby('المنتج').agg({
        'المبيعات': 'sum',
        'هامش_الربح': 'mean',
        'تقييم_العملاء': 'mean',
        'عدد_العملاء': 'sum'
    }).reset_index()
    
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=product_performance['المبيعات'],
        y=product_performance['هامش_الربح'],
        mode='markers+text',
        text=product_performance['المنتج'],
        textposition="middle center",
        marker=dict(
            size=product_performance['عدد_العملاء']/50,
            color=product_performance['تقييم_العملاء'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="تقييم العملاء"),
            line=dict(width=2, color='white')
        ),
        name="المنتجات"
    ))
    
    fig2.update_layout(
        title=dict(
            text="🎯 مصفوفة الأداء الاستراتيجي للمنتجات",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        xaxis_title="إجمالي المبيعات (ريال سعودي)",
        yaxis_title="هامش الربح (%)",
        font=dict(size=16, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        xaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False,
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=14)
        )
    )
    
    fig2.write_image(f"{output_dir}/02_performance_matrix.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 2: مصفوفة الأداء")

def create_visualization_3(df):
    """الرسم البياني 3: التوزيع الجغرافي المتقدم"""
    regional_analysis = df.groupby('المنطقة').agg({
        'المبيعات': 'sum',
        'الأرباح': 'sum',
        'تقييم_العملاء': 'mean',
        'عدد_العملاء': 'sum'
    }).reset_index()
    
    fig3 = go.Figure()
    
    fig3.add_trace(go.Bar(
        x=regional_analysis['المنطقة'],
        y=regional_analysis['المبيعات'],
        name='المبيعات',
        marker_color='#3498db',
        yaxis='y',
        offsetgroup=1
    ))
    
    fig3.add_trace(go.Scatter(
        x=regional_analysis['المنطقة'],
        y=regional_analysis['تقييم_العملاء'],
        mode='lines+markers',
        name='تقييم العملاء',
        yaxis='y2',
        line=dict(color='#e74c3c', width=4),
        marker=dict(size=10)
    ))
    
    fig3.update_layout(
        title=dict(
            text="🗺️ التحليل الجغرافي المتقدم للأداء",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        xaxis_title="المنطقة",
        font=dict(size=16, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        yaxis=dict(
            title="المبيعات (ريال سعودي)", 
            side="left", 
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=14)
        ),
        yaxis2=dict(
            title="تقييم العملاء", 
            side="right", 
            overlaying="y", 
            range=[3, 5],
            tickfont=dict(size=14)
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=14)
        )
    )
    
    fig3.write_image(f"{output_dir}/03_geographic_analysis.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 3: التحليل الجغرافي")

def create_visualization_4(df):
    """الرسم البياني 4: تحليل السلاسل الزمنية والتنبؤات"""
    df_sorted = df.sort_values('التاريخ')
    monthly_sales = df_sorted.groupby(df_sorted['التاريخ'].dt.to_period('M'))['المبيعات'].sum().reset_index()
    monthly_sales['التاريخ'] = monthly_sales['التاريخ'].dt.to_timestamp()
    
    # حساب المتوسط المتحرك
    monthly_sales['متوسط_متحرك_3'] = monthly_sales['المبيعات'].rolling(window=3).mean()
    monthly_sales['متوسط_متحرك_6'] = monthly_sales['المبيعات'].rolling(window=6).mean()
    
    # إنشاء تنبؤات مستقبلية بسيطة
    last_date = monthly_sales['التاريخ'].max()
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1), periods=6, freq='M')
    trend = np.polyfit(range(len(monthly_sales)), monthly_sales['المبيعات'], 1)
    future_values = [trend[0] * (len(monthly_sales) + i) + trend[1] for i in range(1, 7)]
    
    fig4 = go.Figure()
    
    fig4.add_trace(go.Scatter(
        x=monthly_sales['التاريخ'],
        y=monthly_sales['المبيعات'],
        mode='lines+markers',
        name='المبيعات الفعلية',
        line=dict(color='#2c3e50', width=3),
        marker=dict(size=8)
    ))
    
    fig4.add_trace(go.Scatter(
        x=monthly_sales['التاريخ'],
        y=monthly_sales['متوسط_متحرك_3'],
        mode='lines',
        name='المتوسط المتحرك (3 أشهر)',
        line=dict(color='#3498db', width=2, dash='dash')
    ))
    
    fig4.add_trace(go.Scatter(
        x=monthly_sales['التاريخ'],
        y=monthly_sales['متوسط_متحرك_6'],
        mode='lines',
        name='المتوسط المتحرك (6 أشهر)',
        line=dict(color='#e74c3c', width=2, dash='dot')
    ))
    
    fig4.add_trace(go.Scatter(
        x=future_dates,
        y=future_values,
        mode='lines+markers',
        name='التنبؤات المستقبلية',
        line=dict(color='#f39c12', width=3, dash='dashdot'),
        marker=dict(size=10, symbol='diamond')
    ))
    
    fig4.update_layout(
        title=dict(
            text="📊 تحليل السلاسل الزمنية والتنبؤات الذكية",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        xaxis_title="الفترة الزمنية",
        yaxis_title="المبيعات (ريال سعودي)",
        font=dict(size=16, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        xaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8', 
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False,
            tickfont=dict(size=14)
        ),
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=1.02, 
            xanchor="center", 
            x=0.5,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1
        ),
        showlegend=True
    )
    
    fig4.write_image(f"{output_dir}/04_time_series_forecasting.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 4: السلاسل الزمنية والتنبؤات")

def create_visualization_5(df):
    """الرسم البياني 5: تحليل الانحدار والارتباط"""
    fig5 = go.Figure()
    
    fig5.add_trace(go.Scatter(
        x=df['المبيعات'],
        y=df['الأرباح'],
        mode='markers',
        marker=dict(
            size=8,
            color=df['تقييم_العملاء'],
            colorscale='Plasma',
            showscale=True,
            colorbar=dict(title="تقييم العملاء"),
            opacity=0.7
        ),
        name='البيانات الفعلية'
    ))
    
    # خط الاتجاه
    z = np.polyfit(df['المبيعات'], df['الأرباح'], 1)
    p = np.poly1d(z)
    fig5.add_trace(go.Scatter(
        x=df['المبيعات'],
        y=p(df['المبيعات']),
        mode='lines',
        name=f'خط الاتجاه (R² = {np.corrcoef(df["المبيعات"], df["الأرباح"])[0,1]**2:.3f})',
        line=dict(color='red', width=3)
    ))
    
    fig5.update_layout(
        title=dict(
            text="🔍 تحليل الانحدار والارتباط بين المبيعات والأرباح",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        xaxis_title="المبيعات (ريال سعودي)",
        yaxis_title="الأرباح (ريال سعودي)",
        font=dict(size=16, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        xaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False,
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False,
            tickfont=dict(size=14)
        )
    )
    
    fig5.write_image(f"{output_dir}/05_regression_analysis.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 5: تحليل الانحدار")

def create_visualization_6(df):
    """الرسم البياني 6: تحليل التوزيع الإحصائي"""
    fig6 = go.Figure()
    
    fig6.add_trace(go.Histogram(
        x=df['المبيعات'],
        nbinsx=30,
        name='توزيع المبيعات',
        marker_color='skyblue',
        opacity=0.7,
        yaxis='y'
    ))
    
    # منحنى الكثافة
    from scipy import stats
    density = stats.gaussian_kde(df['المبيعات'])
    xs = np.linspace(df['المبيعات'].min(), df['المبيعات'].max(), 200)
    density_values = density(xs) * len(df) * (df['المبيعات'].max() - df['المبيعات'].min()) / 30
    
    fig6.add_trace(go.Scatter(
        x=xs,
        y=density_values,
        mode='lines',
        name='منحنى الكثافة (KDE)',
        line=dict(color='red', width=3),
        yaxis='y'
    ))
    
    fig6.update_layout(
        title=dict(
            text="📈 تحليل التوزيع الإحصائي للمبيعات",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        xaxis_title="المبيعات (ريال سعودي)",
        yaxis_title="التكرار",
        font=dict(size=16, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        xaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False,
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False,
            tickfont=dict(size=14)
        ),
        showlegend=True
    )
    
    fig6.write_image(f"{output_dir}/06_statistical_distribution.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 6: التوزيع الإحصائي")

def create_visualization_7(df):
    """الرسم البياني 7: تحليل الأداء المقارن متعدد المؤشرات"""
    channel_performance = df.groupby('قناة_البيع').agg({
        'المبيعات': 'mean',
        'الأرباح': 'mean',
        'تقييم_العملاء': 'mean',
        'هامش_الربح': 'mean',
        'مؤشر_النمو': 'mean'
    }).reset_index()
    
    # تطبيع البيانات للمقارنة
    metrics = ['المبيعات', 'الأرباح', 'تقييم_العملاء', 'هامش_الربح', 'مؤشر_النمو']
    for metric in metrics:
        max_val = channel_performance[metric].max()
        min_val = channel_performance[metric].min()
        channel_performance[f'{metric}_normalized'] = (channel_performance[metric] - min_val) / (max_val - min_val)
    
    fig7 = go.Figure()
    
    channels = channel_performance['قناة_البيع'].unique()
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    for i, channel in enumerate(channels):
        channel_data = channel_performance[channel_performance['قناة_البيع'] == channel]
        values = [channel_data[f'{metric}_normalized'].iloc[0] for metric in metrics]
        values.append(values[0])  # إغلاق الشكل
        
        fig7.add_trace(go.Scatterpolar(
            r=values,
            theta=metrics + [metrics[0]],
            fill='toself',
            name=channel,
            line_color=colors[i % len(colors)],
            fillcolor=colors[i % len(colors)],
            opacity=0.6
        ))
    
    fig7.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(size=12)
            ),
            angularaxis=dict(
                tickfont=dict(size=14)
            )
        ),
        title=dict(
            text="🎯 تحليل الأداء المقارن متعدد المؤشرات",
            font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
            x=0.5,
            y=0.95
        ),
        font=dict(size=16, family="Cairo, Arial"),
        height=650,
        margin=dict(l=80, r=80, t=100, b=80),
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation="h", 
            yanchor="bottom", 
            y=-0.1, 
            xanchor="center", 
            x=0.5,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#e0e0e0',
            borderwidth=1
        )
    )
    
    fig7.write_image(f"{output_dir}/07_radar_performance.png", width=1200, height=600, scale=2)
    print("✅ تم إنشاء الرسم البياني 7: الأداء المقارن")

def create_visualization_8(df):
    """الرسم البياني 8: لوحة المعلومات التنفيذية الشاملة"""
    fig8 = make_subplots(
        rows=2, cols=2,
        subplot_titles=('الأرباح الشهرية', 'توزيع أنواع العملاء', 'مؤشرات الأداء', 'الموسمية'),
        specs=[[{"secondary_y": False}, {"type": "pie"}],
               [{"type": "bar"}, {"secondary_y": False}]]
    )
    
    # الرسم الفرعي 1: الأرباح الشهرية
    monthly_profit = df.groupby(df['التاريخ'].dt.to_period('M'))['الأرباح'].sum().reset_index()
    monthly_profit['التاريخ'] = monthly_profit['التاريخ'].dt.to_timestamp()
    
    fig8.add_trace(
        go.Scatter(x=monthly_profit['التاريخ'], y=monthly_profit['الأرباح'],
                  mode='lines+markers', name='الأرباح الشهرية',
                  line=dict(color='#2ecc71', width=3)),
        row=1, col=1
    )
    
    # الرسم الفرعي 2: توزيع قنوات البيع
    channel_dist = df['قناة_البيع'].value_counts()
    fig8.add_trace(
        go.Pie(labels=channel_dist.index, values=channel_dist.values,
               name="قنوات البيع", hole=0.4),
        row=1, col=2
    )
    
    # الرسم الفرعي 3: مؤشرات الأداء حسب المنطقة
    region_performance = df.groupby('المنطقة')['مؤشر_النمو'].mean().sort_values(ascending=True)
    fig8.add_trace(
        go.Bar(x=region_performance.values, y=region_performance.index,
               orientation='h', name='مؤشر النمو',
               marker_color='#3498db'),
        row=2, col=1
    )
    
    # الرسم الفرعي 4: الموسمية
    seasonal = df.groupby(df['التاريخ'].dt.month)['المبيعات'].mean()
    months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
              'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
    
    fig8.add_trace(
        go.Scatter(x=months, y=seasonal.values,
                  mode='lines+markers', name='المبيعات الموسمية',
                  line=dict(color='#e74c3c', width=3),
                  marker=dict(size=8)),
        row=2, col=2
    )
    
    fig8.update_layout(
        title_text="📊 لوحة المعلومات التنفيذية الشاملة",
        title_font=dict(size=28, family="Cairo, Arial", color='#2c3e50'),
        title_x=0.5,
        title_y=0.98,
        height=850,
        showlegend=False,
        font=dict(size=14, family="Cairo, Arial"),
        paper_bgcolor='white',
        plot_bgcolor='#fafafa',
        margin=dict(l=80, r=80, t=120, b=80)
    )
    
    fig8.write_image(f"{output_dir}/08_executive_dashboard.png", width=1400, height=850, scale=2)
    print("✅ تم إنشاء الرسم البياني 8: لوحة المعلومات التنفيذية")

def generate_all_plots():
    """إنشاء جميع الرسوم البيانية وحفظها كصور ثابتة"""
    print("🚀 بدء إنشاء الرسوم البيانية الثابتة...")
    print("=" * 50)
    
    # إنشاء البيانات
    print("📊 إنشاء البيانات التجارية...")
    df = generate_business_data()
    
    # إنشاء جميع الرسوم البيانية
    create_visualization_1(df)
    create_visualization_2(df)
    create_visualization_3(df)
    create_visualization_4(df)
    create_visualization_5(df)
    create_visualization_6(df)
    create_visualization_7(df)
    create_visualization_8(df)
    
    # حفظ البيانات كملف CSV
    df.to_csv(f"{output_dir}/business_data.csv", index=False, encoding='utf-8-sig')
    print("💾 تم حفظ البيانات في ملف CSV")
    
    print("=" * 50)
    print("✅ تم إنشاء جميع الرسوم البيانية بنجاح!")
    print(f"📁 الملفات محفوظة في مجلد: {output_dir}")
    print("\n📋 قائمة الملفات المُنشأة:")
    print("1. 01_financial_trends.png - الاتجاهات المالية")
    print("2. 02_performance_matrix.png - مصفوفة الأداء")
    print("3. 03_geographic_analysis.png - التحليل الجغرافي")
    print("4. 04_time_series_forecasting.png - السلاسل الزمنية والتنبؤات")
    print("5. 05_regression_analysis.png - تحليل الانحدار")
    print("6. 06_statistical_distribution.png - التوزيع الإحصائي")
    print("7. 07_radar_performance.png - الأداء المقارن")
    print("8. 08_executive_dashboard.png - لوحة المعلومات التنفيذية")
    print("9. business_data.csv - البيانات التجارية")

if __name__ == "__main__":
    generate_all_plots()
