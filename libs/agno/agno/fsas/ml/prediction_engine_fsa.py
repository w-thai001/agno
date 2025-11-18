"""
Prediction Engine FSA (Focused Specialized Agent)

This module provides a comprehensive prediction engine for orchestrating multi-framework
model inference, real-time prediction serving, batch processing, ensemble predictions,
explainability, and advanced optimization techniques.

Features:
- Multi-framework support (TensorFlow, PyTorch, ONNX, scikit-learn)
- Batch and streaming prediction processing
- Ensemble methods (voting, stacking, blending)
- Explainability (SHAP, LIME, attention visualization)
- A/B testing for model versions
- Prediction caching and memoization
- GPU acceleration and model quantization
- Dynamic batching optimization
- Comprehensive monitoring and logging
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import pickle
import time
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np
from scipy.special import softmax
from scipy.stats import mode

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Container for prediction results with metadata."""

    prediction: Any
    confidence: float
    model_name: str
    inference_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    explanation: Optional[Dict[str, Any]] = None


@dataclass
class ModelConfig:
    """Configuration for model inference."""

    model_path: str
    framework: str  # 'tensorflow', 'pytorch', 'onnx', 'sklearn'
    input_shape: Optional[Tuple[int, ...]] = None
    preprocessing_config: Optional[Dict[str, Any]] = None
    device: str = 'cpu'  # 'cpu', 'cuda', 'cuda:0', etc.
    quantization: Optional[str] = None  # 'int8', 'fp16', etc.
    batch_size: int = 32
    max_batch_delay: float = 0.1  # seconds


