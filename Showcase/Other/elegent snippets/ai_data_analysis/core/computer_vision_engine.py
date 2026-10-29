# Service ID: AIQ36 - Computer Vision and Image Processing Engine
# محرك الرؤية الحاسوبية ومعالجة الصور المتقدم

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass
import json
import base64
from io import BytesIO

# Deep learning imports
import torch
import torchvision.transforms as transforms
from torchvision import models
import tensorflow as tf
from tensorflow.keras.applications import VGG16, ResNet50, InceptionV3
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.imagenet_utils import decode_predictions

# Face detection and recognition
import face_recognition
import mediapipe as mp

# OCR
import pytesseract
import easyocr

logger = logging.getLogger(__name__)

@dataclass
class ImageProcessingConfig:
    """
    Image processing configuration
    تكوين معالجة الصور
    """
    resize_dimensions: Tuple[int, int] = None
    enhance_contrast: bool = False
    enhance_brightness: float = 1.0
    enhance_sharpness: float = 1.0
    apply_filters: List[str] = None
    convert_grayscale: bool = False
    noise_reduction: bool = False

@dataclass
class DetectionConfig:
    """
    Object detection configuration
    تكوين اكتشاف الكائنات
    """
    model_type: str = "yolo"  # yolo, ssd, rcnn
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.4
    target_classes: List[str] = None
    draw_boxes: bool = True
    save_results: bool = True

@dataclass
class AnalysisResult:
    """
    Image analysis result container
    حاوي نتائج تحليل الصور
    """
    image_id: str
    original_path: str
    processed_path: str = None
    image_properties: Dict[str, Any] = None
    detected_objects: List[Dict[str, Any]] = None
    faces_detected: List[Dict[str, Any]] = None
    text_extracted: str = None
    classification_results: List[Dict[str, Any]] = None
    quality_metrics: Dict[str, float] = None
    processed_at: str = None

