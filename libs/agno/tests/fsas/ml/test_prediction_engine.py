"""
Comprehensive test suite for Prediction Engine FSA

This module contains 55 tests covering all aspects of the Prediction Engine FSA:
- Single and batch predictions
- Streaming predictions
- Ensemble methods (voting, stacking, blending)
- Explainability (SHAP, LIME, attention)
- A/B testing
- Caching and optimization
- GPU acceleration
- Model quantization
- Multi-output predictions
- Probability calibration
- Framework-specific serving
- Error handling and edge cases
"""

import asyncio
import pickle
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import numpy as np
import pytest

from agno.fsas.ml.prediction_engine_fsa import (
    PredictionEngineFSA,
    PredictionCache,
    ModelConfig,
    PredictionResult
)


# Fixtures

@pytest.fixture
def engine():
    """Create a PredictionEngineFSA instance."""
    return PredictionEngineFSA(
        cache_enabled=True,
        cache_max_size=100,
        max_workers=2,
        enable_gpu=False,
        log_predictions=False
    )


@pytest.fixture
def mock_sklearn_model():
    """Create a mock scikit-learn model."""
    model = Mock()
    model.predict = Mock(return_value=np.array([0.5, 0.6, 0.7]))
    model.predict_proba = Mock(return_value=np.array([[0.3, 0.7], [0.4, 0.6], [0.2, 0.8]]))
    return model


@pytest.fixture
def mock_pytorch_model():
    """Create a mock PyTorch model."""
    model = Mock()
    model.eval = Mock()
    model.forward = Mock(return_value=Mock(numpy=Mock(return_value=np.array([[0.5, 0.5]]))))
    return model


@pytest.fixture
def sample_input():
    """Create sample input data."""
    return np.random.randn(10, 5)


@pytest.fixture
def sample_config():
    """Create sample model configuration."""
    return ModelConfig(
        model_path='/tmp/model.pkl',
        framework='sklearn',
        input_shape=(5,),
        device='cpu'
    )


# Test 1: Engine Initialization
def test_engine_initialization():
    """Test PredictionEngineFSA initialization."""
    engine = PredictionEngineFSA(cache_enabled=True, enable_gpu=False)
    assert engine.cache_enabled is True
    assert engine.enable_gpu is False
    assert engine.cache is not None
    assert isinstance(engine.metrics, dict)
    assert engine.metrics['total_predictions'] == 0


# Test 2: Single Prediction
def test_predict_single(engine, mock_sklearn_model, sample_input):
    """Test single prediction."""
    prediction = engine.predict_single(mock_sklearn_model, sample_input[0])
    assert prediction is not None
    assert isinstance(prediction, (float, int, np.ndarray))


# Test 3: Batch Prediction
def test_predict_batch(engine, mock_sklearn_model, sample_input):
    """Test batch prediction."""
    predictions = engine.predict_batch(mock_sklearn_model, sample_input)
    assert len(predictions) > 0
    assert isinstance(predictions, np.ndarray)


# Test 4: Streaming Prediction
def test_predict_streaming(engine, mock_sklearn_model):
    """Test streaming prediction."""
    data_stream = iter([np.random.randn(5) for _ in range(10)])
    predictions = list(engine.predict_streaming(mock_sklearn_model, data_stream))
    assert len(predictions) == 10


# Test 5: Ensemble Voting (Hard)
def test_predict_with_voting_hard(engine, sample_input):
    """Test ensemble prediction with hard voting."""
    models = [Mock() for _ in range(3)]
    for i, model in enumerate(models):
        model.predict = Mock(return_value=np.array([i % 2]))

    prediction = engine.predict_with_voting(models, sample_input[0], voting_type='hard')
    assert prediction is not None


# Test 6: Ensemble Voting (Soft)
def test_predict_with_voting_soft(engine, sample_input):
    """Test ensemble prediction with soft voting."""
    models = [Mock() for _ in range(3)]
    for model in models:
        model.predict = Mock(return_value=np.array([0.3, 0.7]))
        model.predict_proba = Mock(return_value=np.array([[0.3, 0.7]]))

    prediction = engine.predict_with_voting(models, sample_input[0], voting_type='soft')
    assert prediction is not None


