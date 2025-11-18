"""
Unit tests for Natural Language Processor FSA.

This module contains comprehensive tests for the NaturalLanguageProcessorFSA,
covering tokenization, sentiment analysis, entity extraction, intent classification,
error handling, and performance benchmarking.
"""

import time
from typing import Dict, List

import pytest

from agno.fsas.nlp.natural_language_processor_fsa import (
    NaturalLanguageProcessorFSA,
    NLPConfig,
)


@pytest.fixture
def fsa():
    """Create a NaturalLanguageProcessorFSA instance for testing."""
    config = NLPConfig()
    return NaturalLanguageProcessorFSA(config=config)


@pytest.fixture
def fsa_with_filters():
    """Create an FSA with text filtering enabled."""
    config = NLPConfig(
        remove_punctuation=True,
        remove_stopwords=True,
        lowercase=True
    )
    return NaturalLanguageProcessorFSA(config=config)


class TestTextTokenization:
    """Tests for text tokenization functionality."""

    def test_basic_tokenization(self, fsa):
        """Test basic tokenization of simple text."""
        text = "Hello, world! How are you?"
        tokens = fsa.tokenize(text)

        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert 'Hello' in tokens
        assert 'world' in tokens

    def test_tokenization_with_punctuation_removal(self, fsa_with_filters):
        """Test tokenization with punctuation removal."""
        text = "Hello, world!"
        tokens = fsa_with_filters.tokenize(text)

        assert ',' not in tokens
        assert '!' not in tokens
        assert 'hello' in tokens  # lowercase enabled
        assert 'world' in tokens

    def test_tokenization_with_stopwords_removal(self, fsa_with_filters):
        """Test tokenization with stopword removal."""
        text = "The quick brown fox jumps over the lazy dog"
        tokens = fsa_with_filters.tokenize(text)

        # Common stopwords should be removed
        assert 'the' not in tokens
        assert 'over' not in tokens

        # Content words should remain
        assert 'quick' in tokens
        assert 'fox' in tokens

    def test_empty_text_tokenization(self, fsa):
        """Test tokenization of empty text."""
        tokens = fsa.tokenize("")
        assert tokens == []

        tokens = fsa.tokenize("   ")
        assert tokens == []

    def test_tokenization_accuracy(self, fsa):
        """Test tokenization accuracy with known input."""
        text = "The cat sat on the mat."
        tokens = fsa.tokenize(text)

        expected_tokens = ['The', 'cat', 'sat', 'on', 'the', 'mat', '.']
        assert tokens == expected_tokens


class TestSentimentAnalysis:
    """Tests for sentiment analysis functionality."""

    def test_positive_sentiment(self, fsa):
        """Test detection of positive sentiment."""
        text = "I love this product! It's absolutely amazing and wonderful!"
        result = fsa.analyze_sentiment(text)

        assert result['polarity'] == 'positive'
        assert result['compound'] > 0
        assert result['positive'] > 0
        assert 'confidence' in result

    def test_negative_sentiment(self, fsa):
        """Test detection of negative sentiment."""
        text = "This is terrible. I hate it and it's completely awful."
        result = fsa.analyze_sentiment(text)

        assert result['polarity'] == 'negative'
        assert result['compound'] < 0
        assert result['negative'] > 0

    def test_neutral_sentiment(self, fsa):
        """Test detection of neutral sentiment."""
        text = "The product arrived on Tuesday."
        result = fsa.analyze_sentiment(text)

        assert result['polarity'] == 'neutral'
        assert abs(result['compound']) < 0.1

    def test_sentiment_validation(self, fsa):
        """Validate sentiment analysis output structure."""
        text = "This is a test."
        result = fsa.analyze_sentiment(text)

        required_keys = ['polarity', 'compound', 'positive', 'negative', 'neutral', 'confidence']
        for key in required_keys:
            assert key in result

        assert result['polarity'] in ['positive', 'negative', 'neutral']
        assert -1 <= result['compound'] <= 1
        assert 0 <= result['confidence'] <= 1

    def test_empty_text_sentiment(self, fsa):
        """Test sentiment analysis on empty text."""
        result = fsa.analyze_sentiment("")

        assert result['polarity'] == 'neutral'
        assert result['compound'] == 0.0


