#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
منصة التنبؤ بالنتائج وتحليل البيانات باستخدام الذكاء الاصطناعي
AI Prediction and Data Analysis Platform
تم التطوير بواسطة: عمرو محمد
"""

import streamlit as st
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
warnings.filterwarnings('ignore')

# إعداد الصفحة
st.set_page_config(
    page_title="منصة التنبؤ والتحليل الذكي",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS للتصميم العربي المسطح المحسن
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;700;900&display=swap');
    
    .main {
        background-color: #fafafa;
    }
    
    .main-header {
        background: linear-gradient(135deg, #2c3e50, #34495e);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        font-family: 'Cairo', sans-serif;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #3498db;
        margin-bottom: 1.5rem;
        font-family: 'Cairo', sans-serif;
    }
    
    .prediction-badge {
        background: linear-gradient(135deg, #27ae60, #2ecc71);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 25px;
        font-size: 1rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem;
        box-shadow: 0 3px 10px rgba(39, 174, 96, 0.3);
        font-family: 'Cairo', sans-serif;
    }
    
    .stMetric {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border: 1px solid #e8e8e8;
        font-family: 'Cairo', sans-serif;
    }
    
    .stMetric > div {
        font-family: 'Cairo', sans-serif;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #2c3e50, #34495e);
        font-family: 'Cairo', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Cairo', sans-serif;
        color: #2c3e50;
        font-weight: 700;
    }
    
    .stSelectbox, .stSlider, .stButton, .stTextInput {
        font-family: 'Cairo', sans-serif;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #3498db, #2980b9);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-family: 'Cairo', sans-serif;
        font-weight: 600;
        box-shadow: 0 3px 10px rgba(52, 152, 219, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(52, 152, 219, 0.4);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-family: 'Cairo', sans-serif;
        font-weight: 600;
        border: 2px solid #e8e8e8;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #3498db;
        color: white;
        border-color: #3498db;
    }
    
    .plot-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 2rem;
        border: 1px solid #e8e8e8;
    }
</style>
""", unsafe_allow_html=True)

# إنشاء بيانات وهمية واقعية
@st.cache_data
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
        "الهواتف الذكية", "أجهزة الكمبيوتر", "الأجهزة اللوحية", "السماعات اللاسلكية",
        "الساعات الذكية", "كاميرات التصوير", "أجهزة التلفزيون", "مكيفات الهواء",
        "الثلاجات المنزلية", "الغسالات الأوتوماتيكية", "أفران الميكروويف", "المكانس الكهربائية"
    ]
    
    regions = [
        "الرياض", "جدة", "الدمام", "مكة المكرمة", "المدينة المنورة",
        "الطائف", "أبها", "تبوك", "الجوف", "حائل", "القصيم", "الباحة"
    ]
    
    data = []
    base_date = datetime.now() - timedelta(days=730)
    
    for i in range(2000):
        date = base_date + timedelta(days=random.randint(0, 730))
        sales = random.randint(10000, 100000)
        cost = sales * random.uniform(0.4, 0.7)
        
        data.append({
            'التاريخ': date,
            'الشركة': random.choice(companies),
            'المنتج': random.choice(products),
            'المنطقة': random.choice(regions),
            'المبيعات': sales,
            'التكلفة': cost,
            'الربح': sales - cost,
            'الكمية': random.randint(50, 1000),
            'معدل_النمو': round(random.uniform(-20, 30), 2),
            'رضا_العملاء': round(random.uniform(3.0, 5.0), 1),
            'التقييم_السوقي': random.choice(['ممتاز', 'جيد جداً', 'جيد', 'مقبول']),
            'الموسم': random.choice(['ربيع', 'صيف', 'خريف', 'شتاء']),
            'نوع_العميل': random.choice(['فردي', 'مؤسسي', 'حكومي']),
            'قناة_البيع': random.choice(['متجر إلكتروني', 'متجر فعلي', 'مندوب مبيعات'])
        })
    
    return pd.DataFrame(data)