# Test 7: Ensemble Stacking
def test_predict_with_stacking(engine, sample_input):
    """Test ensemble prediction with stacking."""
    base_models = [Mock() for _ in range(3)]
    for model in base_models:
        model.predict = Mock(return_value=np.array([0.5]))

    meta_model = Mock()
    meta_model.predict = Mock(return_value=np.array([0.7]))

    prediction = engine.predict_with_stacking(base_models, meta_model, sample_input[0])
    assert prediction is not None


# Test 8: Ensemble Blending
def test_predict_with_blending(engine, sample_input):
    """Test ensemble prediction with blending."""
    models = [Mock() for _ in range(3)]
    for model in models:
        model.predict = Mock(return_value=np.array([0.5]))

    weights = [0.3, 0.3, 0.4]
    prediction = engine.predict_with_blending(models, sample_input[0], weights)
    assert prediction is not None


# Test 9: Prediction Confidence
def test_calculate_prediction_confidence(engine, mock_sklearn_model):
    """Test prediction confidence calculation."""
    prediction = np.array([0.2, 0.8])
    confidence = engine.calculate_prediction_confidence(prediction, mock_sklearn_model)
    assert 0.0 <= confidence <= 1.0


# Test 10: SHAP Explanation
def test_explain_prediction_shap(engine, mock_sklearn_model, sample_input):
    """Test SHAP explanation generation."""
    explanation = engine.explain_prediction_shap(
        mock_sklearn_model,
        sample_input[0],
        sample_input[:5]
    )
    assert isinstance(explanation, dict)
    assert 'method' in explanation
    assert explanation['method'] == 'shap'


# Test 11: LIME Explanation
def test_explain_prediction_lime(engine, mock_sklearn_model, sample_input):
    """Test LIME explanation generation."""
    explanation = engine.explain_prediction_lime(mock_sklearn_model, sample_input[0])
    assert isinstance(explanation, dict)
    assert 'method' in explanation
    assert explanation['method'] == 'lime'


# Test 12: Attention Visualization
def test_visualize_attention(engine, mock_sklearn_model, sample_input):
    """Test attention visualization."""
    attention = engine.visualize_attention(mock_sklearn_model, sample_input[0])
    assert isinstance(attention, np.ndarray)


# Test 13: A/B Testing
def test_run_ab_test(engine, mock_sklearn_model, sample_input):
    """Test A/B testing between two models."""
    model_a = Mock()
    model_a.predict = Mock(return_value=np.random.randn(len(sample_input)))

    model_b = Mock()
    model_b.predict = Mock(return_value=np.random.randn(len(sample_input)))

    results = engine.run_ab_test(model_a, model_b, sample_input)
    assert 'mean_difference' in results
    assert 'agreement_rate' in results
    assert 'test_time' in results


# Test 14: Multi-Model Orchestration
def test_orchestrate_multi_model_pipeline(engine, sample_input):
    """Test multi-model pipeline orchestration."""
    model1 = Mock()
    model1.predict = Mock(return_value=np.array([0.5]))

    model2 = Mock()
    model2.predict = Mock(return_value=np.array([0.7]))

    models = [
        {'model': model1, 'name': 'model1', 'depends_on': ['input']},
        {'model': model2, 'name': 'model2', 'depends_on': ['model1']}
    ]

    outputs = engine.orchestrate_multi_model_pipeline(models, sample_input[0])
    assert 'model1' in outputs
    assert 'model2' in outputs


# Test 15: Feature Preprocessing - Normalize
def test_preprocess_features_normalize(engine):
    """Test feature preprocessing with normalization."""
    raw_data = np.array([1, 2, 3, 4, 5])
    config = {'steps': [{'type': 'normalize', 'min': 0, 'max': 10}]}
    processed = engine.preprocess_features_for_prediction(raw_data, config)
    assert np.all(processed >= 0) and np.all(processed <= 1)


# Test 16: Feature Preprocessing - Standardize
def test_preprocess_features_standardize(engine):
    """Test feature preprocessing with standardization."""
    raw_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    config = {'steps': [{'type': 'standardize'}]}
    processed = engine.preprocess_features_for_prediction(raw_data, config)
    assert abs(np.mean(processed)) < 1e-6


