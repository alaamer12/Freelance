# Service ID: AIQ04 - Deep Learning and Neural Networks Engine
# محرك التعلم العميق والشبكات العصبية المتقدم

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, TensorDataset
import torch.nn.functional as F
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, mean_squared_error
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

@dataclass
class NetworkConfig:
    """
    Neural network configuration
    تكوين الشبكة العصبية
    """
    task_type: str = "classification"  # classification, regression, autoencoder
    hidden_layers: List[int] = None
    activation: str = "relu"
    dropout_rate: float = 0.2
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping: bool = True
    patience: int = 10

@dataclass
class TrainingResult:
    """
    Training result container
    حاوي نتائج التدريب
    """
    model_name: str
    task_type: str
    final_accuracy: float = None
    final_loss: float = None
    training_history: Dict[str, List[float]] = None
    model_path: str = None
    feature_names: List[str] = None
    training_time: float = None
    created_at: str = None

class LearningEngine:
    """
    Learning and neural networks engine
    محرك التعلم العميق والشبكات العصبية المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "dl_models"
        self.results_path = workspace_path / "dl_results"
        self.plots_path = workspace_path / "dl_plots"
        
        for path in [self.models_path, self.results_path, self.plots_path]:
            path.mkdir(exist_ok=True)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.trained_models: Dict[str, nn.Module] = {}
        self.training_history: List[Dict[str, Any]] = []
        
        logger.info(f"Deep learning engine initialized on device: {self.device}")

class FlexibleNeuralNetwork(nn.Module):
    """
    Flexible neural network architecture
    بنية الشبكة العصبية المرنة
    """
    
    def __init__(self, input_size: int, output_size: int, hidden_layers: List[int], 
                 activation: str = "relu", dropout_rate: float = 0.2, task_type: str = "classification"):
        super(FlexibleNeuralNetwork, self).__init__()
        
        self.task_type = task_type
        self.layers = nn.ModuleList()
        
        # Input layer
        prev_size = input_size
        
        # Hidden layers
        for hidden_size in hidden_layers:
            self.layers.append(nn.Linear(prev_size, hidden_size))
            self.layers.append(self._get_activation(activation))
            self.layers.append(nn.Dropout(dropout_rate))
            prev_size = hidden_size
        
        # Output layer
        self.layers.append(nn.Linear(prev_size, output_size))
        
        # Add final activation for classification
        if task_type == "classification" and output_size > 1:
            self.layers.append(nn.Softmax(dim=1))
    
    def _get_activation(self, activation: str):
        """Get activation function"""
        activations = {
            "relu": nn.ReLU(),
            "tanh": nn.Tanh(),
            "sigmoid": nn.Sigmoid(),
            "leaky_relu": nn.LeakyReLU(),
            "elu": nn.ELU()
        }
        return activations.get(activation, nn.ReLU())
    
    def forward(self, x):
        for layer in self.layers:
            x = layer(x)
        return x

class NNetwork(nn.Module):
    """
    Convolutional neural network for image data
    الشبكة العصبية التطبيقية لبيانات الصور
    """
    
    def __init__(self, input_channels: int, num_classes: int):
        super(ConvolutionalNetwork, self).__init__()
        
        self.conv_layers = nn.Sequential(
            nn.Conv2d(input_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2)
        )
        
        # Calculate the size after conv layers
        self.fc_input_size = 128 * 4 * 4  # Assuming 32x32 input
        
        self.fc_layers = nn.Sequential(
            nn.Linear(self.fc_input_size, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )
    
    def forward(self, x):
        x = self.conv_layers(x)
        x = x.view(x.size(0), -1)  # Flatten
        x = self.fc_layers(x)
        return x

def train_neural_network(self, data: pd.DataFrame, target_column: str, 
                        config: NetworkConfig = None) -> TrainingResult:
    """
    Train neural network on tabular data
    تدريب الشبكة العصبية على البيانات الجدولية
    """
    if config is None:
        config = NetworkConfig()
    
    training_start = datetime.utcnow()
    model_name = f"nn_{config.task_type}_{int(training_start.timestamp())}"
    
    try:
        # Prepare data
        X, y, feature_names, label_encoder = self._prepare_tabular_data(data, target_column, config.task_type)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Create datasets
        train_dataset = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
        test_dataset = TensorDataset(torch.FloatTensor(X_test), torch.FloatTensor(y_test))
        
        train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False)
        
        # Create model
        input_size = X_train.shape[1]
        output_size = len(np.unique(y)) if config.task_type == "classification" else 1
        hidden_layers = config.hidden_layers or [128, 64, 32]
        
        model = FlexibleNeuralNetwork(
            input_size=input_size,
            output_size=output_size,
            hidden_layers=hidden_layers,
            activation=config.activation,
            dropout_rate=config.dropout_rate,
            task_type=config.task_type
        ).to(self.device)
        
        # Define loss and optimizer
        if config.task_type == "classification":
            criterion = nn.CrossEntropyLoss()
        else:
            criterion = nn.MSELoss()
        
        optimizer = optim.Adam(model.parameters(), lr=config.learning_rate)
        
        # Training loop
        training_history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(config.epochs):
            # Training phase
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            
            for batch_X, batch_y in train_loader:
                batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                
                optimizer.zero_grad()
                outputs = model(batch_X)
                
                if config.task_type == "classification":
                    loss = criterion(outputs, batch_y.long())
                    _, predicted = torch.max(outputs.data, 1)
                    train_correct += (predicted == batch_y.long()).sum().item()
                else:
                    loss = criterion(outputs.squeeze(), batch_y)
                
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
                train_total += batch_y.size(0)
            
            # Validation phase
            model.eval()
            val_loss = 0.0
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for batch_X, batch_y in test_loader:
                    batch_X, batch_y = batch_X.to(self.device), batch_y.to(self.device)
                    outputs = model(batch_X)
                    
                    if config.task_type == "classification":
                        loss = criterion(outputs, batch_y.long())
                        _, predicted = torch.max(outputs.data, 1)
                        val_correct += (predicted == batch_y.long()).sum().item()
                    else:
                        loss = criterion(outputs.squeeze(), batch_y)
                    
                    val_loss += loss.item()
                    val_total += batch_y.size(0)
            
            # Calculate metrics
            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(test_loader)
            
            training_history["train_loss"].append(avg_train_loss)
            training_history["val_loss"].append(avg_val_loss)
            
            if config.task_type == "classification":
                train_acc = 100 * train_correct / train_total
                val_acc = 100 * val_correct / val_total
                training_history["train_acc"].append(train_acc)
                training_history["val_acc"].append(val_acc)
            
            # Early stopping
            if config.early_stopping:
                if avg_val_loss < best_val_loss:
                    best_val_loss = avg_val_loss
                    patience_counter = 0
                    # Save best model
                    model_path = self.models_path / f"{model_name}_best.pth"
                    torch.save(model.state_dict(), model_path)
                else:
                    patience_counter += 1
                    if patience_counter >= config.patience:
                        logger.info(f"Early stopping at epoch {epoch}")
                        break
            
            if epoch % 10 == 0:
                logger.info(f"Epoch {epoch}: Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}")
        
        # Load best model if early stopping was used
        if config.early_stopping:
            model.load_state_dict(torch.load(model_path))
        else:
            model_path = self.models_path / f"{model_name}.pth"
            torch.save(model.state_dict(), model_path)
        
        # Final evaluation
        model.eval()
        final_accuracy = None
        final_loss = avg_val_loss
        
        if config.task_type == "classification":
            final_accuracy = val_acc
        
        # Store model
        self.trained_models[model_name] = model
        
        # Create result
        training_time = (datetime.utcnow() - training_start).total_seconds()
        
        result = TrainingResult(
            model_name=model_name,
            task_type=config.task_type,
            final_accuracy=final_accuracy,
            final_loss=final_loss,
            training_history=training_history,
            model_path=str(model_path),
            feature_names=feature_names,
            training_time=training_time,
            created_at=training_start.isoformat()
        )
        
        # Save result
        self._save_training_result(result)
        
        # Record in history
        self.training_history.append({
            'model_name': model_name,
            'task_type': config.task_type,
            'final_accuracy': final_accuracy,
            'final_loss': final_loss,
            'training_time': training_time,
            'created_at': training_start.isoformat()
        })
        
        logger.info(f"Neural network training completed: {model_name}")
        return result
        
    except Exception as e:
        logger.error(f"Neural network training failed: {str(e)}")
        raise

def _prepare_tabular_data(self, data: pd.DataFrame, target_column: str, 
                         task_type: str) -> Tuple[np.ndarray, np.ndarray, List[str], Any]:
    """
    Prepare tabular data for neural network training
    إعداد البيانات الجدولية لتدريب الشبكة العصبية
    """
    df = data.copy()
    
    # Separate features and target
    X = df.drop(columns=[target_column])
    y = df[target_column]
    
    # Handle categorical features
    categorical_columns = X.select_dtypes(include=['object']).columns
    for col in categorical_columns:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col].astype(str))
    
    # Handle missing values
    X = X.fillna(X.mean())
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Prepare target
    label_encoder = None
    if task_type == "classification":
        if y.dtype == 'object':
            label_encoder = LabelEncoder()
            y_encoded = label_encoder.fit_transform(y)
        else:
            y_encoded = y.values
    else:
        y_encoded = y.values
    
    return X_scaled, y_encoded, list(X.columns), label_encoder

def create_training_visualization(self, result: TrainingResult) -> str:
    """
    Create training visualization
    إنشاء تصور التدريب
    """
    try:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Plot loss
        axes[0].plot(result.training_history["train_loss"], label="Training Loss", color='blue')
        axes[0].plot(result.training_history["val_loss"], label="Validation Loss", color='red')
        axes[0].set_title("Training and Validation Loss")
        axes[0].set_xlabel("Epoch")
        axes[0].set_ylabel("Loss")
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot accuracy (if classification)
        if result.task_type == "classification" and "train_acc" in result.training_history:
            axes[1].plot(result.training_history["train_acc"], label="Training Accuracy", color='blue')
            axes[1].plot(result.training_history["val_acc"], label="Validation Accuracy", color='red')
            axes[1].set_title("Training and Validation Accuracy")
            axes[1].set_xlabel("Epoch")
            axes[1].set_ylabel("Accuracy (%)")
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
        else:
            axes[1].text(0.5, 0.5, "Accuracy plot not available\nfor regression tasks", 
                        ha='center', va='center', transform=axes[1].transAxes)
            axes[1].set_title("Accuracy Plot")
        
        plt.tight_layout()
        
        # Save plot
        plot_filename = f"training_{result.model_name}.png"
        plot_path = self.plots_path / plot_filename
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(plot_path)
        
    except Exception as e:
        logger.error(f"Training visualization failed: {str(e)}")
        return ""

def _save_training_result(self, result: TrainingResult):
    """
    Save training result to file
    حفظ نتيجة التدريب في ملف
    """
    try:
        result_file = self.results_path / f"{result.model_name}.json"
        
        result_dict = {
            'model_name': result.model_name,
            'task_type': result.task_type,
            'final_accuracy': result.final_accuracy,
            'final_loss': result.final_loss,
            'training_history': result.training_history,
            'model_path': result.model_path,
            'feature_names': result.feature_names,
            'training_time': result.training_time,
            'created_at': result.created_at
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        logger.error(f"Failed to save training result: {str(e)}")

def get_training_statistics(self) -> Dict[str, Any]:
    """
    Get deep learning training statistics
    الحصول على إحصائيات تدريب التعلم العميق
    """
    if not self.training_history:
        return {
            'total_models_trained': 0,
            'average_training_time': 0,
            'task_types': []
        }
    
    training_times = [item.get('training_time', 0) for item in self.training_history]
    task_types = [item.get('task_type', 'unknown') for item in self.training_history]
    
    from collections import Counter
    task_counts = Counter(task_types)
    
    # Calculate average accuracy for classification models
    classification_accuracies = [
        item.get('final_accuracy', 0) for item in self.training_history 
        if item.get('task_type') == 'classification' and item.get('final_accuracy')
    ]
    
    return {
        'total_models_trained': len(self.training_history),
        'average_training_time': sum(training_times) / len(training_times),
        'total_training_time': sum(training_times),
        'task_distribution': dict(task_counts),
        'average_classification_accuracy': sum(classification_accuracies) / len(classification_accuracies) if classification_accuracies else 0,
        'device_used': str(self.device),
        'generated_at': datetime.utcnow().isoformat()
    }

# Add methods to the main class
AdvancedDeepLearningEngine.train_neural_network = train_neural_network
AdvancedDeepLearningEngine._prepare_tabular_data = _prepare_tabular_data
AdvancedDeepLearningEngine.create_training_visualization = create_training_visualization
AdvancedDeepLearningEngine._save_training_result = _save_training_result
AdvancedDeepLearningEngine.get_training_statistics = get_training_statistics
