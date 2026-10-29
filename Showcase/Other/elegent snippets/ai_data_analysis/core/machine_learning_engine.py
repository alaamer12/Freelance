# Service ID: AIQ11 - Machine Learning Engine
# محرك التعلم الآلي المتقدم

import numpy as np
import pandas as pd
import joblib
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.svm import SVC, SVR
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import mean_squared_error, r2_score, classification_report

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """
    Machine learning model configuration
    تكوين نموذج التعلم الآلي
    """
    name: str
    algorithm: str
    task_type: str  # classification, regression
    hyperparameters: Dict[str, Any] = None
    preprocessing: Dict[str, Any] = None
    validation_split: float = 0.2
    cross_validation_folds: int = 5

class MLEngine:
    """
    Advanced machine learning engine with automated model selection and optimization
    محرك التعلم الآلي المتقدم مع اختيار النماذج والتحسين التلقائي
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "ml_models"
        self.experiments_path = workspace_path / "ml_experiments"
        
        for path in [self.models_path, self.experiments_path]:
            path.mkdir(exist_ok=True)
        
        self.trained_models: Dict[str, Any] = {}
        self.model_performance: Dict[str, Dict[str, Any]] = {}
        self.preprocessing_pipelines: Dict[str, Any] = {}
    
    def train_model(self, config: ModelConfig, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """
        Train machine learning model with optimization
        تدريب نموذج التعلم الآلي مع التحسين
        """
        training_start = datetime.utcnow()
        
        try:
            # Preprocessing
            X_processed, preprocessor = self._preprocess_data(X, config.preprocessing)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_processed, y, test_size=config.validation_split, random_state=42
            )
            
            # Initialize model
            model = self._initialize_model(config.algorithm, config.hyperparameters)
            
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test)
            performance = self._evaluate_model(y_test, y_pred, config.task_type)
            
            # Cross validation
            cv_scores = cross_val_score(
                model, X_processed, y, cv=config.cross_validation_folds
            )
            
            # Store model and results
            self.trained_models[config.name] = model
            self.preprocessing_pipelines[config.name] = preprocessor
            
            training_time = (datetime.utcnow() - training_start).total_seconds()
            
            results = {
                'model_name': config.name,
                'algorithm': config.algorithm,
                'task_type': config.task_type,
                'training_time_seconds': training_time,
                'performance': performance,
                'cross_validation_scores': cv_scores.tolist(),
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std(),
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'feature_count': X_processed.shape[1],
                'trained_at': training_start.isoformat()
            }
            
            self.model_performance[config.name] = results
            
            # Save model
            self._save_model(config.name, model, preprocessor, results)
            
            logger.info(f"Model trained successfully: {config.name}")
            return results
            
        except Exception as e:
            logger.error(f"Model training failed: {str(e)}")
            raise
    
    def predict(self, model_name: str, X: pd.DataFrame) -> Dict[str, Any]:
        """
        Make predictions using trained model
        إجراء تنبؤات باستخدام النموذج المدرب
        """
        if model_name not in self.trained_models:
            raise ValueError(f"Model not found: {model_name}")
        
        try:
            model = self.trained_models[model_name]
            preprocessor = self.preprocessing_pipelines[model_name]
            
            # Preprocess input data
            X_processed = preprocessor.transform(X)
            
            # Make predictions
            predictions = model.predict(X_processed)
            
            # Get prediction probabilities if available
            probabilities = None
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(X_processed)
            
            return {
                'model_name': model_name,
                'predictions': predictions.tolist(),
                'probabilities': probabilities.tolist() if probabilities is not None else None,
                'sample_count': len(predictions),
                'predicted_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise
    
    def _preprocess_data(self, X: pd.DataFrame, preprocessing_config: Dict[str, Any]) -> Tuple[np.ndarray, Any]:
        """
        Preprocess data for training
        معالجة البيانات للتدريب
        """
        if not preprocessing_config:
            return X.values, None
        
        from sklearn.compose import ColumnTransformer
        from sklearn.pipeline import Pipeline
        
        transformers = []
        
        # Numerical features
        numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
        if numeric_features and preprocessing_config.get('scale_numeric', True):
            transformers.append(('num', StandardScaler(), numeric_features))
        
        # Categorical features
        categorical_features = X.select_dtypes(include=['object']).columns.tolist()
        if categorical_features:
            if preprocessing_config.get('encode_categorical', 'onehot') == 'onehot':
                transformers.append(('cat', OneHotEncoder(drop='first', sparse=False), categorical_features))
            else:
                # Label encoding for each categorical column
                for col in categorical_features:
                    le = LabelEncoder()
                    X[col] = le.fit_transform(X[col].astype(str))
        
        if transformers:
            preprocessor = ColumnTransformer(transformers=transformers, remainder='passthrough')
            X_processed = preprocessor.fit_transform(X)
        else:
            preprocessor = None
            X_processed = X.values
        
        return X_processed, preprocessor
    
    def _initialize_model(self, algorithm: str, hyperparameters: Dict[str, Any]) -> Any:
        """
        Initialize ML model based on algorithm
        تهيئة نموذج التعلم الآلي بناءً على الخوارزمية
        """
        params = hyperparameters or {}
        
        models = {
            'random_forest_classifier': RandomForestClassifier(**params),
            'random_forest_regressor': GradientBoostingRegressor(**params),
            'logistic_regression': LogisticRegression(**params),
            'linear_regression': LinearRegression(**params),
            'svm_classifier': SVC(**params),
            'svm_regressor': SVR(**params)
        }
        
        if algorithm not in models:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        return models[algorithm]
    
    def _evaluate_model(self, y_true: np.ndarray, y_pred: np.ndarray, task_type: str) -> Dict[str, float]:
        """
        Evaluate model performance
        تقييم أداء النموذج
        """
        if task_type == 'classification':
            return {
                'accuracy': accuracy_score(y_true, y_pred),
                'precision': precision_score(y_true, y_pred, average='weighted'),
                'recall': recall_score(y_true, y_pred, average='weighted'),
                'f1_score': f1_score(y_true, y_pred, average='weighted')
            }
        else:  # regression
            return {
                'mse': mean_squared_error(y_true, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
                'r2_score': r2_score(y_true, y_pred),
                'mae': np.mean(np.abs(y_true - y_pred))
            }
    
    def _save_model(self, model_name: str, model: Any, preprocessor: Any, results: Dict[str, Any]):
        """
        Save trained model and metadata
        حفظ النموذج المدرب والبيانات الوصفية
        """
        model_dir = self.models_path / model_name
        model_dir.mkdir(exist_ok=True)
        
        # Save model
        joblib.dump(model, model_dir / "model.pkl")
        
        # Save preprocessor
        if preprocessor:
            joblib.dump(preprocessor, model_dir / "preprocessor.pkl")
        
        # Save metadata
        with open(model_dir / "metadata.json", 'w') as f:
            json.dump(results, f, indent=2)
    
    def load_model(self, model_name: str) -> bool:
        """
        Load saved model
        تحميل النموذج المحفوظ
        """
        model_dir = self.models_path / model_name
        
        if not model_dir.exists():
            return False
        
        try:
            # Load model
            model = joblib.load(model_dir / "model.pkl")
            self.trained_models[model_name] = model
            
            # Load preprocessor if exists
            preprocessor_path = model_dir / "preprocessor.pkl"
            if preprocessor_path.exists():
                preprocessor = joblib.load(preprocessor_path)
                self.preprocessing_pipelines[model_name] = preprocessor
            
            # Load metadata
            metadata_path = model_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                self.model_performance[model_name] = metadata
            
            logger.info(f"Model loaded successfully: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            return False
    
    def hyperparameter_tuning(self, config: ModelConfig, X: pd.DataFrame, y: pd.Series, 
                            param_grid: Dict[str, List]) -> Dict[str, Any]:
        """
        Perform hyperparameter tuning
        تنفيذ ضبط المعاملات الفائقة
        """
        try:
            # Preprocess data
            X_processed, preprocessor = self._preprocess_data(X, config.preprocessing)
            
            # Initialize base model
            base_model = self._initialize_model(config.algorithm, {})
            
            # Grid search
            grid_search = GridSearchCV(
                base_model, param_grid, cv=config.cross_validation_folds,
                scoring='accuracy' if config.task_type == 'classification' else 'r2',
                n_jobs=-1
            )
            
            grid_search.fit(X_processed, y)
            
            # Update config with best parameters
            tuned_config = ModelConfig(
                name=f"{config.name}_tuned",
                algorithm=config.algorithm,
                task_type=config.task_type,
                hyperparameters=grid_search.best_params_,
                preprocessing=config.preprocessing,
                validation_split=config.validation_split,
                cross_validation_folds=config.cross_validation_folds
            )
            
            # Train model with best parameters
            results = self.train_model(tuned_config, X, y)
            
            tuning_results = {
                'original_model': config.name,
                'tuned_model': tuned_config.name,
                'best_parameters': grid_search.best_params_,
                'best_score': grid_search.best_score_,
                'tuning_results': results
            }
            
            logger.info(f"Hyperparameter tuning completed for {config.name}")
            return tuning_results
            
        except Exception as e:
            logger.error(f"Hyperparameter tuning failed: {str(e)}")
            raise
    
    def compare_models(self, model_names: List[str]) -> Dict[str, Any]:
        """
        Compare performance of multiple models
        مقارنة أداء عدة نماذج
        """
        if not model_names:
            return {'error': 'No models specified for comparison'}
        
        comparison = {
            'models_compared': len(model_names),
            'comparison_timestamp': datetime.utcnow().isoformat(),
            'model_performances': {},
            'best_model': None,
            'ranking': []
        }
        
        valid_models = []
        
        for model_name in model_names:
            if model_name in self.model_performance:
                performance = self.model_performance[model_name]
                comparison['model_performances'][model_name] = performance
                valid_models.append((model_name, performance))
        
        if not valid_models:
            return {'error': 'No valid models found for comparison'}
        
        # Rank models based on primary metric
        if valid_models[0][1]['task_type'] == 'classification':
            # Sort by accuracy (descending)
            valid_models.sort(key=lambda x: x[1]['performance'].get('accuracy', 0), reverse=True)
            best_metric = 'accuracy'
        else:
            # Sort by R2 score (descending)
            valid_models.sort(key=lambda x: x[1]['performance'].get('r2_score', -float('inf')), reverse=True)
            best_metric = 'r2_score'
        
        comparison['best_model'] = valid_models[0][0]
        comparison['best_metric'] = best_metric
        comparison['ranking'] = [model[0] for model in valid_models]
        
        return comparison
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a model
        الحصول على معلومات مفصلة حول النموذج
        """
        if model_name not in self.model_performance:
            return {'error': f'Model not found: {model_name}'}
        
        return self.model_performance[model_name]
    
    def list_models(self) -> List[str]:
        """
        List all trained models
        قائمة جميع النماذج المدربة
        """
        return list(self.trained_models.keys())