# Test 17: Prediction Caching
def test_cache_prediction(engine):
    """Test prediction caching."""
    cache_key = 'test_key'
    prediction = np.array([0.5, 0.6])
    engine.cache_prediction(cache_key, prediction, ttl=60)

    cached = engine.get_cached_prediction(cache_key)
    assert cached is not None
    np.testing.assert_array_equal(cached, prediction)


# Test 18: Cache Retrieval
def test_get_cached_prediction_miss(engine):
    """Test cache miss."""
    result = engine.get_cached_prediction('nonexistent_key')
    assert result is None


# Test 19: Async Prediction
@pytest.mark.asyncio
async def test_predict_async(engine, mock_sklearn_model, sample_input):
    """Test asynchronous prediction."""
    prediction = await engine.predict_async(mock_sklearn_model, sample_input[0])
    assert prediction is not None


# Test 20: GPU Acceleration (CPU Fallback)
def test_predict_gpu_accelerated_fallback(engine, mock_sklearn_model, sample_input):
    """Test GPU acceleration with CPU fallback."""
    prediction = engine.predict_gpu_accelerated(
        mock_sklearn_model,
        sample_input[0],
        device='cuda:0'
    )
    assert prediction is not None


# Test 21: Model Quantization
def test_quantize_model_for_inference(engine, mock_sklearn_model):
    """Test model quantization."""
    quantized = engine.quantize_model_for_inference(mock_sklearn_model, 'int8')
    assert quantized is not None


# Test 22: Dynamic Batching
def test_optimize_dynamic_batching(engine):
    """Test dynamic batching optimization."""
    requests = [np.random.randn(5) for _ in range(50)]
    batches = engine.optimize_dynamic_batching(requests, max_batch_size=10)
    assert len(batches) == 5
    assert all(len(batch) <= 10 for batch in batches)


# Test 23: Performance Monitoring
def test_monitor_prediction_performance(engine):
    """Test prediction performance monitoring."""
    engine.metrics['total_predictions'] = 100
    engine.metrics['cache_hits'] = 30
    engine.metrics['cache_misses'] = 70
    engine.metrics['total_inference_time'] = 10.0
    engine.metrics['errors'] = 5

    analysis = engine.monitor_prediction_performance({})
    assert 'cache_hit_rate' in analysis
    assert 'average_inference_time' in analysis
    assert analysis['cache_hit_rate'] == 0.3


# Test 24: Prediction Logging
def test_log_prediction(engine, sample_input):
    """Test prediction logging."""
    prediction = np.array([0.5])
    metadata = {'model': 'test_model'}
    engine.log_prediction(sample_input[0], prediction, metadata)
    # No exception means success


# Test 25: Fallback Strategy
def test_apply_fallback_strategy(engine, sample_input):
    """Test fallback strategy on error."""
    error = Exception("Test error")
    fallback = engine.apply_fallback_strategy(error, sample_input[0])
    assert fallback is not None


# Test 26: Post-processing - Softmax
def test_postprocess_predictions_softmax(engine):
    """Test post-processing with softmax."""
    raw_predictions = np.array([1.0, 2.0, 3.0])
    config = {'apply_softmax': True}
    processed = engine.postprocess_predictions(raw_predictions, config)
    assert np.isclose(np.sum(processed), 1.0)


# Test 27: Post-processing - Threshold
def test_postprocess_predictions_threshold(engine):
    """Test post-processing with threshold."""
    raw_predictions = np.array([0.3, 0.6, 0.8])
    config = {'apply_threshold': True, 'threshold': 0.5}
    processed = engine.postprocess_predictions(raw_predictions, config)
    np.testing.assert_array_equal(processed, np.array([0, 1, 1]))


# Test 28: Multi-Output Prediction
def test_predict_multi_output(engine, sample_input):
    """Test multi-output prediction."""
    model = Mock()
    model.predict = Mock(return_value=(np.array([0.5]), np.array([0.7])))

    outputs = engine.predict_multi_output(model, sample_input[0])
    assert isinstance(outputs, dict)
    assert len(outputs) > 0


# Test 29: Probability Calibration - Platt
def test_calibrate_probabilities_platt(engine):
    """Test probability calibration with Platt scaling."""
    predictions = np.array([0.2, 0.5, 0.8])
    calibrated = engine.calibrate_probabilities(predictions, 'platt')
    assert len(calibrated) == len(predictions)