class AdvancedComputerVisionEngine:
    """
    Advanced computer vision and image processing engine
    محرك الرؤية الحاسوبية ومعالجة الصور المتقدم
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.processed_images_path = workspace_path / "processed_images"
        self.results_path = workspace_path / "cv_results"
        self.models_path = workspace_path / "cv_models"
        
        for path in [self.processed_images_path, self.results_path, self.models_path]:
            path.mkdir(exist_ok=True)
        
        self.analysis_history: List[Dict[str, Any]] = []
        self.loaded_models: Dict[str, Any] = {}
        
        # Initialize models and processors
        self._initialize_models()
    
    def _initialize_models(self):
        """
        Initialize computer vision models
        تهيئة نماذج الرؤية الحاسوبية
        """
        try:
            # Load pre-trained classification models
            self.classification_models = {
                'resnet50': ResNet50(weights='imagenet'),
                'vgg16': VGG16(weights='imagenet'),
                'inception_v3': InceptionV3(weights='imagenet')
            }
            
            # Initialize MediaPipe for face detection
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_drawing = mp.solutions.drawing_utils
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )
            
            # Initialize EasyOCR
            self.ocr_reader = easyocr.Reader(['en', 'ar'])  # English and Arabic
            
            # Load YOLO model for object detection
            try:
                self.yolo_net = cv2.dnn.readNet(
                    str(self.models_path / "yolov4.weights"),
                    str(self.models_path / "yolov4.cfg")
                )
                
                with open(self.models_path / "coco.names", "r") as f:
                    self.yolo_classes = [line.strip() for line in f.readlines()]
                    
            except FileNotFoundError:
                logger.warning("YOLO model files not found. Object detection will use alternative methods.")
                self.yolo_net = None
                self.yolo_classes = []
            
            logger.info("Computer vision models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize CV models: {str(e)}")
            raise
    
    def process_image(self, image_path: str, config: ImageProcessingConfig) -> Dict[str, Any]:
        """
        Process image with various enhancement techniques
        معالجة الصورة بتقنيات تحسين مختلفة
        """
        processing_start = datetime.utcnow()
        image_id = f"img_{int(processing_start.timestamp())}"
        
        try:
            # Load image
            original_image = Image.open(image_path)
            processed_image = original_image.copy()
            
            # Get original properties
            original_properties = {
                'width': original_image.width,
                'height': original_image.height,
                'mode': original_image.mode,
                'format': original_image.format,
                'size_bytes': Path(image_path).stat().st_size
            }
            
            # Apply processing steps
            if config.resize_dimensions:
                processed_image = processed_image.resize(config.resize_dimensions, Image.Resampling.LANCZOS)
            
            if config.enhance_contrast:
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.5)
            
            if config.enhance_brightness != 1.0:
                enhancer = ImageEnhance.Brightness(processed_image)
                processed_image = enhancer.enhance(config.enhance_brightness)
            
            if config.enhance_sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(processed_image)
                processed_image = enhancer.enhance(config.enhance_sharpness)
            
            if config.apply_filters:
                for filter_name in config.apply_filters:
                    if filter_name == "blur":
                        processed_image = processed_image.filter(ImageFilter.BLUR)
                    elif filter_name == "sharpen":
                        processed_image = processed_image.filter(ImageFilter.SHARPEN)
                    elif filter_name == "edge_enhance":
                        processed_image = processed_image.filter(ImageFilter.EDGE_ENHANCE)
            
            if config.convert_grayscale:
                processed_image = processed_image.convert('L')
            
            if config.noise_reduction:
                # Convert to OpenCV format for noise reduction
                cv_image = cv2.cvtColor(np.array(processed_image), cv2.COLOR_RGB2BGR)
                cv_image = cv2.fastNlMeansDenoisingColored(cv_image, None, 10, 10, 7, 21)
                processed_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            # Save processed image
            processed_path = self.processed_images_path / f"{image_id}_processed.jpg"
            processed_image.save(processed_path, quality=95)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_image_quality(np.array(processed_image))
            
            processing_time = (datetime.utcnow() - processing_start).total_seconds()
            
            result = {
                'image_id': image_id,
                'original_path': image_path,
                'processed_path': str(processed_path),
                'original_properties': original_properties,
                'processed_properties': {
                    'width': processed_image.width,
                    'height': processed_image.height,
                    'mode': processed_image.mode,
                    'size_bytes': processed_path.stat().st_size
                },
                'quality_metrics': quality_metrics,
                'processing_time_seconds': processing_time,
                'processed_at': processing_start.isoformat()
            }
            
            logger.info(f"Image processed successfully: {image_id}")
            return result
            
        except Exception as e:
            logger.error(f"Image processing failed: {str(e)}")
            return {'error': str(e), 'image_id': image_id}
    
    def analyze_image(self, image_path: str, tasks: List[str] = None) -> AnalysisResult:
        """
        Comprehensive image analysis
        تحليل الصور الشامل
        """
        analysis_start = datetime.utcnow()
        image_id = f"analysis_{int(analysis_start.timestamp())}"
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Initialize result
            result = AnalysisResult(
                image_id=image_id,
                original_path=image_path,
                processed_at=analysis_start.isoformat()
            )
            
            # Get image properties
            result.image_properties = self._get_image_properties(image_path)
            
            # Perform requested analyses
            tasks = tasks or ["classification", "objects", "faces", "text", "quality"]
            
            if "classification" in tasks:
                result.classification_results = self._classify_image(image_path)
            
            if "objects" in tasks:
                result.detected_objects = self._detect_objects(image)
            
            if "faces" in tasks:
                result.faces_detected = self._detect_faces(image)
            
            if "text" in tasks:
                result.text_extracted = self._extract_text(image)
            
            if "quality" in tasks:
                result.quality_metrics = self._calculate_image_quality(image)
            
            # Save analysis result
            self._save_analysis_result(result)
            
            # Record in history
            self.analysis_history.append({
                'image_id': image_id,
                'image_path': image_path,
                'tasks_performed': tasks,
                'analysis_time': (datetime.utcnow() - analysis_start).total_seconds(),
                'processed_at': analysis_start.isoformat()
            })
            
            logger.info(f"Image analysis completed: {image_id}")
            return result
            
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            raise
    
    def _get_image_properties(self, image_path: str) -> Dict[str, Any]:
        """
        Extract basic image properties
        استخراج خصائص الصورة الأساسية
        """
        try:
            with Image.open(image_path) as img:
                properties = {
                    'width': img.width,
                    'height': img.height,
                    'mode': img.mode,
                    'format': img.format,
                    'size_bytes': Path(image_path).stat().st_size,
                    'aspect_ratio': img.width / img.height,
                    'total_pixels': img.width * img.height
                }
                
                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = img._getexif()
                    properties['exif'] = {k: v for k, v in exif_data.items() if isinstance(v, (str, int, float))}
                
                return properties
                
        except Exception as e:
            logger.error(f"Failed to get image properties: {str(e)}")
            return {}
    
    def _classify_image(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Classify image using pre-trained models
        تصنيف الصورة باستخدام النماذج المدربة مسبقاً
        """
        try:
            results = []
            
            # Preprocess image for classification
            img = image.load_img(image_path, target_size=(224, 224))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = tf.keras.applications.imagenet_utils.preprocess_input(img_array)
            
            # Classify with multiple models
            for model_name, model in self.classification_models.items():
                try:
                    predictions = model.predict(img_array)
                    decoded_predictions = decode_predictions(predictions, top=3)[0]
                    
                    model_results = []
                    for pred in decoded_predictions:
                        model_results.append({
                            'class_id': pred[0],
                            'class_name': pred[1],
                            'confidence': float(pred[2])
                        })
                    
                    results.append({
                        'model': model_name,
                        'predictions': model_results,
                        'top_prediction': model_results[0] if model_results else None
                    })
                    
                except Exception as e:
                    logger.warning(f"Classification failed for model {model_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Image classification failed: {str(e)}")
            return []
    
    def _detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect objects in image
        اكتشاف الكائنات في الصورة
        """
        try:
            objects = []
            
            if self.yolo_net is not None:
                # Use YOLO for object detection
                height, width = image.shape[:2]
                
                # Create blob from image
                blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
                self.yolo_net.setInput(blob)
                
                # Get detections
                layer_names = self.yolo_net.getLayerNames()
                output_layers = [layer_names[i[0] - 1] for i in self.yolo_net.getUnconnectedOutLayers()]
                outputs = self.yolo_net.forward(output_layers)
                
                # Process detections
                boxes = []
                confidences = []
                class_ids = []
                
                for output in outputs:
                    for detection in output:
                        scores = detection[5:]
                        class_id = np.argmax(scores)
                        confidence = scores[class_id]
                        
                        if confidence > 0.5:
                            center_x = int(detection[0] * width)
                            center_y = int(detection[1] * height)
                            w = int(detection[2] * width)
                            h = int(detection[3] * height)
                            
                            x = int(center_x - w / 2)
                            y = int(center_y - h / 2)
                            
                            boxes.append([x, y, w, h])
                            confidences.append(float(confidence))
                            class_ids.append(class_id)
                
                # Apply non-maximum suppression
                indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
                
                if len(indices) > 0:
                    for i in indices.flatten():
                        x, y, w, h = boxes[i]
                        class_name = self.yolo_classes[class_ids[i]] if class_ids[i] < len(self.yolo_classes) else "unknown"
                        
                        objects.append({
                            'class_name': class_name,
                            'confidence': confidences[i],
                            'bounding_box': {
                                'x': x,
                                'y': y,
                                'width': w,
                                'height': h
                            }
                        })
            
            else:
                # Fallback to basic contour detection
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(blurred, 50, 150)
                
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for i, contour in enumerate(contours):
                    area = cv2.contourArea(contour)
                    if area > 1000:  # Filter small contours
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        objects.append({
                            'class_name': f'object_{i}',
                            'confidence': 0.7,  # Default confidence for contour detection
                            'bounding_box': {
                                'x': x,
                                'y': y,
                                'width': w,
                                'height': h
                            },
                            'area': area
                        })
            
            return objects
            
        except Exception as e:
            logger.error(f"Object detection failed: {str(e)}")
            return []
    
    def _detect_faces(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in image
        اكتشاف الوجوه في الصورة
        """
        try:
            faces = []
            
            # Convert BGR to RGB for MediaPipe
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces using MediaPipe
            results = self.face_detection.process(rgb_image)
            
            if results.detections:
                height, width = image.shape[:2]
                
                for i, detection in enumerate(results.detections):
                    bbox = detection.location_data.relative_bounding_box
                    
                    # Convert relative coordinates to absolute
                    x = int(bbox.xmin * width)
                    y = int(bbox.ymin * height)
                    w = int(bbox.width * width)
                    h = int(bbox.height * height)
                    
                    faces.append({
                        'face_id': i,
                        'confidence': detection.score[0],
                        'bounding_box': {
                            'x': x,
                            'y': y,
                            'width': w,
                            'height': h
                        }
                    })
            
            # Also try face_recognition library for additional features
            try:
                face_locations = face_recognition.face_locations(rgb_image)
                face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                
                for i, (top, right, bottom, left) in enumerate(face_locations):
                    faces.append({
                        'face_id': f'fr_{i}',
                        'confidence': 0.9,  # face_recognition doesn't provide confidence
                        'bounding_box': {
                            'x': left,
                            'y': top,
                            'width': right - left,
                            'height': bottom - top
                        },
                        'encoding_available': True
                    })
                    
            except Exception as e:
                logger.warning(f"face_recognition failed: {str(e)}")
            
            return faces
            
        except Exception as e:
            logger.error(f"Face detection failed: {str(e)}")
            return []
    
    def _extract_text(self, image: np.ndarray) -> str:
        """
        Extract text from image using OCR
        استخراج النص من الصورة باستخدام OCR
        """
        try:
            extracted_texts = []
            
            # Use EasyOCR
            try:
                results = self.ocr_reader.readtext(image)
                easyocr_text = " ".join([result[1] for result in results if result[2] > 0.5])
                if easyocr_text.strip():
                    extracted_texts.append(f"EasyOCR: {easyocr_text}")
            except Exception as e:
                logger.warning(f"EasyOCR failed: {str(e)}")
            
            # Use Tesseract as fallback
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                tesseract_text = pytesseract.image_to_string(gray, lang='eng+ara')
                if tesseract_text.strip():
                    extracted_texts.append(f"Tesseract: {tesseract_text}")
            except Exception as e:
                logger.warning(f"Tesseract failed: {str(e)}")
            
            return "\n".join(extracted_texts) if extracted_texts else ""
            
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return ""
    
    def _calculate_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """
        Calculate image quality metrics
        حساب مقاييس جودة الصورة
        """
        try:
            # Convert to grayscale for some calculations
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Calculate sharpness (Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Calculate brightness (mean intensity)
            brightness = np.mean(gray)
            
            # Calculate contrast (standard deviation)
            contrast = np.std(gray)
            
            # Calculate noise level (using high-frequency components)
            kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            noise = np.mean(np.abs(cv2.filter2D(gray, -1, kernel)))
            
            # Calculate histogram entropy (measure of information content)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = hist.flatten()
            hist = hist / hist.sum()  # Normalize
            entropy = -np.sum(hist * np.log2(hist + 1e-10))
            
            return {
                'sharpness': float(sharpness),
                'brightness': float(brightness),
                'contrast': float(contrast),
                'noise_level': float(noise),
                'entropy': float(entropy),
                'overall_quality': float((sharpness / 1000 + contrast / 100 + entropy / 10) / 3)
            }
            
        except Exception as e:
            logger.error(f"Quality calculation failed: {str(e)}")
            return {}
    
    def batch_process_images(self, image_paths: List[str], config: ImageProcessingConfig) -> List[Dict[str, Any]]:
        """
        Process multiple images in batch
        معالجة عدة صور في دفعة واحدة
        """
        results = []
        
        for i, image_path in enumerate(image_paths):
            try:
                result = self.process_image(image_path, config)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(image_paths)} images")
                    
            except Exception as e:
                logger.error(f"Failed to process image {image_path}: {str(e)}")
                results.append({'error': str(e), 'image_path': image_path})
        
        logger.info(f"Batch processing completed: {len(results)} images processed")
        return results
    
    def compare_images(self, image1_path: str, image2_path: str) -> Dict[str, Any]:
        """
        Compare two images for similarity
        مقارنة صورتين للتشابه
        """
        try:
            # Load images
            img1 = cv2.imread(image1_path)
            img2 = cv2.imread(image2_path)
            
            if img1 is None or img2 is None:
                raise ValueError("Could not load one or both images")
            
            # Resize images to same size for comparison
            height, width = 256, 256
            img1_resized = cv2.resize(img1, (width, height))
            img2_resized = cv2.resize(img2, (width, height))
            
            # Calculate histogram similarity
            hist1 = cv2.calcHist([img1_resized], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            hist2 = cv2.calcHist([img2_resized], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            
            hist_similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            
            # Calculate structural similarity (SSIM)
            from skimage.metrics import structural_similarity as ssim
            
            gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
            
            ssim_score = ssim(gray1, gray2)
            
            # Calculate mean squared error
            mse = np.mean((gray1 - gray2) ** 2)
            
            return {
                'image1_path': image1_path,
                'image2_path': image2_path,
                'histogram_similarity': float(hist_similarity),
                'structural_similarity': float(ssim_score),
                'mean_squared_error': float(mse),
                'overall_similarity': float((hist_similarity + ssim_score) / 2),
                'compared_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Image comparison failed: {str(e)}")
            return {'error': str(e)}
    
    def _save_analysis_result(self, result: AnalysisResult):
        """
        Save analysis result to file
        حفظ نتيجة التحليل في ملف
        """
        try:
            result_file = self.results_path / f"{result.image_id}.json"
            
            # Convert result to dictionary
            result_dict = {
                'image_id': result.image_id,
                'original_path': result.original_path,
                'processed_path': result.processed_path,
                'image_properties': result.image_properties,
                'detected_objects': result.detected_objects,
                'faces_detected': result.faces_detected,
                'text_extracted': result.text_extracted,
                'classification_results': result.classification_results,
                'quality_metrics': result.quality_metrics,
                'processed_at': result.processed_at
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save analysis result: {str(e)}")
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get computer vision processing statistics
        الحصول على إحصائيات معالجة الرؤية الحاسوبية
        """
        if not self.analysis_history:
            return {
                'total_analyses': 0,
                'average_processing_time': 0,
                'tasks_performed': []
            }
        
        processing_times = [item.get('analysis_time', 0) for item in self.analysis_history]
        all_tasks = []
        for item in self.analysis_history:
            all_tasks.extend(item.get('tasks_performed', []))
        
        from collections import Counter
        task_counts = Counter(all_tasks)
        
        return {
            'total_analyses': len(self.analysis_history),
            'average_processing_time': sum(processing_times) / len(processing_times),
            'total_processing_time': sum(processing_times),
            'tasks_distribution': dict(task_counts),
            'most_common_tasks': task_counts.most_common(5),
            'generated_at': datetime.utcnow().isoformat()
        }
