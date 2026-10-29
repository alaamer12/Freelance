# Service ID: AIQ69 - Predictive Analytics and Forecasting Engine
# محرك التحليلات التنبؤية والتنبؤ المتقدم

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.svm import SVR
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, TimeSeriesSplit
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json
import warnings
warnings.filterwarnings('ignore')

# Time series specific imports
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller
import matplotlib.pyplot as plt
import seaborn as sns

# Prophet for advanced forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not available. Install with: pip install prophet")

logger = logging.getLogger(__name__)

@dataclass
class ForecastConfig:
    """
    Forecasting configuration
    تكوين التنبؤ
    """
    model_type: str = "auto"  # auto, arima, prophet, linear, rf, gbm
    forecast_horizon: int = 30
    confidence_interval: float = 0.95
    seasonality: bool = True
    trend: bool = True
    include_holidays: bool = False
    cross_validation_folds: int = 5

@dataclass
class PredictionResult:
    """
    Prediction result container
    حاوي نتائج التنبؤ
    """
    model_name: str
    predictions: List[float]
    confidence_intervals: List[Tuple[float, float]] = None
    feature_importance: Dict[str, float] = None
    model_metrics: Dict[str, float] = None
    forecast_dates: List[str] = None
    model_parameters: Dict[str, Any] = None
    created_at: str = None