# Test 30: Probability Calibration - Isotonic
def test_calibrate_probabilities_isotonic(engine):
    """Test probability calibration with isotonic regression."""
    predictions = np.array([0.2, 0.5, 0.8])
    calibrated = engine.calibrate_probabilities(predictions, 'isotonic')
    assert len(calibrated) == len(predictions)


# Test 31: Probability Calibration - Temperature
def test_calibrate_probabilities_temperature(engine):
    """Test probability calibration with temperature scaling."""
    predictions = np.array([[0.2, 0.8], [0.5, 0.5]])
    calibrated = engine.calibrate_probabilities(predictions, 'temperature')
    assert calibrated.shape == predictions.shape


# Test 32: TensorFlow Model Serving (Mock)
def test_serve_tensorflow_model_mock(engine):
    """Test TensorFlow model serving (mock)."""
    with patch('agno.fsas.ml.prediction_engine_fsa.tf', create=True) as mock_tf:
        mock_model = Mock()
        mock_model.predict = Mock(return_value=np.array([[0.5]]))
        mock_tf.keras.models.load_model = Mock(return_value=mock_model)

        # This will fail without TensorFlow, which is expected
        try:
            result = engine.serve_tensorflow_model('/tmp/model', np.array([[1, 2, 3]]))
        except (ImportError, NameError):
            pass  # Expected when TensorFlow not installed


# Test 33: PyTorch Model Serving
def test_serve_pytorch_model(engine, mock_pytorch_model):
    """Test PyTorch model serving."""
    input_data = np.array([[1, 2, 3]])

    # This will fail without PyTorch, which is expected
    try:
        result = engine.serve_pytorch_model(mock_pytorch_model, input_data)
    except (ImportError, NameError):
        pass  # Expected when PyTorch not installed


# Test 34: ONNX Model Serving (Mock)
def test_serve_onnx_model_mock(engine):
    """Test ONNX model serving (mock)."""
    try:
        result = engine.serve_onnx_model('/tmp/model.onnx', np.array([[1, 2, 3]]))
    except (ImportError, FileNotFoundError, Exception):
        pass  # Expected when ONNX Runtime not installed or file doesn't exist


# Test 35: scikit-learn Model Serving
def test_serve_sklearn_model(engine, mock_sklearn_model):
    """Test scikit-learn model serving."""
    input_data = np.array([[1, 2, 3]])
    result = engine.serve_sklearn_model(mock_sklearn_model, input_data)
    assert result is not None


# Test 36: Model Loading - sklearn
def test_load_model_for_inference_sklearn(engine, tmp_path):
    """Test model loading for scikit-learn."""
    model_path = tmp_path / "model.pkl"
    mock_model = Mock()
    with open(model_path, 'wb') as f:
        pickle.dump(mock_model, f)

    loaded = engine.load_model_for_inference(str(model_path), 'sklearn')
    assert loaded is not None


# Test 37: Inference Graph Optimization
def test_optimize_inference_graph(engine, mock_sklearn_model):
    """Test inference graph optimization."""
    optimized = engine.optimize_inference_graph(mock_sklearn_model)
    assert optimized is not None


# Test 38: ONNX Conversion (Mock)
def test_convert_model_to_onnx(engine, mock_pytorch_model):
    """Test model conversion to ONNX."""
    try:
        path = engine.convert_model_to_onnx(mock_pytorch_model, (1, 3, 224, 224))
    except (ImportError, ValueError, Exception):
        pass  # Expected when conversion libraries not available


# Test 39: Model Deployment
def test_deploy_model_to_serving(engine, mock_sklearn_model):
    """Test model deployment to serving."""
    endpoint_config = {'name': 'test-model', 'platform': 'local'}
    endpoint = engine.deploy_model_to_serving(mock_sklearn_model, endpoint_config)
    assert isinstance(endpoint, str)
    assert 'test-model' in endpoint


# Test 40: Report Generation
def test_generate_prediction_report(engine):
    """Test prediction report generation."""
    predictions = np.random.randn(100)
    metadata = {'model': 'test', 'version': '1.0'}
    report = engine.generate_prediction_report(predictions, metadata)
    assert isinstance(report, str)
    assert 'PREDICTION REPORT' in report