class TestEntityExtraction:
    """Tests for named entity recognition."""

    def test_entity_extraction_organizations(self, fsa):
        """Test extraction of organization entities."""
        text = "Apple Inc. and Microsoft are technology companies."
        entities = fsa.extract_entities(text)

        # Check if we got entities (exact results depend on spaCy model availability)
        assert isinstance(entities, list)

        # If spaCy is available, we should get entities
        if entities:
            entity_texts = [e['text'] for e in entities]
            # At least one company should be recognized
            assert any('Apple' in text or 'Microsoft' in text for text in entity_texts)

    def test_entity_extraction_locations(self, fsa):
        """Test extraction of location entities."""
        text = "New York is a city in the United States."
        entities = fsa.extract_entities(text)

        assert isinstance(entities, list)

    def test_entity_correctness(self, fsa):
        """Test correctness of entity extraction output structure."""
        text = "Barack Obama was born in Hawaii."
        entities = fsa.extract_entities(text)

        for entity in entities:
            assert 'text' in entity
            assert 'label' in entity
            assert 'start_pos' in entity
            assert 'end_pos' in entity
            assert isinstance(entity['text'], str)
            assert isinstance(entity['label'], str)

    def test_empty_text_entities(self, fsa):
        """Test entity extraction on empty text."""
        entities = fsa.extract_entities("")
        assert entities == []


class TestIntentClassification:
    """Tests for intent classification."""

    def test_question_intent(self, fsa):
        """Test classification of question intent."""
        text = "What is the weather today?"
        result = fsa.classify_intent(text)

        assert result['intent'] == 'question'
        assert result['confidence'] > 0

    def test_greeting_intent(self, fsa):
        """Test classification of greeting intent."""
        text = "Hello, how are you?"
        result = fsa.classify_intent(text)

        assert result['intent'] in ['greeting', 'question']
        assert 'confidence' in result

    def test_command_intent(self, fsa):
        """Test classification of command intent."""
        text = "Please create a new document."
        result = fsa.classify_intent(text)

        assert result['intent'] == 'command'
        assert result['confidence'] > 0

    def test_gratitude_intent(self, fsa):
        """Test classification of gratitude intent."""
        text = "Thank you so much for your help!"
        result = fsa.classify_intent(text)

        assert result['intent'] == 'gratitude'
        assert result['confidence'] > 0

    def test_intent_classification_structure(self, fsa):
        """Validate intent classification output structure."""
        text = "This is a test message."
        result = fsa.classify_intent(text)

        assert 'intent' in result
        assert 'confidence' in result
        assert 'all_intents' in result
        assert isinstance(result['all_intents'], dict)


class TestTextSummarization:
    """Tests for text summarization."""

    def test_basic_summarization(self, fsa):
        """Test basic text summarization."""
        text = """
        Natural language processing is a field of artificial intelligence.
        It focuses on the interaction between computers and human language.
        NLP is used in many applications today.
        These applications include chatbots and virtual assistants.
        Machine learning has greatly improved NLP capabilities.
        """
        summary = fsa.summarize(text, max_length=2)

        assert isinstance(summary, str)
        assert len(summary) > 0
        assert len(summary) < len(text)

    def test_summarization_length_control(self, fsa):
        """Test that summarization respects max_length parameter."""
        text = """
        Sentence one. Sentence two. Sentence three.
        Sentence four. Sentence five. Sentence six.
        """
        summary = fsa.summarize(text, max_length=2)

        # Count sentences in summary
        import nltk
        sentences = nltk.sent_tokenize(summary)
        assert len(sentences) <= 2

    def test_short_text_summarization(self, fsa):
        """Test summarization of very short text."""
        text = "This is a single sentence."
        summary = fsa.summarize(text)

        # Single sentence should return as-is or similar
        assert len(summary) > 0

    def test_empty_text_summarization(self, fsa):
        """Test summarization of empty text."""
        summary = fsa.summarize("")
        assert summary == ""


class TestLanguageDetection:
    """Tests for language detection."""

    def test_english_detection(self, fsa):
        """Test detection of English language."""
        text = "The quick brown fox jumps over the lazy dog."
        result = fsa.detect_language(text)

        assert 'language' in result
        assert 'confidence' in result
        # Should detect English or have low confidence
        assert result['language'] in ['en', 'unknown']

    def test_multiple_languages(self, fsa):
        """Test language detection with various inputs."""
        texts = {
            'en': "Hello, how are you?",
            'es': "Hola, ¿cómo estás?",
            'fr': "Bonjour, comment allez-vous?",
        }

        for lang, text in texts.items():
            result = fsa.detect_language(text)
            assert 'language' in result
            assert 'confidence' in result