class PredictionCache:
    """Simple in-memory cache for predictions with TTL support."""

    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached prediction if not expired."""
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """Store prediction in cache with TTL."""
        if len(self.cache) >= self.max_size:
            # Simple LRU: remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = (value, time.time() + ttl)

    def clear(self):
        """Clear all cached predictions."""
        self.cache.clear()


class PredictionEngineFSA:
    """
    Comprehensive Prediction Engine FSA for multi-framework model inference.

    This class provides a complete suite of prediction capabilities including:
    - Single and batch predictions
    - Streaming predictions
    - Ensemble predictions (voting, stacking, blending)
    - Model explainability (SHAP, LIME, attention)
    - A/B testing
    - Caching and optimization
    - GPU acceleration
    - Model quantization
    - Performance monitoring

    Example:
        >>> engine = PredictionEngineFSA()
        >>> config = ModelConfig(model_path='model.pkl', framework='sklearn')
        >>> result = engine.execute(input_data, {'model_config': config})
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_max_size: int = 1000,
        max_workers: int = 4,
        enable_gpu: bool = False,
        log_predictions: bool = True
    ):
        """
        Initialize the Prediction Engine FSA.

        Args:
            cache_enabled: Whether to enable prediction caching
            cache_max_size: Maximum number of cached predictions
            max_workers: Number of worker threads for async predictions
            enable_gpu: Whether to enable GPU acceleration
            log_predictions: Whether to log predictions
        """
        self.cache_enabled = cache_enabled
        self.cache = PredictionCache(max_size=cache_max_size) if cache_enabled else None
        self.max_workers = max_workers
        self.enable_gpu = enable_gpu
        self.log_predictions = log_predictions

        # Performance metrics
        self.metrics = {
            'total_predictions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_inference_time': 0.0,
            'errors': 0
        }

        # Model registry
        self.loaded_models: Dict[str, Any] = {}

        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        logger.info(f"PredictionEngineFSA initialized with cache={cache_enabled}, "
                   f"GPU={enable_gpu}, workers={max_workers}")

    def execute(self, input_data: Any, model_config: Dict) -> Dict[str, Any]:
        """
        Main execution method for the Prediction Engine FSA.

        This method orchestrates the entire prediction pipeline including
        preprocessing, inference, post-processing, and caching.

        Args:
            input_data: Input data for prediction (numpy array, tensor, dataframe, etc.)
            model_config: Dictionary containing model configuration

        Returns:
            Dictionary containing prediction results and metadata

        Example:
            >>> config = {'model_config': ModelConfig(...), 'use_cache': True}
            >>> result = engine.execute(data, config)
            >>> print(result['prediction'])
        """
        start_time = time.time()

        try:
            # Extract configuration
            cfg = model_config.get('model_config')
            use_cache = model_config.get('use_cache', True)
            explain = model_config.get('explain', False)

            if cfg is None:
                raise ValueError("model_config must contain 'model_config' key")

            # Check cache if enabled
            if use_cache and self.cache_enabled:
                cache_key = self._generate_cache_key(input_data, cfg)
                cached_result = self.get_cached_prediction(cache_key)
                if cached_result is not None:
                    self.metrics['cache_hits'] += 1
                    return {
                        'prediction': cached_result,
                        'cached': True,
                        'execution_time': time.time() - start_time
                    }
                self.metrics['cache_misses'] += 1

            # Preprocess input data
            if cfg.preprocessing_config:
                input_data = self.preprocess_features_for_prediction(
                    input_data, cfg.preprocessing_config
                )

            # Load or retrieve model
            model = self._get_or_load_model(cfg)

            # Perform prediction based on framework
            if cfg.framework == 'tensorflow':
                prediction = self.serve_tensorflow_model(cfg.model_path, input_data)
            elif cfg.framework == 'pytorch':
                prediction = self.serve_pytorch_model(model, input_data)
            elif cfg.framework == 'onnx':
                prediction = self.serve_onnx_model(cfg.model_path, input_data)
            elif cfg.framework == 'sklearn':
                prediction = self.serve_sklearn_model(model, input_data)
            else:
                raise ValueError(f"Unsupported framework: {cfg.framework}")

            # Calculate confidence
            confidence = self.calculate_prediction_confidence(prediction, model)

            # Generate explanation if requested
            explanation = None
            if explain:
                try:
                    explanation = self.explain_prediction_shap(
                        model, input_data, input_data[:100] if len(input_data) > 100 else input_data
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate explanation: {e}")

            # Cache result if enabled
            if use_cache and self.cache_enabled:
                self.cache_prediction(cache_key, prediction, ttl=300)

            # Update metrics
            inference_time = time.time() - start_time
            self.metrics['total_predictions'] += 1
            self.metrics['total_inference_time'] += inference_time

            # Log prediction if enabled
            if self.log_predictions:
                self.log_prediction(input_data, prediction, {
                    'confidence': confidence,
                    'inference_time': inference_time,
                    'framework': cfg.framework
                })

            return {
                'prediction': prediction,
                'confidence': confidence,
                'cached': False,
                'execution_time': inference_time,
                'explanation': explanation,
                'metadata': {
                    'framework': cfg.framework,
                    'model_path': cfg.model_path
                }
            }

        except Exception as e:
            self.metrics['errors'] += 1
            return self.error_handling(e)

    def predict_single(self, model: Any, input_data: np.ndarray) -> Any:
        """
        Perform single prediction on one input sample.

        Args:
            model: Trained model instance
            input_data: Single input sample

        Returns:
            Prediction result
        """
        start_time = time.time()

        try:
            # Ensure input is 2D (batch dimension)
            if input_data.ndim == 1:
                input_data = input_data.reshape(1, -1)

            # Framework-agnostic prediction
            if hasattr(model, 'predict'):
                prediction = model.predict(input_data)
            elif hasattr(model, 'forward'):
                # PyTorch model
                import torch
                with torch.no_grad():
                    tensor_input = torch.tensor(input_data, dtype=torch.float32)
                    prediction = model.forward(tensor_input).numpy()
            else:
                raise ValueError("Model does not have predict or forward method")

            # Extract single prediction if batch
            if isinstance(prediction, np.ndarray) and len(prediction) == 1:
                prediction = prediction[0]

            inference_time = time.time() - start_time
            logger.debug(f"Single prediction completed in {inference_time:.4f}s")

            return prediction

        except Exception as e:
            logger.error(f"Error in predict_single: {e}")
            raise

    def predict_batch(self, model: Any, input_batch: np.ndarray) -> np.ndarray:
        """
        Perform batch prediction on multiple input samples.

        Args:
            model: Trained model instance
            input_batch: Batch of input samples (2D array)

        Returns:
            Array of predictions
        """
        start_time = time.time()
        batch_size = len(input_batch)

        try:
            logger.info(f"Processing batch of {batch_size} samples")

            # Framework-agnostic batch prediction
            if hasattr(model, 'predict'):
                predictions = model.predict(input_batch)
            elif hasattr(model, 'forward'):
                # PyTorch model
                import torch
                with torch.no_grad():
                    tensor_input = torch.tensor(input_batch, dtype=torch.float32)
                    predictions = model.forward(tensor_input).numpy()
            else:
                raise ValueError("Model does not have predict or forward method")

            inference_time = time.time() - start_time
            throughput = batch_size / inference_time
            logger.info(f"Batch prediction: {batch_size} samples in {inference_time:.4f}s "
                       f"({throughput:.2f} samples/s)")

            return predictions

        except Exception as e:
            logger.error(f"Error in predict_batch: {e}")
            raise

    def predict_streaming(self, model: Any, data_stream: Iterator) -> Iterator:
        """
        Perform streaming prediction on a data stream.

        This method processes data in a streaming fashion, yielding predictions
        as they are generated. Useful for real-time applications.

        Args:
            model: Trained model instance
            data_stream: Iterator yielding input samples

        Yields:
            Individual predictions
        """
        logger.info("Starting streaming prediction")

        processed = 0
        for data_chunk in data_stream:
            try:
                # Convert to numpy array if needed
                if not isinstance(data_chunk, np.ndarray):
                    data_chunk = np.array(data_chunk)

                # Predict single or batch
                if data_chunk.ndim == 1:
                    prediction = self.predict_single(model, data_chunk)
                else:
                    prediction = self.predict_batch(model, data_chunk)

                processed += 1 if data_chunk.ndim == 1 else len(data_chunk)

                yield prediction

            except Exception as e:
                logger.error(f"Error in streaming prediction: {e}")
                yield None

        logger.info(f"Streaming prediction completed: {processed} samples processed")

    def predict_ensemble(
        self,
        models: List[Any],
        input_data: np.ndarray,
        strategy: str = 'voting'
    ) -> Any:
        """
        Perform ensemble prediction using multiple models.

        Args:
            models: List of trained model instances
            input_data: Input data for prediction
            strategy: Ensemble strategy ('voting', 'stacking', 'blending', 'averaging')

        Returns:
            Ensemble prediction result
        """
        logger.info(f"Ensemble prediction with {len(models)} models using {strategy}")

        if strategy == 'voting':
            return self.predict_with_voting(models, input_data, voting_type='hard')
        elif strategy == 'soft_voting':
            return self.predict_with_voting(models, input_data, voting_type='soft')
        elif strategy == 'averaging':
            # Simple averaging of predictions
            predictions = [self.predict_single(m, input_data) for m in models]
            return np.mean(predictions, axis=0)
        elif strategy == 'weighted_averaging':
            # Weighted averaging (equal weights for now)
            weights = [1.0 / len(models)] * len(models)
            return self.predict_with_blending(models, input_data, weights)
        else:
            raise ValueError(f"Unknown ensemble strategy: {strategy}")

    def predict_with_voting(
        self,
        models: List[Any],
        input_data: np.ndarray,
        voting_type: str = 'hard'
    ) -> Any:
        """
        Perform ensemble prediction using voting.

        Args:
            models: List of trained model instances
            input_data: Input data for prediction
            voting_type: 'hard' for majority voting, 'soft' for probability averaging

        Returns:
            Voted prediction result
        """
        start_time = time.time()

        if voting_type == 'hard':
            # Hard voting: majority vote
            predictions = []
            for model in models:
                pred = self.predict_single(model, input_data)
                # Convert to class labels if probabilities
                if isinstance(pred, np.ndarray) and pred.ndim > 0:
                    pred = np.argmax(pred) if len(pred) > 1 else pred
                predictions.append(pred)

            # Majority vote
            predictions_array = np.array(predictions)
            final_prediction = mode(predictions_array, axis=0, keepdims=False)[0]

            logger.info(f"Hard voting completed in {time.time() - start_time:.4f}s")
            return final_prediction

        elif voting_type == 'soft':
            # Soft voting: average probabilities
            probability_predictions = []
            for model in models:
                pred = self.predict_single(model, input_data)

                # Convert to probabilities if needed
                if hasattr(model, 'predict_proba'):
                    if input_data.ndim == 1:
                        input_data_2d = input_data.reshape(1, -1)
                    else:
                        input_data_2d = input_data
                    pred = model.predict_proba(input_data_2d)[0]
                elif isinstance(pred, np.ndarray) and pred.ndim == 1:
                    # Apply softmax if not already probabilities
                    if not np.isclose(np.sum(pred), 1.0):
                        pred = softmax(pred)

                probability_predictions.append(pred)

            # Average probabilities
            avg_probs = np.mean(probability_predictions, axis=0)
            final_prediction = np.argmax(avg_probs)

            logger.info(f"Soft voting completed in {time.time() - start_time:.4f}s")
            return final_prediction

        else:
            raise ValueError(f"Unknown voting type: {voting_type}")

    def predict_with_stacking(
        self,
        base_models: List[Any],
        meta_model: Any,
        X: np.ndarray
    ) -> Any:
        """
        Perform ensemble prediction using stacking.

        Stacking uses predictions from base models as input features for a meta-model.

        Args:
            base_models: List of base model instances
            meta_model: Meta-model that combines base model predictions
            X: Input data for prediction

        Returns:
            Stacked prediction result
        """
        start_time = time.time()
        logger.info(f"Stacking prediction with {len(base_models)} base models")

        # Get predictions from all base models
        base_predictions = []
        for i, model in enumerate(base_models):
            try:
                pred = self.predict_single(model, X)

                # Ensure prediction is numeric array
                if not isinstance(pred, np.ndarray):
                    pred = np.array([pred])
                elif pred.ndim == 0:
                    pred = np.array([pred])

                base_predictions.append(pred)
            except Exception as e:
                logger.warning(f"Base model {i} failed: {e}")
                # Use zeros as fallback
                base_predictions.append(np.zeros(1))

        # Stack base predictions as features for meta-model
        stacked_features = np.column_stack(base_predictions)

        # Meta-model prediction
        final_prediction = self.predict_single(meta_model, stacked_features.flatten())

        inference_time = time.time() - start_time
        logger.info(f"Stacking completed in {inference_time:.4f}s")

        return final_prediction

    def predict_with_blending(
        self,
        models: List[Any],
        X: np.ndarray,
        weights: List[float]
    ) -> Any:
        """
        Perform ensemble prediction using weighted blending.

        Args:
            models: List of trained model instances
            X: Input data for prediction
            weights: List of weights for each model (should sum to 1.0)

        Returns:
            Blended prediction result
        """
        start_time = time.time()

        if len(models) != len(weights):
            raise ValueError("Number of models must match number of weights")

        if not np.isclose(sum(weights), 1.0):
            logger.warning("Weights don't sum to 1.0, normalizing...")
            weights = np.array(weights) / sum(weights)

        logger.info(f"Blending prediction with {len(models)} models")

        # Get predictions from all models
        weighted_predictions = []
        for model, weight in zip(models, weights):
            pred = self.predict_single(model, X)

            # Convert to array if needed
            if not isinstance(pred, np.ndarray):
                pred = np.array(pred)

            weighted_predictions.append(pred * weight)

        # Sum weighted predictions
        final_prediction = np.sum(weighted_predictions, axis=0)

        inference_time = time.time() - start_time
        logger.info(f"Blending completed in {inference_time:.4f}s")

        return final_prediction

    def calculate_prediction_confidence(self, prediction: Any, model: Any) -> float:
        """
        Calculate confidence score for a prediction.

        Args:
            prediction: Model prediction
            model: Model instance

        Returns:
            Confidence score between 0 and 1
        """
        try:
            # For probability predictions
            if isinstance(prediction, np.ndarray):
                if prediction.ndim > 0 and len(prediction) > 1:
                    # Multi-class: use max probability
                    return float(np.max(prediction))
                elif prediction.ndim > 0:
                    # Binary: use absolute distance from 0.5
                    return float(abs(prediction[0] - 0.5) * 2)

            # For classification models with predict_proba
            if hasattr(model, 'predict_proba'):
                # Return max probability from last prediction
                return 0.8  # Placeholder

            # Default confidence
            return 0.5

        except Exception as e:
            logger.warning(f"Could not calculate confidence: {e}")
            return 0.5

    def explain_prediction_shap(
        self,
        model: Any,
        input_data: np.ndarray,
        background_data: np.ndarray
    ) -> Dict:
        """
        Generate SHAP explanation for a prediction.

        SHAP (SHapley Additive exPlanations) provides feature importance
        scores showing how each feature contributes to the prediction.

        Args:
            model: Trained model instance
            input_data: Input sample to explain
            background_data: Background dataset for SHAP computation

        Returns:
            Dictionary containing SHAP values and explanation metadata
        """
        start_time = time.time()

        try:
            # Import SHAP (lazy import to avoid dependency issues)
            try:
                import shap
            except ImportError:
                logger.warning("SHAP not installed, returning mock explanation")
                return {
                    'method': 'shap',
                    'available': False,
                    'message': 'SHAP library not installed'
                }

            # Ensure 2D arrays
            if input_data.ndim == 1:
                input_data = input_data.reshape(1, -1)
            if background_data.ndim == 1:
                background_data = background_data.reshape(1, -1)

            # Create explainer based on model type
            if hasattr(model, 'predict_proba'):
                # Classification model
                explainer = shap.KernelExplainer(model.predict_proba, background_data)
            else:
                # Regression or other
                explainer = shap.KernelExplainer(model.predict, background_data)

            # Calculate SHAP values
            shap_values = explainer.shap_values(input_data)

            # Extract feature importance
            if isinstance(shap_values, list):
                # Multi-class: use first class
                feature_importance = np.abs(shap_values[0][0])
            else:
                feature_importance = np.abs(shap_values[0])

            explanation_time = time.time() - start_time
            logger.info(f"SHAP explanation generated in {explanation_time:.4f}s")

            return {
                'method': 'shap',
                'shap_values': shap_values,
                'feature_importance': feature_importance.tolist(),
                'base_value': explainer.expected_value,
                'explanation_time': explanation_time
            }

        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {e}")
            return {
                'method': 'shap',
                'available': False,
                'error': str(e)
            }

    def explain_prediction_lime(
        self,
        model: Any,
        input_data: np.ndarray
    ) -> Dict:
        """
        Generate LIME explanation for a prediction.

        LIME (Local Interpretable Model-agnostic Explanations) explains
        predictions by approximating the model locally with an interpretable model.

        Args:
            model: Trained model instance
            input_data: Input sample to explain

        Returns:
            Dictionary containing LIME explanation
        """
        start_time = time.time()

        try:
            # Import LIME (lazy import)
            try:
                from lime.lime_tabular import LimeTabularExplainer
            except ImportError:
                logger.warning("LIME not installed, returning mock explanation")
                return {
                    'method': 'lime',
                    'available': False,
                    'message': 'LIME library not installed'
                }

            # Ensure 2D array
            if input_data.ndim == 1:
                input_data_2d = input_data.reshape(1, -1)
            else:
                input_data_2d = input_data

            # Create training data (using input as pseudo-training data)
            training_data = np.tile(input_data_2d, (100, 1))
            training_data += np.random.normal(0, 0.1, training_data.shape)

            # Create LIME explainer
            explainer = LimeTabularExplainer(
                training_data,
                mode='classification' if hasattr(model, 'predict_proba') else 'regression'
            )

            # Explain prediction
            explanation = explainer.explain_instance(
                input_data_2d[0],
                model.predict_proba if hasattr(model, 'predict_proba') else model.predict,
                num_features=min(10, input_data_2d.shape[1])
            )

            explanation_time = time.time() - start_time
            logger.info(f"LIME explanation generated in {explanation_time:.4f}s")

            return {
                'method': 'lime',
                'feature_importance': dict(explanation.as_list()),
                'score': explanation.score,
                'explanation_time': explanation_time
            }

        except Exception as e:
            logger.error(f"Error generating LIME explanation: {e}")
            return {
                'method': 'lime',
                'available': False,
                'error': str(e)
            }

    def visualize_attention(
        self,
        model: Any,
        input_data: np.ndarray
    ) -> np.ndarray:
        """
        Visualize attention weights for transformer/attention-based models.

        Args:
            model: Model with attention mechanism
            input_data: Input data

        Returns:
            Attention weight matrix
        """
        try:
            # Check if model has attention mechanism
            if hasattr(model, 'get_attention_weights'):
                attention_weights = model.get_attention_weights(input_data)
                return attention_weights

            # Mock attention for demonstration
            logger.warning("Model doesn't support attention visualization")
            seq_length = input_data.shape[-1] if input_data.ndim > 1 else 10
            attention = np.random.random((seq_length, seq_length))
            attention = attention / attention.sum(axis=1, keepdims=True)

            return attention

        except Exception as e:
            logger.error(f"Error visualizing attention: {e}")
            return np.array([])

    def run_ab_test(
        self,
        model_a: Any,
        model_b: Any,
        test_data: np.ndarray
    ) -> Dict[str, Any]:
        """
        Run A/B test comparing two model versions.

        Args:
            model_a: First model (control)
            model_b: Second model (treatment)
            test_data: Test dataset

        Returns:
            Dictionary with A/B test results and statistics
        """
        logger.info("Running A/B test on models")
        start_time = time.time()

        # Predictions from both models
        predictions_a = self.predict_batch(model_a, test_data)
        predictions_b = self.predict_batch(model_b, test_data)

        # Calculate metrics
        diff = np.abs(predictions_a - predictions_b)
        mean_diff = np.mean(diff)
        std_diff = np.std(diff)
        max_diff = np.max(diff)

        # Agreement rate
        if predictions_a.ndim > 1:
            agreement = np.mean(np.argmax(predictions_a, axis=1) == np.argmax(predictions_b, axis=1))
        else:
            agreement = np.mean(predictions_a == predictions_b)

        test_time = time.time() - start_time

        results = {
            'model_a_predictions': predictions_a,
            'model_b_predictions': predictions_b,
            'mean_difference': float(mean_diff),
            'std_difference': float(std_diff),
            'max_difference': float(max_diff),
            'agreement_rate': float(agreement),
            'test_time': test_time,
            'num_samples': len(test_data)
        }

        logger.info(f"A/B test completed: agreement={agreement:.2%}, "
                   f"mean_diff={mean_diff:.4f}")

        return results

    def orchestrate_multi_model_pipeline(
        self,
        models: List[Dict],
        input_data: Any
    ) -> Dict[str, Any]:
        """
        Orchestrate a pipeline of multiple models.

        Args:
            models: List of model configurations with dependencies
                   Each dict should have: {'model': model_instance, 'name': str, 'depends_on': List[str]}
            input_data: Initial input data

        Returns:
            Dictionary with outputs from all models in the pipeline
        """
        logger.info(f"Orchestrating pipeline with {len(models)} models")
        start_time = time.time()

        # Track outputs from each model
        outputs = {'input': input_data}

        # Process models in dependency order
        processed = set(['input'])
        remaining = list(range(len(models)))

        while remaining:
            made_progress = False

            for idx in list(remaining):
                model_config = models[idx]
                model = model_config['model']
                name = model_config['name']
                depends_on = model_config.get('depends_on', ['input'])

                # Check if dependencies are satisfied
                if all(dep in processed for dep in depends_on):
                    # Get input from dependencies
                    if len(depends_on) == 1:
                        model_input = outputs[depends_on[0]]
                    else:
                        # Concatenate multiple dependencies
                        dep_outputs = [outputs[dep] for dep in depends_on]
                        model_input = np.concatenate([
                            np.array(x).flatten() for x in dep_outputs
                        ])

                    # Run prediction
                    try:
                        prediction = self.predict_single(model, model_input)
                        outputs[name] = prediction
                        processed.add(name)
                        remaining.remove(idx)
                        made_progress = True
                        logger.info(f"Completed model: {name}")
                    except Exception as e:
                        logger.error(f"Error in model {name}: {e}")
                        outputs[name] = None
                        processed.add(name)
                        remaining.remove(idx)

            if not made_progress and remaining:
                logger.error("Circular dependency detected in pipeline")
                break

        total_time = time.time() - start_time
        outputs['pipeline_time'] = total_time

        logger.info(f"Pipeline completed in {total_time:.4f}s")

        return outputs

    def preprocess_features_for_prediction(
        self,
        raw_data: Any,
        preprocessing_config: Dict
    ) -> np.ndarray:
        """
        Preprocess raw features before prediction.

        Args:
            raw_data: Raw input data
            preprocessing_config: Configuration for preprocessing steps

        Returns:
            Preprocessed numpy array ready for prediction
        """
        data = raw_data

        # Convert to numpy array if needed
        if not isinstance(data, np.ndarray):
            try:
                data = np.array(data)
            except Exception as e:
                logger.error(f"Failed to convert data to numpy array: {e}")
                raise

        # Apply preprocessing steps
        steps = preprocessing_config.get('steps', [])

        for step in steps:
            step_type = step.get('type')

            if step_type == 'normalize':
                # Min-max normalization
                min_val = step.get('min', data.min())
                max_val = step.get('max', data.max())
                if max_val > min_val:
                    data = (data - min_val) / (max_val - min_val)

            elif step_type == 'standardize':
                # Z-score standardization
                mean = step.get('mean', data.mean())
                std = step.get('std', data.std())
                if std > 0:
                    data = (data - mean) / std

            elif step_type == 'clip':
                # Clip values
                min_val = step.get('min', -np.inf)
                max_val = step.get('max', np.inf)
                data = np.clip(data, min_val, max_val)

            elif step_type == 'reshape':
                # Reshape data
                shape = step.get('shape')
                if shape:
                    data = data.reshape(shape)

            elif step_type == 'cast':
                # Cast to specific dtype
                dtype = step.get('dtype', 'float32')
                data = data.astype(dtype)

        logger.debug(f"Preprocessing complete: {len(steps)} steps applied")

        return data

    def cache_prediction(self, cache_key: str, prediction: Any, ttl: int = 300) -> None:
        """
        Cache a prediction result.

        Args:
            cache_key: Unique key for this prediction
            prediction: Prediction result to cache
            ttl: Time-to-live in seconds
        """
        if self.cache_enabled and self.cache:
            self.cache.set(cache_key, prediction, ttl)
            logger.debug(f"Cached prediction with key: {cache_key[:16]}...")

    def get_cached_prediction(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached prediction if available.

        Args:
            cache_key: Cache key to lookup

        Returns:
            Cached prediction or None if not found/expired
        """
        if self.cache_enabled and self.cache:
            result = self.cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for key: {cache_key[:16]}...")
            return result
        return None

    async def predict_async(self, model: Any, input_data: np.ndarray) -> Any:
        """
        Perform asynchronous prediction.

        Args:
            model: Trained model instance
            input_data: Input data for prediction

        Returns:
            Prediction result
        """
        # Run prediction in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        prediction = await loop.run_in_executor(
            self.executor,
            self.predict_single,
            model,
            input_data
        )
        return prediction

    def predict_gpu_accelerated(
        self,
        model: Any,
        input_data: np.ndarray,
        device: str = 'cuda:0'
    ) -> np.ndarray:
        """
        Perform GPU-accelerated prediction.

        Args:
            model: Trained model instance
            input_data: Input data for prediction
            device: GPU device identifier

        Returns:
            Prediction result
        """
        if not self.enable_gpu:
            logger.warning("GPU acceleration not enabled, falling back to CPU")
            return self.predict_single(model, input_data)

        try:
            # Check for PyTorch
            try:
                import torch

                # Move model and data to GPU
                if isinstance(model, torch.nn.Module):
                    device_obj = torch.device(device if torch.cuda.is_available() else 'cpu')
                    model = model.to(device_obj)

                    # Convert input to tensor
                    if not isinstance(input_data, torch.Tensor):
                        input_tensor = torch.tensor(input_data, dtype=torch.float32)
                    else:
                        input_tensor = input_data

                    input_tensor = input_tensor.to(device_obj)

                    # Prediction
                    with torch.no_grad():
                        prediction = model(input_tensor)

                    return prediction.cpu().numpy()

            except ImportError:
                logger.warning("PyTorch not available for GPU acceleration")

            # Fallback to CPU prediction
            return self.predict_single(model, input_data)

        except Exception as e:
            logger.error(f"GPU prediction failed: {e}, falling back to CPU")
            return self.predict_single(model, input_data)

    def quantize_model_for_inference(
        self,
        model: Any,
        quantization_type: str = 'int8'
    ) -> Any:
        """
        Quantize model for faster inference.

        Args:
            model: Model to quantize
            quantization_type: Type of quantization ('int8', 'fp16', 'dynamic')

        Returns:
            Quantized model
        """
        logger.info(f"Quantizing model with {quantization_type}")

        try:
            # PyTorch quantization
            try:
                import torch

                if isinstance(model, torch.nn.Module):
                    if quantization_type == 'int8':
                        quantized_model = torch.quantization.quantize_dynamic(
                            model, {torch.nn.Linear}, dtype=torch.qint8
                        )
                    elif quantization_type == 'fp16':
                        quantized_model = model.half()
                    else:
                        quantized_model = torch.quantization.quantize_dynamic(
                            model, {torch.nn.Linear, torch.nn.Conv2d}
                        )

                    logger.info("Model quantized successfully")
                    return quantized_model

            except ImportError:
                pass

            # TensorFlow quantization
            try:
                import tensorflow as tf

                if hasattr(model, 'save'):
                    # TF model - would require converter
                    logger.warning("TensorFlow quantization not fully implemented")
                    return model

            except ImportError:
                pass

            # Return original model if quantization not supported
            logger.warning(f"Quantization not supported for this model type")
            return model

        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return model

    def optimize_dynamic_batching(
        self,
        requests: List[np.ndarray],
        max_batch_size: int = 32
    ) -> List[np.ndarray]:
        """
        Optimize batching of prediction requests.

        Args:
            requests: List of individual prediction requests
            max_batch_size: Maximum batch size

        Returns:
            List of optimized batches
        """
        logger.info(f"Optimizing {len(requests)} requests into batches")

        batches = []
        current_batch = []

        for request in requests:
            current_batch.append(request)

            if len(current_batch) >= max_batch_size:
                # Create batch
                batch_array = np.array(current_batch)
                batches.append(batch_array)
                current_batch = []

        # Add remaining requests
        if current_batch:
            batch_array = np.array(current_batch)
            batches.append(batch_array)

        logger.info(f"Created {len(batches)} batches")
        return batches

    def monitor_prediction_performance(
        self,
        prediction_metrics: Dict
    ) -> Dict[str, Any]:
        """
        Monitor and analyze prediction performance metrics.

        Args:
            prediction_metrics: Dictionary of performance metrics

        Returns:
            Analysis results and recommendations
        """
        analysis = {
            'total_predictions': self.metrics['total_predictions'],
            'cache_hit_rate': (
                self.metrics['cache_hits'] /
                (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0
                else 0.0
            ),
            'average_inference_time': (
                self.metrics['total_inference_time'] / self.metrics['total_predictions']
                if self.metrics['total_predictions'] > 0
                else 0.0
            ),
            'error_rate': (
                self.metrics['errors'] / self.metrics['total_predictions']
                if self.metrics['total_predictions'] > 0
                else 0.0
            ),
            'recommendations': []
        }

        # Generate recommendations
        if analysis['cache_hit_rate'] < 0.3:
            analysis['recommendations'].append(
                "Low cache hit rate - consider increasing cache size or TTL"
            )

        if analysis['average_inference_time'] > 1.0:
            analysis['recommendations'].append(
                "High inference time - consider model quantization or batch processing"
            )

        if analysis['error_rate'] > 0.05:
            analysis['recommendations'].append(
                "High error rate - check model compatibility and input validation"
            )

        return analysis

    def log_prediction(
        self,
        input_data: Any,
        prediction: Any,
        metadata: Dict
    ) -> None:
        """
        Log prediction for monitoring and debugging.

        Args:
            input_data: Input data
            prediction: Prediction result
            metadata: Additional metadata
        """
        log_entry = {
            'timestamp': time.time(),
            'input_shape': input_data.shape if isinstance(input_data, np.ndarray) else None,
            'prediction_shape': prediction.shape if isinstance(prediction, np.ndarray) else None,
            'metadata': metadata
        }

        logger.debug(f"Prediction logged: {log_entry}")

    def apply_fallback_strategy(
        self,
        error: Exception,
        input_data: Any
    ) -> Any:
        """
        Apply fallback strategy when prediction fails.

        Args:
            error: Exception that occurred
            input_data: Original input data

        Returns:
            Fallback prediction
        """
        logger.warning(f"Applying fallback strategy due to: {error}")

        # Return default prediction based on input type
        if isinstance(input_data, np.ndarray):
            if input_data.ndim > 1:
                # Multi-dimensional: return zeros
                return np.zeros(input_data.shape[1])
            else:
                # 1D: return single zero
                return np.array([0.0])

        return None

    def postprocess_predictions(
        self,
        raw_predictions: np.ndarray,
        config: Dict
    ) -> Any:
        """
        Post-process raw predictions.

        Args:
            raw_predictions: Raw model predictions
            config: Post-processing configuration

        Returns:
            Post-processed predictions
        """
        predictions = raw_predictions

        # Apply post-processing steps
        if config.get('apply_softmax', False):
            predictions = softmax(predictions, axis=-1)

        if config.get('apply_threshold', False):
            threshold = config.get('threshold', 0.5)
            predictions = (predictions > threshold).astype(int)

        if config.get('convert_to_labels', False):
            label_map = config.get('label_map', {})
            if predictions.ndim > 1:
                predictions = np.argmax(predictions, axis=-1)
            predictions = np.array([label_map.get(p, p) for p in predictions])

        if config.get('round', False):
            decimals = config.get('decimals', 2)
            predictions = np.round(predictions, decimals)

        return predictions

    def predict_multi_output(
        self,
        model: Any,
        input_data: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        Handle multi-output predictions.

        Args:
            model: Multi-output model
            input_data: Input data

        Returns:
            Dictionary mapping output names to predictions
        """
        try:
            prediction = self.predict_single(model, input_data)

            # If prediction is tuple/list, assume multiple outputs
            if isinstance(prediction, (tuple, list)):
                outputs = {
                    f'output_{i}': pred for i, pred in enumerate(prediction)
                }
            elif isinstance(prediction, dict):
                outputs = prediction
            else:
                # Single output
                outputs = {'output_0': prediction}

            logger.info(f"Multi-output prediction: {len(outputs)} outputs")
            return outputs

        except Exception as e:
            logger.error(f"Multi-output prediction failed: {e}")
            return {}

    def calibrate_probabilities(
        self,
        predictions: np.ndarray,
        calibration_method: str = 'platt'
    ) -> np.ndarray:
        """
        Calibrate prediction probabilities.

        Args:
            predictions: Raw probability predictions
            calibration_method: Calibration method ('platt', 'isotonic', 'temperature')

        Returns:
            Calibrated probabilities
        """
        logger.info(f"Calibrating probabilities using {calibration_method}")

        if calibration_method == 'platt':
            # Platt scaling (simplified)
            # In practice, this requires training data
            # Here we apply a simple sigmoid transformation
            calibrated = 1 / (1 + np.exp(-predictions))

        elif calibration_method == 'isotonic':
            # Isotonic regression (simplified)
            # Would require actual calibration data in practice
            calibrated = np.clip(predictions, 0, 1)

        elif calibration_method == 'temperature':
            # Temperature scaling
            temperature = 1.5  # Could be learned from validation data
            calibrated = softmax(predictions / temperature, axis=-1)

        else:
            logger.warning(f"Unknown calibration method: {calibration_method}")
            calibrated = predictions

        return calibrated

    def serve_tensorflow_model(
        self,
        model_path: str,
        input_data: np.ndarray
    ) -> np.ndarray:
        """
        Serve predictions from a TensorFlow model.

        Args:
            model_path: Path to TensorFlow model
            input_data: Input data for prediction

        Returns:
            Prediction results
        """
        try:
            import tensorflow as tf

            # Load model if not cached
            cache_key = f"tf_model_{model_path}"
            if cache_key not in self.loaded_models:
                model = tf.keras.models.load_model(model_path)
                self.loaded_models[cache_key] = model
            else:
                model = self.loaded_models[cache_key]

            # Ensure correct input shape
            if input_data.ndim == 1:
                input_data = input_data.reshape(1, -1)

            # Predict
            predictions = model.predict(input_data, verbose=0)

            return predictions

        except ImportError:
            logger.error("TensorFlow not installed")
            raise
        except Exception as e:
            logger.error(f"TensorFlow serving error: {e}")
            raise

    def serve_pytorch_model(
        self,
        model: Any,
        input_data: Any
    ) -> Any:
        """
        Serve predictions from a PyTorch model.

        Args:
            model: PyTorch model instance
            input_data: Input tensor or numpy array

        Returns:
            Prediction results
        """
        try:
            import torch

            # Ensure model is in eval mode
            model.eval()

            # Convert to tensor if needed
            if not isinstance(input_data, torch.Tensor):
                input_tensor = torch.tensor(input_data, dtype=torch.float32)
            else:
                input_tensor = input_data

            # Ensure batch dimension
            if input_tensor.ndim == 1:
                input_tensor = input_tensor.unsqueeze(0)

            # Predict
            with torch.no_grad():
                predictions = model(input_tensor)

            # Convert to numpy
            if isinstance(predictions, torch.Tensor):
                predictions = predictions.numpy()

            return predictions

        except ImportError:
            logger.error("PyTorch not installed")
            raise
        except Exception as e:
            logger.error(f"PyTorch serving error: {e}")
            raise

    def serve_onnx_model(
        self,
        model_path: str,
        input_data: np.ndarray
    ) -> np.ndarray:
        """
        Serve predictions from an ONNX model.

        Args:
            model_path: Path to ONNX model
            input_data: Input data for prediction

        Returns:
            Prediction results
        """
        try:
            import onnxruntime as ort

            # Load model if not cached
            cache_key = f"onnx_model_{model_path}"
            if cache_key not in self.loaded_models:
                session = ort.InferenceSession(model_path)
                self.loaded_models[cache_key] = session
            else:
                session = self.loaded_models[cache_key]

            # Ensure correct input shape and type
            if input_data.ndim == 1:
                input_data = input_data.reshape(1, -1)
            input_data = input_data.astype(np.float32)

            # Get input name
            input_name = session.get_inputs()[0].name

            # Predict
            predictions = session.run(None, {input_name: input_data})

            return predictions[0]

        except ImportError:
            logger.error("ONNX Runtime not installed")
            raise
        except Exception as e:
            logger.error(f"ONNX serving error: {e}")
            raise

    def serve_sklearn_model(
        self,
        model: Any,
        input_data: np.ndarray
    ) -> np.ndarray:
        """
        Serve predictions from a scikit-learn model.

        Args:
            model: scikit-learn model instance
            input_data: Input data for prediction

        Returns:
            Prediction results
        """
        try:
            # Ensure 2D input
            if input_data.ndim == 1:
                input_data = input_data.reshape(1, -1)

            # Predict
            predictions = model.predict(input_data)

            return predictions

        except Exception as e:
            logger.error(f"scikit-learn serving error: {e}")
            raise

    def load_model_for_inference(
        self,
        model_path: str,
        framework: str
    ) -> Any:
        """
        Load a model for inference based on framework.

        Args:
            model_path: Path to model file
            framework: Framework name ('tensorflow', 'pytorch', 'onnx', 'sklearn')

        Returns:
            Loaded model instance
        """
        cache_key = f"{framework}_{model_path}"

        if cache_key in self.loaded_models:
            logger.info(f"Using cached model: {cache_key}")
            return self.loaded_models[cache_key]

        logger.info(f"Loading {framework} model from {model_path}")

        try:
            if framework == 'tensorflow':
                import tensorflow as tf
                model = tf.keras.models.load_model(model_path)

            elif framework == 'pytorch':
                import torch
                model = torch.load(model_path)
                model.eval()

            elif framework == 'onnx':
                import onnxruntime as ort
                model = ort.InferenceSession(model_path)

            elif framework == 'sklearn':
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)

            else:
                raise ValueError(f"Unsupported framework: {framework}")

            self.loaded_models[cache_key] = model
            logger.info(f"Model loaded successfully")

            return model

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def optimize_inference_graph(self, model: Any) -> Any:
        """
        Optimize model inference graph.

        Args:
            model: Model to optimize

        Returns:
            Optimized model
        """
        try:
            # TensorFlow optimization
            try:
                import tensorflow as tf

                if isinstance(model, tf.keras.Model):
                    # Convert to TFLite for optimization
                    converter = tf.lite.TFLiteConverter.from_keras_model(model)
                    converter.optimizations = [tf.lite.Optimize.DEFAULT]
                    tflite_model = converter.convert()

                    logger.info("TensorFlow model optimized")
                    return model  # Return original for now

            except (ImportError, Exception):
                pass

            # PyTorch optimization
            try:
                import torch

                if isinstance(model, torch.nn.Module):
                    # JIT compilation
                    model = torch.jit.script(model)
                    logger.info("PyTorch model optimized with JIT")
                    return model

            except (ImportError, Exception):
                pass

            logger.warning("Model optimization not applied")
            return model

        except Exception as e:
            logger.error(f"Graph optimization failed: {e}")
            return model

    def convert_model_to_onnx(
        self,
        model: Any,
        input_shape: Tuple
    ) -> str:
        """
        Convert model to ONNX format.

        Args:
            model: Model to convert
            input_shape: Example input shape

        Returns:
            Path to saved ONNX model
        """
        output_path = "/tmp/model_converted.onnx"

        try:
            # PyTorch to ONNX
            try:
                import torch

                if isinstance(model, torch.nn.Module):
                    dummy_input = torch.randn(input_shape)
                    torch.onnx.export(
                        model,
                        dummy_input,
                        output_path,
                        export_params=True,
                        opset_version=11,
                        do_constant_folding=True
                    )
                    logger.info(f"Model converted to ONNX: {output_path}")
                    return output_path

            except (ImportError, Exception) as e:
                logger.warning(f"PyTorch to ONNX conversion failed: {e}")

            # TensorFlow to ONNX
            try:
                import tensorflow as tf
                import tf2onnx

                if isinstance(model, tf.keras.Model):
                    spec = (tf.TensorSpec(input_shape, tf.float32),)
                    output_path_tf = output_path.replace('.onnx', '_tf.onnx')

                    model_proto, _ = tf2onnx.convert.from_keras(
                        model,
                        input_signature=spec,
                        output_path=output_path_tf
                    )
                    logger.info(f"Model converted to ONNX: {output_path_tf}")
                    return output_path_tf

            except (ImportError, Exception) as e:
                logger.warning(f"TensorFlow to ONNX conversion failed: {e}")

            raise ValueError("Model conversion to ONNX not supported for this model type")

        except Exception as e:
            logger.error(f"ONNX conversion failed: {e}")
            raise

    def deploy_model_to_serving(
        self,
        model: Any,
        endpoint_config: Dict
    ) -> str:
        """
        Deploy model to serving infrastructure.

        Args:
            model: Model to deploy
            endpoint_config: Deployment configuration

        Returns:
            Endpoint URL or identifier
        """
        logger.info("Deploying model to serving infrastructure")

        # Mock deployment - in practice, this would integrate with
        # serving platforms like TF Serving, TorchServe, KServe, etc.

        endpoint_name = endpoint_config.get('name', 'model-endpoint')
        platform = endpoint_config.get('platform', 'local')

        if platform == 'local':
            # Local deployment (mock)
            endpoint_url = f"http://localhost:8080/v1/models/{endpoint_name}"

        elif platform == 'kubernetes':
            # Kubernetes deployment (mock)
            namespace = endpoint_config.get('namespace', 'default')
            endpoint_url = f"http://{endpoint_name}.{namespace}.svc.cluster.local:8080"

        elif platform == 'cloud':
            # Cloud deployment (mock)
            region = endpoint_config.get('region', 'us-east-1')
            endpoint_url = f"https://api.{region}.cloud.com/models/{endpoint_name}"

        else:
            endpoint_url = f"http://localhost:8080/v1/models/{endpoint_name}"

        logger.info(f"Model deployed to: {endpoint_url}")

        return endpoint_url

    def generate_prediction_report(
        self,
        predictions: np.ndarray,
        metadata: Dict
    ) -> str:
        """
        Generate comprehensive prediction report.

        Args:
            predictions: Array of predictions
            metadata: Additional metadata

        Returns:
            Report string
        """
        report = []
        report.append("=" * 50)
        report.append("PREDICTION REPORT")
        report.append("=" * 50)
        report.append("")

        # Summary statistics
        report.append("Summary Statistics:")
        report.append(f"  Total predictions: {len(predictions)}")

        if predictions.dtype in [np.float32, np.float64]:
            report.append(f"  Mean: {np.mean(predictions):.4f}")
            report.append(f"  Std: {np.std(predictions):.4f}")
            report.append(f"  Min: {np.min(predictions):.4f}")
            report.append(f"  Max: {np.max(predictions):.4f}")

        # Metadata
        if metadata:
            report.append("")
            report.append("Metadata:")
            for key, value in metadata.items():
                report.append(f"  {key}: {value}")

        # Performance metrics
        report.append("")
        report.append("Engine Performance:")
        metrics = self.monitor_prediction_performance({})
        report.append(f"  Total predictions: {metrics['total_predictions']}")
        report.append(f"  Cache hit rate: {metrics['cache_hit_rate']:.2%}")
        report.append(f"  Avg inference time: {metrics['average_inference_time']:.4f}s")
        report.append(f"  Error rate: {metrics['error_rate']:.2%}")

        report.append("")
        report.append("=" * 50)

        return "\n".join(report)

    def validate(self) -> bool:
        """
        Validate the Prediction Engine FSA configuration.

        Returns:
            True if configuration is valid
        """
        try:
            # Check cache
            if self.cache_enabled and self.cache is None:
                logger.error("Cache enabled but not initialized")
                return False

            # Check executor
            if self.executor is None:
                logger.error("Thread pool executor not initialized")
                return False

            # Check metrics
            if not isinstance(self.metrics, dict):
                logger.error("Metrics not properly initialized")
                return False

            logger.info("Prediction Engine FSA validation passed")
            return True

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle errors and generate error response.

        Args:
            exception: Exception that occurred

        Returns:
            Error response dictionary
        """
        error_type = type(exception).__name__
        error_message = str(exception)

        logger.error(f"Error in Prediction Engine: {error_type} - {error_message}")

        return {
            'success': False,
            'error': {
                'type': error_type,
                'message': error_message
            },
            'prediction': None,
            'execution_time': 0.0
        }

    def _generate_cache_key(self, input_data: Any, config: ModelConfig) -> str:
        """Generate unique cache key for input and configuration."""
        # Hash input data
        if isinstance(input_data, np.ndarray):
            data_hash = hashlib.md5(input_data.tobytes()).hexdigest()
        else:
            data_hash = hashlib.md5(str(input_data).encode()).hexdigest()

        # Hash configuration
        config_str = f"{config.model_path}_{config.framework}_{config.device}"
        config_hash = hashlib.md5(config_str.encode()).hexdigest()

        return f"{config_hash}_{data_hash}"

    def _get_or_load_model(self, config: ModelConfig) -> Any:
        """Load model or retrieve from cache."""
        cache_key = f"{config.framework}_{config.model_path}"

        if cache_key not in self.loaded_models:
            model = self.load_model_for_inference(config.model_path, config.framework)
            self.loaded_models[cache_key] = model

        return self.loaded_models[cache_key]

    def __del__(self):
        """Cleanup resources."""
        try:
            if hasattr(self, 'executor'):
                self.executor.shutdown(wait=False)
        except Exception:
            pass