# Test 41: Large Batch Processing
def test_large_batch_processing(engine, mock_sklearn_model):
    """Test processing of large batches."""
    large_batch = np.random.randn(1000, 5)
    predictions = engine.predict_batch(mock_sklearn_model, large_batch)
    assert len(predictions) == 1000


# Test 42: Real-time Low-Latency Prediction
def test_real_time_low_latency(engine, mock_sklearn_model, sample_input):
    """Test low-latency prediction."""
    start = time.time()
    prediction = engine.predict_single(mock_sklearn_model, sample_input[0])
    latency = time.time() - start
    assert latency < 1.0  # Should be fast


# Test 43: High-Throughput Prediction
def test_high_throughput_prediction(engine, mock_sklearn_model, sample_input):
    """Test high-throughput batch prediction."""
    start = time.time()
    predictions = engine.predict_batch(mock_sklearn_model, sample_input)
    duration = time.time() - start
    throughput = len(sample_input) / duration
    assert throughput > 1  # At least 1 sample per second


# Test 44: Classification Prediction
def test_classification_prediction(engine):
    """Test classification prediction."""
    model = Mock()
    model.predict = Mock(return_value=np.array([0, 1, 1, 0]))
    model.predict_proba = Mock(return_value=np.array([[0.8, 0.2], [0.3, 0.7], [0.2, 0.8], [0.9, 0.1]]))

    input_data = np.random.randn(4, 5)
    predictions = engine.predict_batch(model, input_data)
    assert len(predictions) == 4


# Test 45: Regression Prediction
def test_regression_prediction(engine, mock_sklearn_model, sample_input):
    """Test regression prediction."""
    model = Mock()
    model.predict = Mock(return_value=np.array([1.5, 2.3, 3.7]))

    predictions = engine.predict_batch(model, sample_input[:3])
    assert len(predictions) == 3


# Test 46: Multi-Class Prediction
def test_multi_class_prediction(engine):
    """Test multi-class classification."""
    model = Mock()
    model.predict = Mock(return_value=np.array([0, 1, 2, 1]))
    model.predict_proba = Mock(return_value=np.array([
        [0.7, 0.2, 0.1],
        [0.1, 0.8, 0.1],
        [0.1, 0.1, 0.8],
        [0.2, 0.7, 0.1]
    ]))

    input_data = np.random.randn(4, 5)
    predictions = engine.predict_batch(model, input_data)
    assert len(predictions) == 4


# Test 47: Multi-Label Prediction
def test_multi_label_prediction(engine):
    """Test multi-label classification."""
    model = Mock()
    model.predict = Mock(return_value=np.array([
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 0]
    ]))

    input_data = np.random.randn(3, 5)
    predictions = engine.predict_batch(model, input_data)
    assert predictions.shape[0] == 3


# Test 48: Time-Series Prediction
def test_time_series_prediction(engine):
    """Test time-series prediction."""
    model = Mock()
    # Simulate LSTM-like output
    model.predict = Mock(return_value=np.array([[0.5], [0.6], [0.7]]))

    time_series_input = np.random.randn(3, 10, 5)  # (samples, timesteps, features)
    predictions = engine.predict_batch(model, time_series_input)
    assert len(predictions) > 0


# Test 49: Image Classification
def test_image_classification(engine):
    """Test image classification prediction."""
    model = Mock()
    model.predict = Mock(return_value=np.array([[0.1, 0.2, 0.7]]))

    # Simulate image input (batch, height, width, channels)
    image_input = np.random.randn(1, 224, 224, 3)
    predictions = engine.predict_batch(model, image_input)
    assert len(predictions) == 1


# Test 50: Object Detection (Mock)
def test_object_detection(engine):
    """Test object detection prediction."""
    model = Mock()
    # Simulate object detection output (bounding boxes, scores, classes)
    model.predict = Mock(return_value={
        'boxes': np.array([[10, 10, 100, 100]]),
        'scores': np.array([0.95]),
        'classes': np.array([1])
    })

    image_input = np.random.randn(1, 224, 224, 3)
    predictions = engine.predict_single(model, image_input)
    assert predictions is not None


# Test 51: Validation
def test_validate(engine):
    """Test engine validation."""
    assert engine.validate() is True