# نموذج التنبؤ بالذكاء الاصطناعي
@st.cache_data
def create_prediction_model(df):
    """إنشاء نموذج التنبؤ باستخدام Random Forest"""
    # تحضير البيانات
    df_model = df.copy()
    df_model['الشهر'] = df_model['التاريخ'].dt.month
    df_model['السنة'] = df_model['التاريخ'].dt.year
    df_model['اليوم_في_السنة'] = df_model['التاريخ'].dt.dayofyear
    
    # ترميز المتغيرات الفئوية
    categorical_cols = ['المنطقة', 'المنتج', 'التقييم_السوقي', 'الموسم', 'نوع_العميل', 'قناة_البيع']
    for col in categorical_cols:
        df_model[col + '_encoded'] = pd.Categorical(df_model[col]).codes
    
    # اختيار المتغيرات
    features = ['الشهر', 'السنة', 'اليوم_في_السنة', 'التكلفة', 'الكمية', 'رضا_العملاء'] + \
               [col + '_encoded' for col in categorical_cols]
    
    X = df_model[features]
    y = df_model['المبيعات']
    
    # تقسيم البيانات
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # تدريب النموذج
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # تقييم النموذج
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    return model, mae, r2, features

# الواجهة الرئيسية
def main():
    # العنوان الرئيسي
    st.markdown("""
    <div class="main-header">
        <h1>🧠 منصة التنبؤ بالنتائج وتحليل البيانات</h1>
        <h3>تحليل متقدم وتنبؤات دقيقة باستخدام الذكاء الاصطناعي</h3>
        <p>تم التطوير بواسطة: عمرو محمد | نسخة 2.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    # الشريط الجانبي
    st.sidebar.title("🎛️ لوحة التحكم")
    st.sidebar.markdown("---")
    
    # إنشاء البيانات
    df = generate_business_data()
    
    # خيارات التصفية
    st.sidebar.subheader("🔍 تصفية البيانات")
    
    selected_regions = st.sidebar.multiselect(
        "اختر المناطق:",
        options=df['المنطقة'].unique(),
        default=df['المنطقة'].unique()[:3]
    )
    
    selected_products = st.sidebar.multiselect(
        "اختر المنتجات:",
        options=df['المنتج'].unique(),
        default=df['المنتج'].unique()[:3]
    )
    
    date_range = st.sidebar.date_input(
        "نطاق التاريخ:",
        value=[df['التاريخ'].min().date(), df['التاريخ'].max().date()],
        min_value=df['التاريخ'].min().date(),
        max_value=df['التاريخ'].max().date()
    )
    
    # تطبيق التصفية
    if selected_regions and selected_products:
        filtered_df = df[
            (df['المنطقة'].isin(selected_regions)) &
            (df['المنتج'].isin(selected_products)) &
            (df['التاريخ'].dt.date >= date_range[0]) &
            (df['التاريخ'].dt.date <= date_range[1])
        ]
    else:
        filtered_df = df
    
    # المؤشرات الرئيسية
    st.subheader("📊 المؤشرات الرئيسية")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = filtered_df['المبيعات'].sum()
        st.metric(
            label="إجمالي المبيعات",
            value=f"{total_sales:,.0f} ريال",
            delta=f"+{random.randint(5, 15)}% من الشهر الماضي"
        )
    
    with col2:
        total_profit = filtered_df['الربح'].sum()
        st.metric(
            label="صافي الأرباح",
            value=f"{total_profit:,.0f} ريال",
            delta=f"+{random.randint(8, 20)}% من الشهر الماضي"
        )
    
    with col3:
        avg_satisfaction = filtered_df['رضا_العملاء'].mean()
        st.metric(
            label="متوسط رضا العملاء",
            value=f"{avg_satisfaction:.1f}/5.0",
            delta=f"+{random.uniform(0.1, 0.5):.1f} من الشهر الماضي"
        )
    
    with col4:
        growth_rate = filtered_df['معدل_النمو'].mean()
        st.metric(
            label="معدل النمو",
            value=f"{growth_rate:.1f}%",
            delta=f"+{random.uniform(1, 5):.1f}% من الشهر الماضي"
        )
    
    # نموذج التنبؤ
    st.subheader("🤖 نموذج التنبؤ بالذكاء الاصطناعي")
    
    with st.expander("عرض تفاصيل النموذج", expanded=True):
        model, mae, r2, features = create_prediction_model(filtered_df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("دقة النموذج (R²)", f"{r2:.3f}")
        with col2:
            st.metric("متوسط الخطأ المطلق", f"{mae:,.0f}")
        with col3:
            accuracy_percent = r2 * 100
            st.metric("نسبة الدقة", f"{accuracy_percent:.1f}%")
        
        st.markdown(f"""
        <div class="prediction-badge">
            نوع النموذج: Random Forest Regressor
        </div>
        <div class="prediction-badge">
            عدد الأشجار: 100
        </div>
        <div class="prediction-badge">
            عدد المتغيرات: {len(features)}
        </div>
        """, unsafe_allow_html=True)
    
    # التصورات البيانية الاحترافية المتقدمة
    st.subheader("📊 التحليلات البيانية المتقدمة - مستوى المؤسسات")
    
    # الرسم البياني 1: تحليل الأداء المالي متعدد الأبعاد
    st.subheader("1️⃣ تحليل الأداء المالي الشامل")
    
    # إعداد البيانات للتحليل المتقدم
    monthly_data = filtered_df.groupby([filtered_df['التاريخ'].dt.to_period('M'), 'المنطقة']).agg({
        'المبيعات': 'sum',
        'الربح': 'sum',
        'التكلفة': 'sum',
        'رضا_العملاء': 'mean'
    }).reset_index()
    monthly_data['الشهر'] = monthly_data['التاريخ'].astype(str)
    monthly_data['هامش_الربح'] = (monthly_data['الربح'] / monthly_data['المبيعات'] * 100).round(2)
    
    fig1 = go.Figure()
    
    # إضافة خطوط المبيعات لكل منطقة
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
    for i, region in enumerate(monthly_data['المنطقة'].unique()[:5]):
        region_data = monthly_data[monthly_data['المنطقة'] == region]
        fig1.add_trace(go.Scatter(
            x=region_data['الشهر'],
            y=region_data['المبيعات'],
            mode='lines+markers',
            name=f'{region}',
            line=dict(color=colors[i % len(colors)], width=3),
            marker=dict(size=8),
            hovertemplate='<b>%{fullData.name}</b><br>الشهر: %{x}<br>المبيعات: %{y:,.0f} ريال<extra></extra>'
        ))
    
    fig1.update_layout(
        title=dict(
            text='📈 تحليل اتجاهات المبيعات حسب المناطق الجغرافية',
            x=0.5,
            y=0.95,
            font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
        ),
        xaxis_title="الشهر",
        yaxis_title="المبيعات (ريال سعودي)",
        font=dict(size=14, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=550,
        margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(
            showgrid=True,
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e8e8e8',
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False
        ),
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # الرسم البياني 2: مصفوفة الأداء الاستراتيجي
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("2️⃣ مصفوفة الأداء الاستراتيجي")
        
        # تحليل المنتجات حسب المبيعات والربحية
        product_analysis = filtered_df.groupby('المنتج').agg({
            'المبيعات': 'sum',
            'الربح': 'sum',
            'الكمية': 'sum',
            'رضا_العملاء': 'mean'
        }).reset_index()
        product_analysis['هامش_الربح'] = (product_analysis['الربح'] / product_analysis['المبيعات'] * 100)
        
        fig2 = go.Figure()
        
        fig2.add_trace(go.Scatter(
            x=product_analysis['المبيعات'],
            y=product_analysis['هامش_الربح'],
            mode='markers+text',
            marker=dict(
                size=product_analysis['الكمية']/50,
                color=product_analysis['رضا_العملاء'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="رضا العملاء"),
                line=dict(width=2, color='white')
            ),
            text=product_analysis['المنتج'].str[:15],
            textposition="middle center",
            textfont=dict(size=10, color='white'),
            hovertemplate='<b>%{text}</b><br>المبيعات: %{x:,.0f}<br>هامش الربح: %{y:.1f}%<br>رضا العملاء: %{marker.color:.1f}<extra></extra>'
        ))
        
        fig2.update_layout(
            title=dict(
                text='🎯 مصفوفة المنتجات: المبيعات vs هامش الربح',
                x=0.5,
                y=0.95,
                font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
            ),
            xaxis_title="إجمالي المبيعات (ريال)",
            yaxis_title="هامش الربح (%)",
            font=dict(size=14, family="Cairo, Arial"),
            plot_bgcolor='#fafafa',
            paper_bgcolor='white',
            height=550,
            margin=dict(l=60, r=60, t=80, b=60),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                tickformat=',.0f',
                zeroline=False
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                zeroline=False
            )
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    with col2:
        st.subheader("3️⃣ تحليل التوزيع الجغرافي المتقدم")
        
        # خريطة حرارية للمناطق
        regional_performance = filtered_df.groupby('المنطقة').agg({
            'المبيعات': 'sum',
            'الربح': 'sum',
            'رضا_العملاء': 'mean',
            'معدل_النمو': 'mean'
        }).reset_index()
        
        fig3 = go.Figure(data=go.Bar(
            x=regional_performance['المنطقة'],
            y=regional_performance['المبيعات'],
            marker=dict(
                color=regional_performance['رضا_العملاء'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="رضا العملاء", x=1.1)
            ),
            text=regional_performance['المبيعات'].apply(lambda x: f'{x/1000:.0f}K'),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>المبيعات: %{y:,.0f}<br>الربح: %{customdata[0]:,.0f}<br>رضا العملاء: %{marker.color:.1f}<extra></extra>',
            customdata=regional_performance[['الربح']]
        ))
        
        fig3.update_layout(
            title=dict(
                text='🗺️ الأداء الإقليمي الشامل',
                x=0.5,
                y=0.95,
                font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
            ),
            xaxis_title="المنطقة",
            yaxis_title="المبيعات (ريال)",
            font=dict(size=14, family="Cairo, Arial"),
            plot_bgcolor='#fafafa',
            paper_bgcolor='white',
            height=550,
            margin=dict(l=60, r=60, t=80, b=60),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                zeroline=False,
                tickangle=45
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                tickformat=',.0f',
                zeroline=False
            ),
            yaxis2=dict(
                title="رضا العملاء",
                overlaying="y",
                side="right",
                range=[3, 5]
            )
        )
        
        st.plotly_chart(fig3, use_container_width=True)
    
    # الرسم البياني 4: تحليل السلاسل الزمنية المتقدم
    st.subheader("4️⃣ تحليل السلاسل الزمنية والتنبؤات الذكية")
    
    # إعداد بيانات السلاسل الزمنية
    daily_data = filtered_df.groupby(filtered_df['التاريخ'].dt.date).agg({
        'المبيعات': 'sum',
        'الربح': 'sum',
        'الكمية': 'sum'
    }).reset_index()
    daily_data['المتوسط_المتحرك_7'] = daily_data['المبيعات'].rolling(window=7).mean()
    daily_data['المتوسط_المتحرك_30'] = daily_data['المبيعات'].rolling(window=30).mean()
    
    # إنشاء التنبؤات المتقدمة
    from sklearn.linear_model import LinearRegression
    X = np.arange(len(daily_data)).reshape(-1, 1)
    y = daily_data['المبيعات'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # توليد التنبؤات المستقبلية
    future_days = 30
    future_X = np.arange(len(daily_data), len(daily_data) + future_days).reshape(-1, 1)
    future_predictions = model.predict(future_X)
    future_dates = pd.date_range(start=daily_data['التاريخ'].max() + timedelta(days=1), periods=future_days)
    
    fig4 = go.Figure()
    
    # البيانات الفعلية
    fig4.add_trace(go.Scatter(
        x=daily_data['التاريخ'],
        y=daily_data['المبيعات'],
        mode='lines',
        name='المبيعات الفعلية',
        line=dict(color='#2c3e50', width=1)
    ))
    
    # المتوسط المتحرك 7 أيام
    fig4.add_trace(go.Scatter(
        x=daily_data['التاريخ'],
        y=daily_data['المتوسط_المتحرك_7'],
        mode='lines',
        name='المتوسط المتحرك (7 أيام)',
        line=dict(color='#f39c12', width=3)
    ))
    
    # المتوسط المتحرك 30 يوم
    fig4.add_trace(go.Scatter(
        x=daily_data['التاريخ'],
        y=daily_data['المتوسط_المتحرك_30'],
        mode='lines',
        name='المتوسط المتحرك (30 يوم)',
        line=dict(color='#e74c3c', width=3)
    ))
    
    # التنبؤات
    fig4.add_trace(go.Scatter(
        x=future_dates,
        y=future_predictions,
        mode='lines',
        name='التنبؤات الذكية',
        line=dict(color='#9b59b6', width=3, dash='dash')
    ))
    
    fig4.update_layout(
        title=dict(
            text='📊 تحليل السلاسل الزمنية والتنبؤات المستقبلية',
            x=0.5,
            y=0.95,
            font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
        ),
        xaxis_title="التاريخ",
        yaxis_title="المبيعات (ريال)",
        font=dict(size=14, family="Cairo, Arial"),
        plot_bgcolor='#fafafa',
        paper_bgcolor='white',
        height=550,
        margin=dict(l=60, r=60, t=80, b=60),
        xaxis=dict(
            showgrid=True,
            gridcolor='#e8e8e8',
            gridwidth=1,
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#e8e8e8',
            gridwidth=1,
            tickformat=',.0f',
            zeroline=False
        ),
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig4, use_container_width=True)
    
    # الرسم البياني 5 و 6: تحليل متقدم ثنائي
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("5️⃣ تحليل الانحدار والارتباط")
        
        # تحليل العلاقة بين المتغيرات
        fig5 = go.Figure()
        
        # إضافة نقاط البيانات
        fig5.add_trace(go.Scatter(
            x=filtered_df['رضا_العملاء'],
            y=filtered_df['المبيعات'],
            mode='markers',
            marker=dict(
                size=8,
                color=filtered_df['الربح'],
                colorscale='Plasma',
                showscale=True,
                colorbar=dict(title="الربح", x=1.1),
                opacity=0.7
            ),
            name='نقاط البيانات',
            hovertemplate='رضا العملاء: %{x}<br>المبيعات: %{y:,.0f}<br>الربح: %{marker.color:,.0f}<extra></extra>'
        ))
        
        # إضافة خط الانحدار
        z = np.polyfit(filtered_df['رضا_العملاء'], filtered_df['المبيعات'], 1)
        p = np.poly1d(z)
        x_trend = np.linspace(filtered_df['رضا_العملاء'].min(), filtered_df['رضا_العملاء'].max(), 100)
        
        fig5.add_trace(go.Scatter(
            x=x_trend,
            y=p(x_trend),
            mode='lines',
            name='خط الاتجاه',
            line=dict(color='red', width=3, dash='dash')
        ))
        
        fig5.update_layout(
            title=dict(
                text='🔍 العلاقة بين رضا العملاء والمبيعات',
                x=0.5,
                y=0.95,
                font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
            ),
            xaxis_title="رضا العملاء (1-5)",
            yaxis_title="المبيعات (ريال)",
            font=dict(size=14, family="Cairo, Arial"),
            plot_bgcolor='#fafafa',
            paper_bgcolor='white',
            height=550,
            margin=dict(l=60, r=60, t=80, b=60),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                zeroline=False
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                tickformat=',.0f',
                zeroline=False
            )
        )
        
        st.plotly_chart(fig5, use_container_width=True)
    
    with col2:
        st.subheader("6️⃣ تحليل التوزيع الإحصائي")
        
        # رسم بياني للتوزيع
        fig6 = go.Figure()
        
        # إضافة هيستوجرام
        fig6.add_trace(go.Histogram(
            x=filtered_df['المبيعات'],
            nbinsx=30,
            name='توزيع المبيعات',
            marker_color='rgba(243, 156, 18, 0.7)',
            yaxis='y'
        ))
        
        # إضافة منحنى الكثافة
        from scipy import stats
        sales_data = filtered_df['المبيعات'].dropna()
        x_range = np.linspace(sales_data.min(), sales_data.max(), 100)
        kde = stats.gaussian_kde(sales_data)
        kde_values = kde(x_range) * len(sales_data) * (sales_data.max() - sales_data.min()) / 30
        
        fig6.add_trace(go.Scatter(
            x=x_range,
            y=kde_values,
            mode='lines',
            name='منحنى الكثافة',
            line=dict(color='red', width=3),
            yaxis='y'
        ))
        
        fig6.update_layout(
            title=dict(
                text='📈 التوزيع الإحصائي للمبيعات',
                x=0.5,
                y=0.95,
                font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
            ),
            xaxis_title="المبيعات (ريال)",
            yaxis_title="التكرار",
            font=dict(size=14, family="Cairo, Arial"),
            plot_bgcolor='#fafafa',
            paper_bgcolor='white',
            height=550,
            margin=dict(l=60, r=60, t=80, b=60),
            xaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                tickformat=',.0f',
                zeroline=False
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='#e8e8e8',
                gridwidth=1,
                zeroline=False
            ),
            showlegend=True
        )
        
        st.plotly_chart(fig6, use_container_width=True)
    
    # الرسم البياني 7: تحليل الأداء المقارن
    st.subheader("7️⃣ تحليل الأداء المقارن متعدد المؤشرات")
    
    # إعداد بيانات المقارنة
    comparison_data = filtered_df.groupby('قناة_البيع').agg({
        'المبيعات': 'sum',
        'الربح': 'sum',
        'رضا_العملاء': 'mean',
        'معدل_النمو': 'mean'
    }).reset_index()
    
    # تطبيع البيانات للمقارنة
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    metrics = ['المبيعات', 'الربح', 'رضا_العملاء', 'معدل_النمو']
    comparison_data[metrics] = scaler.fit_transform(comparison_data[metrics])
    
    fig7 = go.Figure()
    
    colors_radar = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, channel in enumerate(comparison_data['قناة_البيع']):
        values = comparison_data[comparison_data['قناة_البيع'] == channel][metrics].values[0]
        
        fig7.add_trace(go.Scatterpolar(
            r=list(values) + [values[0]],  # إغلاق الشكل
            theta=metrics + [metrics[0]],
            fill='toself',
            name=channel,
            line_color=colors_radar[i % len(colors_radar)],
            fillcolor=colors_radar[i % len(colors_radar)]
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
            text='🎯 مقارنة الأداء عبر قنوات البيع',
            x=0.5,
            y=0.95,
            font=dict(size=24, family="Cairo, Arial", color='#2c3e50')
        ),
        font=dict(size=14, family="Cairo, Arial"),
        height=550,
        margin=dict(l=60, r=60, t=80, b=60),
        paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.1,
            xanchor="center",
            x=0.5
        )
    )
    
    st.plotly_chart(fig7, use_container_width=True)
    
    # الرسم البياني 8: لوحة معلومات تنفيذية شاملة
    st.subheader("8️⃣ لوحة المعلومات التنفيذية الشاملة")
    
    # إنشاء subplots متعددة
    from plotly.subplots import make_subplots
    
    fig8 = make_subplots(
        rows=2, cols=2,
        subplot_titles=('الاتجاه الزمني للأرباح', 'توزيع العملاء حسب النوع', 
                       'مؤشر الأداء الشهري', 'تحليل الموسمية'),
        specs=[[{"secondary_y": True}, {"type": "pie"}],
               [{"type": "bar"}, {"type": "scatter"}]]
    )
    
    # الرسم الفرعي 1: الاتجاه الزمني للأرباح
    monthly_profit = filtered_df.groupby(filtered_df['التاريخ'].dt.to_period('M')).agg({
        'الربح': 'sum',
        'المبيعات': 'sum'
    }).reset_index()
    monthly_profit['الشهر'] = monthly_profit['التاريخ'].astype(str)
    
    fig8.add_trace(
        go.Scatter(x=monthly_profit['الشهر'], y=monthly_profit['الربح'],
                  name='الأرباح الشهرية', line=dict(color='green', width=3)),
        row=1, col=1
    )
    
    # الرسم الفرعي 2: توزيع العملاء
    customer_dist = filtered_df['نوع_العميل'].value_counts()
    fig8.add_trace(
        go.Pie(labels=customer_dist.index, values=customer_dist.values,
               name="نوع العميل", marker_colors=['#ff9999','#66b3ff','#99ff99']),
        row=1, col=2
    )
    
    # الرسم الفرعي 3: مؤشر الأداء الشهري
    performance_index = monthly_profit['الربح'] / monthly_profit['المبيعات'] * 100
    fig8.add_trace(
        go.Bar(x=monthly_profit['الشهر'], y=performance_index,
               name='مؤشر الأداء %', marker_color='orange'),
        row=2, col=1
    )
    
    # الرسم الفرعي 4: تحليل الموسمية
    seasonal_data = filtered_df.groupby('الموسم')['المبيعات'].mean()
    fig8.add_trace(
        go.Scatter(x=seasonal_data.index, y=seasonal_data.values,
                  mode='markers+lines', name='المبيعات الموسمية',
                  marker=dict(size=15, color='purple')),
        row=2, col=2
    )
    
    fig8.update_layout(
        title_text="📊 لوحة المعلومات التنفيذية الشاملة",
        title_font=dict(size=24, family="Cairo, Arial", color='#2c3e50'),
        title_x=0.5,
        title_y=0.98,
        height=750,
        showlegend=True,
        font=dict(size=14, family="Cairo, Arial"),
        paper_bgcolor='white',
        plot_bgcolor='#fafafa',
        margin=dict(l=60, r=60, t=100, b=60)
    )
    
    st.plotly_chart(fig8, use_container_width=True)
    
    # إحصائيات متقدمة
    st.subheader("📋 التحليل التفصيلي")
    
    tab1, tab2, tab3 = st.tabs(["إحصائيات وصفية", "تحليل الاتجاهات", "التوصيات الذكية"])
    
    with tab1:
        st.write("### الإحصائيات الوصفية للبيانات")
        st.dataframe(filtered_df[numeric_cols].describe())
    
    with tab2:
        st.write("### تحليل الاتجاهات")
        
        # أفضل المناطق
        top_regions = filtered_df.groupby('المنطقة')['المبيعات'].sum().sort_values(ascending=False).head(5)
        st.write("**أفضل 5 مناطق من حيث المبيعات:**")
        for i, (region, sales) in enumerate(top_regions.items(), 1):
            st.write(f"{i}. {region}: {sales:,.0f} ريال")
        
        # أفضل المنتجات
        top_products = filtered_df.groupby('المنتج')['الربح'].sum().sort_values(ascending=False).head(5)
        st.write("**أفضل 5 منتجات من حيث الربحية:**")
        for i, (product, profit) in enumerate(top_products.items(), 1):
            st.write(f"{i}. {product}: {profit:,.0f} ريال")
    
    with tab3:
        st.write("### التوصيات الذكية")
        
        st.success("🎯 **توصيات لزيادة المبيعات:**")
        st.write("• التركيز على منطقة الرياض حيث تحقق أعلى مبيعات")
        st.write("• زيادة المخزون من الهواتف الذكية في الربع القادم")
        st.write("• تطوير استراتيجية تسويقية للعملاء المؤسسيين")
        
        st.info("📊 **تحسينات مقترحة:**")
        st.write("• تحسين رضا العملاء في المنتجات ذات التقييم المنخفض")
        st.write("• استغلال الموسمية في شهر ديسمبر لزيادة المبيعات")
        st.write("• تطوير قنوات البيع الإلكترونية")
        
        st.warning("⚠️ **تحذيرات:**")
        st.write("• مراقبة انخفاض المبيعات في بعض المناطق")
        st.write("• مراجعة استراتيجية التسعير للمنتجات منخفضة الأداء")
    
    # عرض البيانات الخام
    with st.expander("عرض البيانات الخام"):
        st.dataframe(filtered_df)
        
        # إمكانية تحميل البيانات
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="تحميل البيانات كملف CSV",
            data=csv,
            file_name='data_analysis.csv',
            mime='text/csv'
        )

if __name__ == "__main__":
    main()