class AdvancedPredictiveAnalyticsEngine:
    """
    Advanced predictive analytics and forecasting engine
    محرك التحليلات التنبؤية والتنبؤ المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "forecasting_models"
        self.results_path = workspace_path / "forecast_results"
        self.plots_path = workspace_path / "forecast_plots"
        
        for path in [self.models_path, self.results_path, self.plots_path]:
            path.mkdir(exist_ok=True)
        
        self.trained_models: Dict[str, Any] = {}
        self.forecast_history: List[Dict[str, Any]] = []
        self.model_performance: Dict[str, Dict[str, float]] = {}
    
    def create_forecast(self, data: pd.DataFrame, target_column: str, 
                       date_column: str = None, config: ForecastConfig = None) -> PredictionResult:
        """
        Create comprehensive forecast using multiple models
        إنشاء تنبؤ شامل باستخدام نماذج متعددة
        """
        if config is None:
            config = ForecastConfig()
        
        forecast_start = datetime.utcnow()
        
        try:
            # Prepare data
            prepared_data = self._prepare_time_series_data(data, target_column, date_column)
            
            # Select best model if auto mode
            if config.model_type == "auto":
                best_model = self._select_best_model(prepared_data, target_column, config)
                config.model_type = best_model
            
            # Create forecast based on model type
            if config.model_type == "prophet" and PROPHET_AVAILABLE:
                result = self._forecast_with_prophet(prepared_data, target_column, config)
            elif config.model_type == "arima":
                result = self._forecast_with_arima(prepared_data, target_column, config)
            elif config.model_type in ["linear", "rf", "gbm", "svr"]:
                result = self._forecast_with_ml(prepared_data, target_column, config)
            else:
                # Fallback to exponential smoothing
                result = self._forecast_with_exponential_smoothing(prepared_data, target_column, config)
            
            # Add metadata
            result.created_at = forecast_start.isoformat()
            
            # Save forecast result
            self._save_forecast_result(result, prepared_data, target_column)
            
            # Record in history
            self.forecast_history.append({
                'model_name': result.model_name,
                'target_column': target_column,
                'forecast_horizon': config.forecast_horizon,
                'data_points': len(prepared_data),
                'model_metrics': result.model_metrics,
                'created_at': forecast_start.isoformat()
            })
            
            logger.info(f"Forecast created successfully: {result.model_name}")
            return result
            
        except Exception as e:
            logger.error(f"Forecast creation failed: {str(e)}")
            raise
    
    def _prepare_time_series_data(self, data: pd.DataFrame, target_column: str, 
                                 date_column: str = None) -> pd.DataFrame:
        """
        Prepare time series data for forecasting
        إعداد بيانات السلاسل الزمنية للتنبؤ
        """
        df = data.copy()
        
        # Handle date column
        if date_column and date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.sort_values(date_column)
            df.set_index(date_column, inplace=True)
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df.set_index('date', inplace=True)
        else:
            # Create date index if none exists
            df.index = pd.date_range(start='2020-01-01', periods=len(df), freq='D')
        
        # Handle missing values
        df[target_column] = df[target_column].fillna(method='ffill').fillna(method='bfill')
        
        # Remove outliers using IQR method
        Q1 = df[target_column].quantile(0.25)
        Q3 = df[target_column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        df[target_column] = df[target_column].clip(lower=lower_bound, upper=upper_bound)
        
        return df
    
    def _select_best_model(self, data: pd.DataFrame, target_column: str, 
                          config: ForecastConfig) -> str:
        """
        Select best forecasting model based on data characteristics
        اختيار أفضل نموذج تنبؤ بناءً على خصائص البيانات
        """
        try:
            # Analyze data characteristics
            series = data[target_column]
            
            # Check for stationarity
            adf_result = adfuller(series.dropna())
            is_stationary = adf_result[1] < 0.05
            
            # Check for seasonality
            if len(series) >= 24:  # Need enough data for seasonal decomposition
                try:
                    decomposition = seasonal_decompose(series, model='additive', period=min(12, len(series)//2))
                    seasonal_strength = np.var(decomposition.seasonal) / np.var(series)
                    has_strong_seasonality = seasonal_strength > 0.1
                except:
                    has_strong_seasonality = False
            else:
                has_strong_seasonality = False
            
            # Check data size
            data_size = len(series)
            
            # Model selection logic
            if PROPHET_AVAILABLE and data_size >= 100 and has_strong_seasonality:
                return "prophet"
            elif data_size >= 50 and not is_stationary:
                return "arima"
            elif data_size >= 100:
                return "gbm"  # Gradient boosting for larger datasets
            else:
                return "exponential_smoothing"
                
        except Exception as e:
            logger.warning(f"Model selection failed, using default: {str(e)}")
            return "exponential_smoothing"
    
    def _forecast_with_prophet(self, data: pd.DataFrame, target_column: str, 
                              config: ForecastConfig) -> PredictionResult:
        """
        Create forecast using Facebook Prophet
        إنشاء تنبؤ باستخدام Facebook Prophet
        """
        # Prepare data for Prophet
        prophet_data = data.reset_index()
        prophet_data = prophet_data.rename(columns={
            prophet_data.columns[0]: 'ds',  # Date column
            target_column: 'y'  # Target column
        })
        
        # Initialize Prophet model
        model = Prophet(
            yearly_seasonality=config.seasonality,
            weekly_seasonality=config.seasonality,
            daily_seasonality=False,
            interval_width=config.confidence_interval
        )
        
        # Fit model
        model.fit(prophet_data)
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=config.forecast_horizon)
        
        # Make predictions
        forecast = model.predict(future)
        
        # Extract results
        predictions = forecast['yhat'].tail(config.forecast_horizon).tolist()
        confidence_intervals = list(zip(
            forecast['yhat_lower'].tail(config.forecast_horizon).tolist(),
            forecast['yhat_upper'].tail(config.forecast_horizon).tolist()
        ))
        
        # Generate forecast dates
        last_date = data.index[-1]
        forecast_dates = [
            (last_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(config.forecast_horizon)
        ]
        
        # Calculate metrics on training data
        train_predictions = forecast['yhat'].iloc[:-config.forecast_horizon]
        actual_values = prophet_data['y']
        
        metrics = {
            'mae': mean_absolute_error(actual_values, train_predictions),
            'mse': mean_squared_error(actual_values, train_predictions),
            'rmse': np.sqrt(mean_squared_error(actual_values, train_predictions)),
            'r2': r2_score(actual_values, train_predictions)
        }
        
        return PredictionResult(
            model_name="prophet",
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            model_metrics=metrics,
            forecast_dates=forecast_dates,
            model_parameters={
                'seasonality': config.seasonality,
                'confidence_interval': config.confidence_interval
            }
        )
    
    def _forecast_with_arima(self, data: pd.DataFrame, target_column: str, 
                            config: ForecastConfig) -> PredictionResult:
        """
        Create forecast using ARIMA model
        إنشاء تنبؤ باستخدام نموذج ARIMA
        """
        series = data[target_column]
        
        # Auto-determine ARIMA parameters
        try:
            from statsmodels.tsa.arima.model import auto_arima
            auto_model = auto_arima(series, seasonal=config.seasonality, stepwise=True, 
                                  suppress_warnings=True, error_action='ignore')
            order = auto_model.order
            seasonal_order = auto_model.seasonal_order if config.seasonality else None
        except:
            # Fallback to simple ARIMA(1,1,1)
            order = (1, 1, 1)
            seasonal_order = None
        
        # Fit ARIMA model
        model = ARIMA(series, order=order, seasonal_order=seasonal_order)
        fitted_model = model.fit()
        
        # Make predictions
        forecast_result = fitted_model.forecast(steps=config.forecast_horizon, alpha=1-config.confidence_interval)
        predictions = forecast_result.tolist()
        
        # Get confidence intervals
        forecast_ci = fitted_model.get_forecast(steps=config.forecast_horizon, alpha=1-config.confidence_interval)
        confidence_intervals = list(zip(
            forecast_ci.conf_int().iloc[:, 0].tolist(),
            forecast_ci.conf_int().iloc[:, 1].tolist()
        ))
        
        # Generate forecast dates
        last_date = data.index[-1]
        forecast_dates = [
            (last_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(config.forecast_horizon)
        ]
        
        # Calculate metrics
        fitted_values = fitted_model.fittedvalues
        actual_values = series[fitted_values.index]
        
        metrics = {
            'mae': mean_absolute_error(actual_values, fitted_values),
            'mse': mean_squared_error(actual_values, fitted_values),
            'rmse': np.sqrt(mean_squared_error(actual_values, fitted_values)),
            'aic': fitted_model.aic,
            'bic': fitted_model.bic
        }
        
        return PredictionResult(
            model_name="arima",
            predictions=predictions,
            confidence_intervals=confidence_intervals,
            model_metrics=metrics,
            forecast_dates=forecast_dates,
            model_parameters={
                'order': order,
                'seasonal_order': seasonal_order
            }
        )
    
    def _forecast_with_ml(self, data: pd.DataFrame, target_column: str, 
                         config: ForecastConfig) -> PredictionResult:
        """
        Create forecast using machine learning models
        إنشاء تنبؤ باستخدام نماذج التعلم الآلي
        """
        # Create features for ML models
        ml_data = self._create_ml_features(data, target_column)
        
        # Prepare features and target
        feature_columns = [col for col in ml_data.columns if col != target_column]
        X = ml_data[feature_columns]
        y = ml_data[target_column]
        
        # Split data (use last 20% for validation)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        # Select and train model
        if config.model_type == "rf":
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif config.model_type == "gbm":
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        elif config.model_type == "svr":
            model = SVR(kernel='rbf', C=1.0, gamma='scale')
        else:  # linear
            model = Ridge(alpha=1.0)
        
        # Train model
        if config.model_type == "svr":
            model.fit(X_train_scaled, y_train)
            val_predictions = model.predict(X_val_scaled)
        else:
            model.fit(X_train, y_train)
            val_predictions = model.predict(X_val)
        
        # Calculate metrics
        metrics = {
            'mae': mean_absolute_error(y_val, val_predictions),
            'mse': mean_squared_error(y_val, val_predictions),
            'rmse': np.sqrt(mean_squared_error(y_val, val_predictions)),
            'r2': r2_score(y_val, val_predictions)
        }
        
        # Get feature importance
        feature_importance = {}
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(feature_columns, model.feature_importances_))
        elif hasattr(model, 'coef_'):
            feature_importance = dict(zip(feature_columns, abs(model.coef_)))
        
        # Make future predictions
        predictions = []
        last_features = X.iloc[-1:].copy()
        
        for i in range(config.forecast_horizon):
            if config.model_type == "svr":
                next_pred = model.predict(scaler.transform(last_features))[0]
            else:
                next_pred = model.predict(last_features)[0]
            
            predictions.append(next_pred)
            
            # Update features for next prediction
            # Shift lag features
            for col in feature_columns:
                if 'lag_' in col:
                    lag_num = int(col.split('_')[-1])
                    if lag_num > 1:
                        last_features[col] = last_features[f'lag_{lag_num-1}']
                    else:
                        last_features[col] = next_pred
        
        # Generate forecast dates
        last_date = data.index[-1]
        forecast_dates = [
            (last_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(config.forecast_horizon)
        ]
        
        return PredictionResult(
            model_name=config.model_type,
            predictions=predictions,
            feature_importance=feature_importance,
            model_metrics=metrics,
            forecast_dates=forecast_dates,
            model_parameters={
                'features_used': feature_columns,
                'training_samples': len(X_train)
            }
        )
    
    def _forecast_with_exponential_smoothing(self, data: pd.DataFrame, target_column: str, 
                                           config: ForecastConfig) -> PredictionResult:
        """
        Create forecast using Exponential Smoothing
        إنشاء تنبؤ باستخدام التنعيم الأسي
        """
        series = data[target_column]
        
        # Determine seasonality period
        seasonal_periods = min(12, len(series) // 4) if config.seasonality and len(series) >= 24 else None
        
        # Fit Exponential Smoothing model
        model = ExponentialSmoothing(
            series,
            trend='add' if config.trend else None,
            seasonal='add' if seasonal_periods else None,
            seasonal_periods=seasonal_periods
        )
        
        fitted_model = model.fit()
        
        # Make predictions
        forecast_result = fitted_model.forecast(config.forecast_horizon)
        predictions = forecast_result.tolist()
        
        # Generate forecast dates
        last_date = data.index[-1]
        forecast_dates = [
            (last_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
            for i in range(config.forecast_horizon)
        ]
        
        # Calculate metrics
        fitted_values = fitted_model.fittedvalues
        actual_values = series[fitted_values.index]
        
        metrics = {
            'mae': mean_absolute_error(actual_values, fitted_values),
            'mse': mean_squared_error(actual_values, fitted_values),
            'rmse': np.sqrt(mean_squared_error(actual_values, fitted_values)),
            'aic': fitted_model.aic
        }
        
        return PredictionResult(
            model_name="exponential_smoothing",
            predictions=predictions,
            model_metrics=metrics,
            forecast_dates=forecast_dates,
            model_parameters={
                'trend': config.trend,
                'seasonality': config.seasonality,
                'seasonal_periods': seasonal_periods
            }
        )
    
    def _create_ml_features(self, data: pd.DataFrame, target_column: str) -> pd.DataFrame:
        """
        Create features for machine learning models
        إنشاء ميزات لنماذج التعلم الآلي
        """
        df = data.copy()
        
        # Lag features
        for lag in [1, 2, 3, 7, 14, 30]:
            if lag < len(df):
                df[f'lag_{lag}'] = df[target_column].shift(lag)
        
        # Rolling statistics
        for window in [3, 7, 14, 30]:
            if window < len(df):
                df[f'rolling_mean_{window}'] = df[target_column].rolling(window=window).mean()
                df[f'rolling_std_{window}'] = df[target_column].rolling(window=window).std()
        
        # Time-based features
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        df['quarter'] = df.index.quarter
        df['year'] = df.index.year
        
        # Trend feature
        df['trend'] = range(len(df))
        
        # Drop rows with NaN values
        df = df.dropna()
        
        return df
    
    def analyze_forecast_accuracy(self, actual_values: List[float], 
                                 predicted_values: List[float]) -> Dict[str, float]:
        """
        Analyze forecast accuracy with multiple metrics
        تحليل دقة التنبؤ بمقاييس متعددة
        """
        try:
            actual = np.array(actual_values)
            predicted = np.array(predicted_values)
            
            # Basic metrics
            mae = mean_absolute_error(actual, predicted)
            mse = mean_squared_error(actual, predicted)
            rmse = np.sqrt(mse)
            
            # Percentage errors
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100
            smape = np.mean(2 * np.abs(actual - predicted) / (np.abs(actual) + np.abs(predicted))) * 100
            
            # Directional accuracy
            actual_direction = np.diff(actual) > 0
            predicted_direction = np.diff(predicted) > 0
            directional_accuracy = np.mean(actual_direction == predicted_direction) * 100
            
            return {
                'mae': float(mae),
                'mse': float(mse),
                'rmse': float(rmse),
                'mape': float(mape),
                'smape': float(smape),
                'directional_accuracy': float(directional_accuracy),
                'r2_score': float(r2_score(actual, predicted))
            }
            
        except Exception as e:
            logger.error(f"Accuracy analysis failed: {str(e)}")
            return {}
    
    def create_forecast_visualization(self, data: pd.DataFrame, target_column: str, 
                                    forecast_result: PredictionResult) -> str:
        """
        Create forecast visualization
        إنشاء تصور التنبؤ
        """
        try:
            plt.figure(figsize=(12, 8))
            
            # Plot historical data
            plt.plot(data.index, data[target_column], label='Historical Data', color='blue', linewidth=2)
            
            # Plot forecast
            last_date = data.index[-1]
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), 
                                         periods=len(forecast_result.predictions), freq='D')
            
            plt.plot(forecast_dates, forecast_result.predictions, 
                    label=f'Forecast ({forecast_result.model_name})', color='red', linewidth=2, linestyle='--')
            
            # Plot confidence intervals if available
            if forecast_result.confidence_intervals:
                lower_bounds = [ci[0] for ci in forecast_result.confidence_intervals]
                upper_bounds = [ci[1] for ci in forecast_result.confidence_intervals]
                
                plt.fill_between(forecast_dates, lower_bounds, upper_bounds, 
                               alpha=0.3, color='red', label='Confidence Interval')
            
            plt.title(f'Forecast for {target_column}', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel(target_column, fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Save plot
            plot_filename = f"forecast_{forecast_result.model_name}_{int(datetime.utcnow().timestamp())}.png"
            plot_path = self.plots_path / plot_filename
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(plot_path)
            
        except Exception as e:
            logger.error(f"Visualization creation failed: {str(e)}")
            return ""
    
    def _save_forecast_result(self, result: PredictionResult, data: pd.DataFrame, target_column: str):
        """
        Save forecast result to file
        حفظ نتيجة التنبؤ في ملف
        """
        try:
            result_file = self.results_path / f"forecast_{result.model_name}_{int(datetime.utcnow().timestamp())}.json"
            
            result_dict = {
                'model_name': result.model_name,
                'predictions': result.predictions,
                'confidence_intervals': result.confidence_intervals,
                'feature_importance': result.feature_importance,
                'model_metrics': result.model_metrics,
                'forecast_dates': result.forecast_dates,
                'model_parameters': result.model_parameters,
                'data_summary': {
                    'target_column': target_column,
                    'data_points': len(data),
                    'date_range': f"{data.index[0]} to {data.index[-1]}"
                },
                'created_at': result.created_at
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save forecast result: {str(e)}")
    
    def get_forecast_statistics(self) -> Dict[str, Any]:
        """
        Get forecasting engine statistics
        الحصول على إحصائيات محرك التنبؤ
        """
        if not self.forecast_history:
            return {
                'total_forecasts': 0,
                'models_used': [],
                'average_accuracy': 0
            }
        
        models_used = [item['model_name'] for item in self.forecast_history]
        from collections import Counter
        model_counts = Counter(models_used)
        
        # Calculate average metrics
        all_metrics = [item.get('model_metrics', {}) for item in self.forecast_history]
        avg_metrics = {}
        
        if all_metrics:
            metric_keys = set()
            for metrics in all_metrics:
                metric_keys.update(metrics.keys())
            
            for key in metric_keys:
                values = [metrics.get(key, 0) for metrics in all_metrics if key in metrics]
                if values:
                    avg_metrics[f'avg_{key}'] = sum(values) / len(values)
        
        return {
            'total_forecasts': len(self.forecast_history),
            'models_used': list(model_counts.keys()),
            'model_usage_distribution': dict(model_counts),
            'most_used_model': model_counts.most_common(1)[0][0] if model_counts else None,
            'average_metrics': avg_metrics,
            'generated_at': datetime.utcnow().isoformat()
        }
