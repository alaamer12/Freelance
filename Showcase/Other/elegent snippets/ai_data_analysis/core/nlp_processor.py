# Service ID: AIQ47 - Natural Language Processing Engine
# محرك معالجة اللغة الطبيعية المتقدم

import nltk
import spacy
from transformers import pipeline, AutoTokenizer, AutoModel
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json
import re
from collections import Counter

from textblob import TextBlob
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

@dataclass
class NLPConfig:
    """
    NLP processing configuration
    تكوين معالجة اللغة الطبيعية
    """
    language: str = "en"
    model_name: str = "en_core_web_sm"
    tasks: List[str] = None  # sentiment, entities, topics, similarity
    preprocessing: Dict[str, bool] = None
    output_format: str = "json"

@dataclass
class TextAnalysisResult:
    """
    Text analysis result container
    حاوي نتائج تحليل النص
    """
    text_id: str
    original_text: str
    processed_text: str
    sentiment: Dict[str, Any] = None
    entities: List[Dict[str, Any]] = None
    keywords: List[str] = None
    topics: List[Dict[str, Any]] = None
    language_detected: str = None
    readability_score: float = None
    word_count: int = 0
    processed_at: str = None

class AdvancedNLPProcessor:
    """
    Advanced Natural Language Processing engine with multilingual support
    محرك معالجة اللغة الطبيعية المتقدم مع دعم متعدد اللغات
    """
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.models_path = workspace_path / "nlp_models"
        self.results_path = workspace_path / "nlp_results"
        self.wordclouds_path = workspace_path / "wordclouds"
        
        for path in [self.models_path, self.results_path, self.wordclouds_path]:
            path.mkdir(exist_ok=True)
        
        self.analysis_history: List[Dict[str, Any]] = []
        self.loaded_models: Dict[str, Any] = {}
        
        # Initialize NLP models
        self._initialize_models()
    
    def _initialize_models(self):
        """
        Initialize NLP models and pipelines
        تهيئة نماذج ومسارات معالجة اللغة الطبيعية
        """
        try:
            # Download required NLTK data
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('wordnet', quiet=True)
            
            # Initialize sentiment analysis pipeline
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            
            # Initialize NER pipeline
            self.ner_pipeline = pipeline(
                "ner",
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple"
            )
            
            # Initialize text classification pipeline
            self.classification_pipeline = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli"
            )
            
            # Initialize summarization pipeline
            self.summarization_pipeline = pipeline(
                "summarization",
                model="facebook/bart-large-cnn"
            )
            
            # Load spaCy model
            try:
                self.nlp_spacy = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp_spacy = None
            
            logger.info("NLP models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NLP models: {str(e)}")
            raise
    
    def analyze_text(self, text: str, config: NLPConfig) -> TextAnalysisResult:
        """
        Comprehensive text analysis
        تحليل النص الشامل
        """
        analysis_start = datetime.utcnow()
        text_id = f"text_{int(analysis_start.timestamp())}"
        
        try:
            # Preprocessing
            processed_text = self._preprocess_text(text, config.preprocessing or {})
            
            # Initialize result
            result = TextAnalysisResult(
                text_id=text_id,
                original_text=text,
                processed_text=processed_text,
                word_count=len(processed_text.split()),
                processed_at=analysis_start.isoformat()
            )
            
            # Language detection
            result.language_detected = self._detect_language(text)
            
            # Perform requested analyses
            tasks = config.tasks or ["sentiment", "entities", "keywords"]
            
            if "sentiment" in tasks:
                result.sentiment = self._analyze_sentiment(text)
            
            if "entities" in tasks:
                result.entities = self._extract_entities(text)
            
            if "keywords" in tasks:
                result.keywords = self._extract_keywords(processed_text)
            
            if "topics" in tasks:
                result.topics = self._extract_topics([processed_text])
            
            if "readability" in tasks:
                result.readability_score = self._calculate_readability(text)
            
            # Store analysis
            self._save_analysis_result(result)
            
            # Record in history
            self.analysis_history.append({
                'text_id': text_id,
                'text_length': len(text),
                'word_count': result.word_count,
                'language': result.language_detected,
                'tasks_performed': tasks,
                'processed_at': analysis_start.isoformat()
            })
            
            logger.info(f"Text analysis completed: {text_id}")
            return result
            
        except Exception as e:
            logger.error(f"Text analysis failed: {str(e)}")
            raise
    
    def analyze_batch(self, texts: List[str], config: NLPConfig) -> List[TextAnalysisResult]:
        """
        Batch text analysis
        تحليل النصوص بالدفعات
        """
        results = []
        
        for i, text in enumerate(texts):
            try:
                result = self.analyze_text(text, config)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(texts)} texts")
                    
            except Exception as e:
                logger.error(f"Failed to analyze text {i}: {str(e)}")
                continue
        
        logger.info(f"Batch analysis completed: {len(results)}/{len(texts)} successful")
        return results
    
    def _preprocess_text(self, text: str, preprocessing_config: Dict[str, bool]) -> str:
        """
        Preprocess text based on configuration
        معالجة النص مسبقاً بناءً على التكوين
        """
        processed = text
        
        # Convert to lowercase
        if preprocessing_config.get('lowercase', True):
            processed = processed.lower()
        
        # Remove URLs
        if preprocessing_config.get('remove_urls', True):
            processed = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', processed)
        
        # Remove mentions and hashtags
        if preprocessing_config.get('remove_mentions', True):
            processed = re.sub(r'@\w+', '', processed)
            processed = re.sub(r'#\w+', '', processed)
        
        # Remove special characters
        if preprocessing_config.get('remove_special_chars', True):
            processed = re.sub(r'[^a-zA-Z0-9\s]', '', processed)
        
        # Remove extra whitespace
        processed = re.sub(r'\s+', ' ', processed).strip()
        
        # Remove stopwords
        if preprocessing_config.get('remove_stopwords', False):
            from nltk.corpus import stopwords
            stop_words = set(stopwords.words('english'))
            words = processed.split()
            processed = ' '.join([word for word in words if word not in stop_words])
        
        return processed
    
    def _detect_language(self, text: str) -> str:
        """
        Detect text language
        اكتشاف لغة النص
        """
        try:
            from langdetect import detect
            return detect(text)
        except:
            # Fallback to TextBlob
            try:
                blob = TextBlob(text)
                return blob.detect_language()
            except:
                return "unknown"
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze text sentiment
        تحليل مشاعر النص
        """
        try:
            # Use Transformers pipeline
            result = self.sentiment_pipeline(text[:512])  # Limit text length
            
            # Also use TextBlob for comparison
            blob = TextBlob(text)
            textblob_sentiment = {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
            
            return {
                'transformers_result': result[0],
                'textblob_result': textblob_sentiment,
                'confidence': result[0]['score'],
                'label': result[0]['label']
            }
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {'error': str(e)}
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text
        استخراج الكيانات المسماة من النص
        """
        entities = []
        
        try:
            # Use Transformers NER pipeline
            ner_results = self.ner_pipeline(text)
            
            for entity in ner_results:
                entities.append({
                    'text': entity['word'],
                    'label': entity['entity_group'],
                    'confidence': entity['score'],
                    'start': entity.get('start', 0),
                    'end': entity.get('end', 0)
                })
            
            # Also use spaCy if available
            if self.nlp_spacy:
                doc = self.nlp_spacy(text)
                
                for ent in doc.ents:
                    entities.append({
                        'text': ent.text,
                        'label': ent.label_,
                        'description': spacy.explain(ent.label_),
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'source': 'spacy'
                    })
            
            return entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return []
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords using TF-IDF
        استخراج الكلمات المفتاحية باستخدام TF-IDF
        """
        try:
            # Use TF-IDF for keyword extraction
            vectorizer = TfidfVectorizer(
                max_features=max_keywords,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Get top keywords
            keyword_scores = list(zip(feature_names, tfidf_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [keyword for keyword, score in keyword_scores if score > 0]
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {str(e)}")
            return []
    
    def _extract_topics(self, texts: List[str], n_topics: int = 5) -> List[Dict[str, Any]]:
        """
        Extract topics using LDA
        استخراج المواضيع باستخدام LDA
        """
        try:
            if len(texts) < 2:
                return []
            
            # Vectorize texts
            vectorizer = CountVectorizer(
                max_features=100,
                stop_words='english',
                min_df=1,
                max_df=0.8
            )
            
            doc_term_matrix = vectorizer.fit_transform(texts)
            
            # Apply LDA
            lda = LatentDirichletAllocation(
                n_components=min(n_topics, len(texts)),
                random_state=42
            )
            
            lda.fit(doc_term_matrix)
            
            # Extract topics
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            
            for topic_idx, topic in enumerate(lda.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                
                topics.append({
                    'topic_id': topic_idx,
                    'words': top_words,
                    'weights': [topic[i] for i in top_words_idx]
                })
            
            return topics
            
        except Exception as e:
            logger.error(f"Topic extraction failed: {str(e)}")
            return []
    
    def _calculate_readability(self, text: str) -> float:
        """
        Calculate text readability score
        حساب درجة قابلية قراءة النص
        """
        try:
            # Simple readability calculation based on sentence and word length
            sentences = text.split('.')
            words = text.split()
            
            if len(sentences) == 0 or len(words) == 0:
                return 0.0
            
            avg_sentence_length = len(words) / len(sentences)
            avg_word_length = sum(len(word) for word in words) / len(words)
            
            # Flesch Reading Ease approximation
            readability = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_word_length / 4.7)
            
            return max(0, min(100, readability))
            
        except Exception as e:
            logger.error(f"Readability calculation failed: {str(e)}")
            return 0.0
    
    def generate_summary(self, text: str, max_length: int = 150) -> Dict[str, Any]:
        """
        Generate text summary
        إنشاء ملخص النص
        """
        try:
            # Use transformers summarization pipeline
            summary_result = self.summarization_pipeline(
                text,
                max_length=max_length,
                min_length=30,
                do_sample=False
            )
            
            summary_text = summary_result[0]['summary_text']
            
            # Calculate compression ratio
            compression_ratio = len(summary_text) / len(text)
            
            return {
                'original_length': len(text),
                'summary_length': len(summary_text),
                'compression_ratio': compression_ratio,
                'summary': summary_text,
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Text summarization failed: {str(e)}")
            return {'error': str(e)}
    
    def calculate_similarity(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        Calculate text similarity
        حساب تشابه النصوص
        """
        try:
            # Use TF-IDF vectorization
            vectorizer = TfidfVectorizer()
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            similarity_score = similarity_matrix[0][1]
            
            # Also calculate using TextBlob
            blob1 = TextBlob(text1)
            blob2 = TextBlob(text2)
            
            # Simple word overlap similarity
            words1 = set(blob1.words.lower())
            words2 = set(blob2.words.lower())
            
            jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
            
            return {
                'cosine_similarity': float(similarity_score),
                'jaccard_similarity': float(jaccard_similarity),
                'text1_length': len(text1),
                'text2_length': len(text2),
                'common_words': len(words1.intersection(words2)),
                'calculated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return {'error': str(e)}
    
    def generate_wordcloud(self, text: str, title: str = "Word Cloud") -> Dict[str, Any]:
        """
        Generate word cloud visualization
        إنشاء تصور سحابة الكلمات
        """
        try:
            # Create word cloud
            wordcloud = WordCloud(
                width=800,
                height=400,
                background_color='white',
                max_words=100,
                colormap='viridis'
            ).generate(text)
            
            # Save word cloud
            timestamp = int(datetime.utcnow().timestamp())
            filename = f"wordcloud_{timestamp}.png"
            filepath = self.wordclouds_path / filename
            
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.title(title, fontsize=16, fontweight='bold')
            plt.tight_layout(pad=0)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            plt.close()
            
            return {
                'filename': filename,
                'filepath': str(filepath),
                'file_size_kb': round(filepath.stat().st_size / 1024, 2),
                'word_count': len(text.split()),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Word cloud generation failed: {str(e)}")
            return {'error': str(e)}
    
    def classify_text(self, text: str, candidate_labels: List[str]) -> Dict[str, Any]:
        """
        Classify text into categories
        تصنيف النص إلى فئات
        """
        try:
            result = self.classification_pipeline(text, candidate_labels)
            
            return {
                'text_length': len(text),
                'candidate_labels': candidate_labels,
                'predictions': [
                    {
                        'label': label,
                        'score': score
                    }
                    for label, score in zip(result['labels'], result['scores'])
                ],
                'top_prediction': {
                    'label': result['labels'][0],
                    'confidence': result['scores'][0]
                },
                'classified_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Text classification failed: {str(e)}")
            return {'error': str(e)}
    
    def _save_analysis_result(self, result: TextAnalysisResult):
        """
        Save analysis result to file
        حفظ نتيجة التحليل في ملف
        """
        try:
            result_file = self.results_path / f"{result.text_id}.json"
            
            # Convert result to dictionary
            result_dict = {
                'text_id': result.text_id,
                'original_text': result.original_text[:500] + "..." if len(result.original_text) > 500 else result.original_text,
                'processed_text': result.processed_text,
                'sentiment': result.sentiment,
                'entities': result.entities,
                'keywords': result.keywords,
                'topics': result.topics,
                'language_detected': result.language_detected,
                'readability_score': result.readability_score,
                'word_count': result.word_count,
                'processed_at': result.processed_at
            }
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save analysis result: {str(e)}")
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get NLP processing statistics
        الحصول على إحصائيات معالجة اللغة الطبيعية
        """
        if not self.analysis_history:
            return {
                'total_analyses': 0,
                'languages_processed': [],
                'average_text_length': 0
            }
        
        languages = [item.get('language', 'unknown') for item in self.analysis_history]
        text_lengths = [item.get('text_length', 0) for item in self.analysis_history]
        
        return {
            'total_analyses': len(self.analysis_history),
            'languages_processed': list(set(languages)),
            'language_distribution': dict(Counter(languages)),
            'average_text_length': sum(text_lengths) / len(text_lengths),
            'total_words_processed': sum(item.get('word_count', 0) for item in self.analysis_history),
            'generated_at': datetime.utcnow().isoformat()
        }