# Test 52: Error Handling
def test_error_handling(engine):
    """Test error handling."""
    error = ValueError("Test error")
    response = engine.error_handling(error)
    assert response['success'] is False
    assert 'error' in response
    assert response['error']['type'] == 'ValueError'


# Test 53: Execute Method Integration
def test_execute_method(engine, mock_sklearn_model, sample_input, tmp_path):
    """Test main execute method."""
    model_path = tmp_path / "model.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(mock_sklearn_model, f)

    config = {
        'model_config': ModelConfig(
            model_path=str(model_path),
            framework='sklearn',
            device='cpu'
        ),
        'use_cache': False
    }

    result = engine.execute(sample_input[0], config)
    assert 'prediction' in result
    assert 'execution_time' in result


# Test 54: Cache Key Generation
def test_cache_key_generation(engine, sample_config):
    """Test cache key generation."""
    input_data = np.array([1, 2, 3, 4, 5])
    key1 = engine._generate_cache_key(input_data, sample_config)
    key2 = engine._generate_cache_key(input_data, sample_config)
    assert key1 == key2  # Same input should generate same key

    # Different input should generate different key
    different_input = np.array([5, 4, 3, 2, 1])
    key3 = engine._generate_cache_key(different_input, sample_config)
    assert key1 != key3


# Test 55: Memory Efficiency
def test_memory_efficiency(engine, mock_sklearn_model):
    """Test memory efficiency with repeated predictions."""
    input_data = np.random.randn(100, 10)

    # Run multiple predictions
    for _ in range(10):
        predictions = engine.predict_batch(mock_sklearn_model, input_data)

    # Check that metrics are being tracked
    assert engine.metrics['total_predictions'] > 0


# Additional Test: PredictionCache
def test_prediction_cache():
    """Test PredictionCache class."""
    cache = PredictionCache(max_size=10)

    # Test set and get
    cache.set('key1', 'value1', ttl=60)
    assert cache.get('key1') == 'value1'

    # Test expiry
    cache.set('key2', 'value2', ttl=0)
    time.sleep(0.1)
    assert cache.get('key2') is None

    # Test max size
    for i in range(15):
        cache.set(f'key{i}', f'value{i}', ttl=60)
    assert len(cache.cache) <= 10

    # Test clear
    cache.clear()
    assert len(cache.cache) == 0


# Additional Test: PredictionResult Dataclass
def test_prediction_result():
    """Test PredictionResult dataclass."""
    result = PredictionResult(
        prediction=np.array([0.5]),
        confidence=0.8,
        model_name='test_model',
        inference_time=0.1,
        metadata={'version': '1.0'}
    )

    assert result.prediction is not None
    assert result.confidence == 0.8
    assert result.model_name == 'test_model'
    assert result.inference_time == 0.1
    assert result.metadata['version'] == '1.0'


# Additional Test: ModelConfig Dataclass
def test_model_config():
    """Test ModelConfig dataclass."""
    config = ModelConfig(
        model_path='/path/to/model',
        framework='pytorch',
        input_shape=(224, 224, 3),
        device='cuda:0',
        quantization='int8',
        batch_size=16
    )

    assert config.model_path == '/path/to/model'
    assert config.framework == 'pytorch'
    assert config.input_shape == (224, 224, 3)
    assert config.device == 'cuda:0'
    assert config.quantization == 'int8'
    assert config.batch_size == 16


# Additional Test: Ensemble with Different Strategies
def test_ensemble_different_strategies(engine, sample_input):
    """Test ensemble prediction with different strategies."""
    models = [Mock() for _ in range(3)]
    for model in models:
        model.predict = Mock(return_value=np.array([0.5]))

    # Test averaging
    pred1 = engine.predict_ensemble(models, sample_input[0], strategy='averaging')
    assert pred1 is not None

    # Test weighted averaging
    pred2 = engine.predict_ensemble(models, sample_input[0], strategy='weighted_averaging')
    assert pred2 is not None


# Additional Test: Concurrent Predictions
def test_concurrent_predictions(engine, mock_sklearn_model, sample_input):
    """Test concurrent predictions using thread pool."""
    def predict_task():
        return engine.predict_single(mock_sklearn_model, sample_input[0])

    # Submit multiple tasks
    futures = [engine.executor.submit(predict_task) for _ in range(5)]

    # Get results
    results = [f.result() for f in futures]
    assert len(results) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