class TestPOSTagging:
    """Tests for part-of-speech tagging."""

    def test_pos_tagging_basic(self, fsa):
        """Test basic POS tagging."""
        text = "The cat sat on the mat."
        tags = fsa.pos_tag(text)

        assert isinstance(tags, list)
        assert len(tags) > 0
        # Each tag should be a tuple
        assert all(isinstance(tag, tuple) and len(tag) == 2 for tag in tags)

    def test_pos_tagging_structure(self, fsa):
        """Test POS tagging output structure."""
        text = "Dogs bark loudly."
        tags = fsa.pos_tag(text)

        for word, tag in tags:
            assert isinstance(word, str)
            assert isinstance(tag, str)
            assert len(tag) > 0


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_error_handling_invalid_task(self, fsa):
        """Test error handling for invalid task."""
        result = fsa.execute("test", "invalid_task")

        assert result['success'] is False
        assert 'error' in result
        assert 'type' in result['error']

    def test_error_handling_excessive_length(self, fsa):
        """Test error handling for text exceeding max length."""
        long_text = "a " * (fsa.config.max_text_length + 1000)

        result = fsa.execute(long_text, "tokenize")
        assert result['success'] is False

    def test_validation_passes(self, fsa):
        """Test that FSA validation passes."""
        assert fsa.validate() is True

    def test_error_handling_structure(self, fsa):
        """Test error handling returns proper structure."""
        result = fsa.execute("", "invalid_task")

        assert 'success' in result
        assert 'error' in result
        assert 'type' in result['error']
        assert 'message' in result['error']


class TestExecuteMethod:
    """Tests for the main execute method."""

    def test_execute_tokenize(self, fsa):
        """Test execute method with tokenize task."""
        result = fsa.execute("Hello world", "tokenize")

        assert result['success'] is True
        assert result['task'] == 'tokenize'
        assert 'tokens' in result

    def test_execute_sentiment(self, fsa):
        """Test execute method with sentiment task."""
        result = fsa.execute("I love this!", "sentiment")

        assert result['success'] is True
        assert result['task'] == 'sentiment'
        assert 'sentiment' in result

    def test_execute_entities(self, fsa):
        """Test execute method with entities task."""
        result = fsa.execute("Apple is a company.", "entities")

        assert result['success'] is True
        assert result['task'] == 'entities'
        assert 'entities' in result

    def test_execute_caching(self, fsa):
        """Test that caching works for repeated executions."""
        text = "Test text for caching"

        # First execution
        result1 = fsa.execute(text, "tokenize")

        # Second execution (should use cache)
        result2 = fsa.execute(text, "tokenize")

        assert result1 == result2
        assert result1['success'] is True


class TestPerformance:
    """Performance benchmarking tests."""

    def test_tokenization_performance(self, fsa):
        """Benchmark tokenization performance."""
        text = "The quick brown fox jumps over the lazy dog. " * 100

        start_time = time.time()
        result = fsa.execute(text, "tokenize")
        elapsed_time = time.time() - start_time

        assert result['success'] is True
        assert elapsed_time < 1.0  # Should complete in under 1 second

    def test_sentiment_analysis_performance(self, fsa):
        """Benchmark sentiment analysis performance."""
        text = "I love this product! It's amazing. " * 50

        start_time = time.time()
        result = fsa.execute(text, "sentiment")
        elapsed_time = time.time() - start_time

        assert result['success'] is True
        assert elapsed_time < 1.0  # Should complete in under 1 second

    def test_cache_performance(self, fsa):
        """Test that caching improves performance."""
        text = "This is a test for cache performance."

        # First run (no cache)
        start_time = time.time()
        fsa.execute(text, "tokenize")
        first_run_time = time.time() - start_time

        # Second run (with cache)
        start_time = time.time()
        fsa.execute(text, "tokenize")
        cached_run_time = time.time() - start_time

        # Cached run should be faster (or at least not significantly slower)
        assert cached_run_time <= first_run_time * 1.1  # Allow 10% margin


class TestConfiguration:
    """Tests for FSA configuration."""

    def test_custom_config(self):
        """Test FSA initialization with custom configuration."""
        config = NLPConfig(
            max_text_length=50000,
            cache_size=256,
            lowercase=True,
            remove_punctuation=True
        )
        fsa = NaturalLanguageProcessorFSA(config=config)

        assert fsa.config.max_text_length == 50000
        assert fsa.config.cache_size == 256
        assert fsa.config.lowercase is True

    def test_default_config(self, fsa):
        """Test that default configuration is properly set."""
        assert fsa.config.max_text_length == 100000
        assert fsa.config.cache_size == 128
        assert fsa.config.summary_ratio == 0.3
