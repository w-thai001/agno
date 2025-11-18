"""
Natural Language Processor FSA (Focused Specialized Agent)

This module provides a comprehensive Natural Language Processing agent for the MLA framework.
It handles various NLP tasks including tokenization, named entity recognition, sentiment analysis,
part-of-speech tagging, dependency parsing, intent classification, language detection, and text summarization.

The FSA integrates with popular NLP libraries (spaCy, NLTK, transformers) and includes robust
error handling, caching mechanisms, and comprehensive validation.
"""

from __future__ import annotations

import hashlib
import re
import string
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import nltk
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import sent_tokenize, word_tokenize

from agno.utils.log import logger


# Download required NLTK data on initialization
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)


@dataclass
class NLPConfig:
    """Configuration for Natural Language Processor FSA."""

    # Model settings
    spacy_model: str = "en_core_web_sm"
    max_text_length: int = 100000
    cache_size: int = 128

    # Tokenization settings
    remove_punctuation: bool = False
    remove_stopwords: bool = False
    lowercase: bool = False

    # Sentiment analysis settings
    sentiment_threshold_positive: float = 0.05
    sentiment_threshold_negative: float = -0.05

    # Summarization settings
    summary_ratio: float = 0.3
    min_summary_sentences: int = 1
    max_summary_sentences: int = 10

    # Language detection settings
    supported_languages: List[str] = field(default_factory=lambda: [
        'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ar'
    ])

    # Intent classification settings
    intent_confidence_threshold: float = 0.6
    max_intents: int = 5


@dataclass
class EntityResult:
    """Represents an extracted named entity."""

    text: str
    label: str
    start_pos: int
    end_pos: int
    confidence: float = 1.0


@dataclass
class SentimentResult:
    """Represents sentiment analysis results."""

    polarity: str  # 'positive', 'negative', or 'neutral'
    compound_score: float
    positive_score: float
    negative_score: float
    neutral_score: float
    confidence: float


@dataclass
class IntentResult:
    """Represents an intent classification result."""

    intent: str
    confidence: float
    entities: List[EntityResult] = field(default_factory=list)


class NaturalLanguageProcessorFSA:
    """
    Focused Specialized Agent for Natural Language Processing.

    This FSA provides comprehensive NLP capabilities including:
    - Text tokenization and normalization
    - Named entity recognition (NER)
    - Sentiment analysis
    - Part-of-speech tagging
    - Dependency parsing
    - Intent classification
    - Language detection
    - Text summarization

    The agent uses a combination of NLTK, spaCy, and custom algorithms to provide
    robust NLP functionality with caching and error handling.

    Example:
        >>> fsa = NaturalLanguageProcessorFSA()
        >>> result = fsa.execute("Hello world!", "tokenize")
        >>> print(result['tokens'])
        ['Hello', 'world', '!']
    """

    def __init__(self, config: Optional[NLPConfig] = None):
        """
        Initialize the Natural Language Processor FSA.

        Args:
            config: Configuration object for the FSA. If None, uses default configuration.
        """
        self.config = config or NLPConfig()
        self._spacy_nlp = None
        self._sia = None  # Sentiment Intensity Analyzer
        self._cache: Dict[str, Any] = {}
        self._stopwords: Set[str] = set(stopwords.words('english'))

        # Intent patterns for basic intent classification
        self._intent_patterns = self._initialize_intent_patterns()

        # Language detection patterns (basic heuristics)
        self._language_patterns = self._initialize_language_patterns()

        logger.info("NaturalLanguageProcessorFSA initialized successfully")

    def _initialize_intent_patterns(self) -> Dict[str, List[str]]:
        """
        Initialize intent classification patterns.

        Returns:
            Dictionary mapping intent names to pattern lists.
        """
        return {
            'greeting': [
                r'\b(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))\b',
                r'\bhowdy\b',
                r'\bwhat\'?s\s+up\b',
            ],
            'farewell': [
                r'\b(goodbye|bye|farewell|see\s+you|talk\s+to\s+you\s+later)\b',
                r'\bcatch\s+you\s+later\b',
                r'\btake\s+care\b',
            ],
            'question': [
                r'^\s*(what|when|where|who|why|how|which|whose|whom)\b',
                r'\?$',
                r'\b(can\s+you|could\s+you|would\s+you)\b',
            ],
            'command': [
                r'^\s*(do|make|create|delete|remove|update|add|set|get)\b',
                r'\bplease\s+(do|make|create|delete|remove)\b',
                r'^\s*(show|display|list|find)\b',
            ],
            'affirmation': [
                r'\b(yes|yeah|yep|sure|okay|ok|alright|absolutely|definitely)\b',
                r'\bi\s+agree\b',
                r'\bthat\'?s\s+correct\b',
            ],
            'negation': [
                r'\b(no|nope|nah|never|not\s+really)\b',
                r'\bi\s+disagree\b',
                r'\bthat\'?s\s+(wrong|incorrect)\b',
            ],
            'gratitude': [
                r'\b(thank|thanks|appreciate|grateful)\b',
                r'\bthank\s+you\b',
            ],
            'apology': [
                r'\b(sorry|apologize|apology|my\s+bad|excuse\s+me)\b',
                r'\bi\s+apologize\b',
            ],
        }

    def _initialize_language_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize language detection patterns.

        Returns:
            Dictionary with language detection heuristics.
        """
        return {
            'en': {
                'common_words': {'the', 'is', 'and', 'to', 'a', 'of', 'in', 'that', 'it', 'for'},
                'pattern': r'[a-zA-Z\s]+',
            },
            'es': {
                'common_words': {'el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se'},
                'pattern': r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ\s]+',
            },
            'fr': {
                'common_words': {'le', 'de', 'un', 'être', 'et', 'à', 'il', 'avoir', 'ne', 'je'},
                'pattern': r'[a-zA-ZàâäæçéèêëïîôùûüÿœÀÂÄÆÇÉÈÊËÏÎÔÙÛÜŸŒ\s]+',
            },
            'de': {
                'common_words': {'der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich'},
                'pattern': r'[a-zA-ZäöüßÄÖÜ\s]+',
            },
        }

    @property
    def spacy_nlp(self):
        """
        Lazy-load spaCy model.

        Returns:
            spaCy language model.
        """
        if self._spacy_nlp is None:
            try:
                import spacy
                try:
                    self._spacy_nlp = spacy.load(self.config.spacy_model)
                    logger.info(f"Loaded spaCy model: {self.config.spacy_model}")
                except OSError:
                    logger.warning(
                        f"spaCy model '{self.config.spacy_model}' not found. "
                        f"Please install it with: python -m spacy download {self.config.spacy_model}"
                    )
                    # Use a blank model as fallback
                    self._spacy_nlp = spacy.blank("en")
            except ImportError:
                logger.warning("spaCy not installed. Some features will be limited.")
                self._spacy_nlp = None
        return self._spacy_nlp

    @property
    def sentiment_analyzer(self):
        """
        Lazy-load NLTK sentiment analyzer.

        Returns:
            NLTK SentimentIntensityAnalyzer.
        """
        if self._sia is None:
            self._sia = SentimentIntensityAnalyzer()
        return self._sia

    def _generate_cache_key(self, text: str, task: str, **kwargs) -> str:
        """
        Generate a cache key for the given text and task.

        Args:
            text: Input text.
            task: Task name.
            **kwargs: Additional parameters.

        Returns:
            Hash-based cache key.
        """
        key_data = f"{task}:{text}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve result from cache.

        Args:
            cache_key: Cache key.

        Returns:
            Cached result or None.
        """
        return self._cache.get(cache_key)

    def _store_in_cache(self, cache_key: str, result: Any) -> None:
        """
        Store result in cache with size limit.

        Args:
            cache_key: Cache key.
            result: Result to cache.
        """
        if len(self._cache) >= self.config.cache_size:
            # Remove oldest entry (simple FIFO)
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = result

    def validate(self) -> bool:
        """
        Validate the FSA configuration and dependencies.

        Returns:
            True if validation passes, False otherwise.
        """
        try:
            # Check NLTK data
            required_nltk_data = ['punkt', 'punkt_tab', 'stopwords', 'vader_lexicon',
                                 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng']
            for dataset in required_nltk_data:
                try:
                    nltk.data.find(dataset)
                except LookupError:
                    # Some datasets are optional, so just log a warning
                    logger.warning(f"NLTK dataset '{dataset}' not found, downloading...")
                    try:
                        nltk.download(dataset, quiet=True)
                    except:
                        logger.error(f"Failed to download NLTK dataset '{dataset}'")
                        return False

            # Check spaCy model if available
            if self.spacy_nlp is None:
                logger.warning("spaCy model not available, some features will be limited")

            # Validate configuration
            if self.config.max_text_length <= 0:
                logger.error("max_text_length must be positive")
                return False

            if not 0 <= self.config.summary_ratio <= 1:
                logger.error("summary_ratio must be between 0 and 1")
                return False

            logger.info("FSA validation successful")
            return True

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return False

    def error_handling(self, exception: Exception) -> Dict[str, Any]:
        """
        Handle errors and return formatted error information.

        Args:
            exception: The exception that occurred.

        Returns:
            Dictionary with error details.
        """
        error_info = {
            'success': False,
            'error': {
                'type': type(exception).__name__,
                'message': str(exception),
                'details': None,
            }
        }

        # Add specific error details based on exception type
        if isinstance(exception, ValueError):
            error_info['error']['details'] = "Invalid input value provided"
        elif isinstance(exception, ImportError):
            error_info['error']['details'] = "Required dependency not installed"
        elif isinstance(exception, LookupError):
            error_info['error']['details'] = "Required NLTK data not found"

        logger.error(f"Error in NLP FSA: {error_info['error']}")
        return error_info

    def normalize_text(self, text: str) -> str:
        """
        Normalize text based on configuration.

        Args:
            text: Input text.

        Returns:
            Normalized text.
        """
        normalized = text

        if self.config.lowercase:
            normalized = normalized.lower()

        if self.config.remove_punctuation:
            normalized = normalized.translate(str.maketrans('', '', string.punctuation))

        # Remove extra whitespace
        normalized = ' '.join(normalized.split())

        return normalized

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text to tokenize.

        Returns:
            List of tokens.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> fsa.tokenize("Hello, world!")
            ['Hello', ',', 'world', '!']
        """
        try:
            if not text or not text.strip():
                return []

            # Validate text length
            if len(text) > self.config.max_text_length:
                raise ValueError(f"Text length exceeds maximum of {self.config.max_text_length}")

            # Use NLTK word tokenizer
            tokens = word_tokenize(text)

            # Apply filters based on configuration
            if self.config.remove_stopwords:
                tokens = [t for t in tokens if t.lower() not in self._stopwords]

            if self.config.remove_punctuation:
                tokens = [t for t in tokens if t not in string.punctuation]

            if self.config.lowercase:
                tokens = [t.lower() for t in tokens]

            return tokens

        except Exception as e:
            logger.error(f"Tokenization failed: {str(e)}")
            raise

    def extract_entities(self, text: str) -> List[Dict[str, str]]:
        """
        Extract named entities from text using spaCy.

        Args:
            text: Input text.

        Returns:
            List of dictionaries containing entity information.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> entities = fsa.extract_entities("Apple Inc. is located in California.")
            >>> print(entities[0]['label'])
            'ORG'
        """
        try:
            if not text or not text.strip():
                return []

            if self.spacy_nlp is None:
                logger.warning("spaCy not available for entity extraction")
                return []

            doc = self.spacy_nlp(text)
            entities = []

            for ent in doc.ents:
                entity = {
                    'text': ent.text,
                    'label': ent.label_,
                    'start_pos': ent.start_char,
                    'end_pos': ent.end_char,
                }
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            raise

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text using VADER sentiment analyzer.

        Args:
            text: Input text.

        Returns:
            Dictionary with sentiment scores.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> sentiment = fsa.analyze_sentiment("I love this product!")
            >>> print(sentiment['polarity'])
            'positive'
        """
        try:
            if not text or not text.strip():
                return {
                    'polarity': 'neutral',
                    'compound': 0.0,
                    'positive': 0.0,
                    'negative': 0.0,
                    'neutral': 1.0,
                    'confidence': 1.0,
                }

            # Get VADER scores
            scores = self.sentiment_analyzer.polarity_scores(text)

            # Determine polarity based on compound score
            compound = scores['compound']
            if compound >= self.config.sentiment_threshold_positive:
                polarity = 'positive'
                confidence = min(abs(compound), 1.0)
            elif compound <= self.config.sentiment_threshold_negative:
                polarity = 'negative'
                confidence = min(abs(compound), 1.0)
            else:
                polarity = 'neutral'
                confidence = 1.0 - abs(compound)

            return {
                'polarity': polarity,
                'compound': compound,
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu'],
                'confidence': confidence,
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            raise

    def pos_tag(self, text: str) -> List[Tuple[str, str]]:
        """
        Perform part-of-speech tagging.

        Args:
            text: Input text.

        Returns:
            List of (token, tag) tuples.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> tags = fsa.pos_tag("The cat sat on the mat.")
            >>> print(tags[0])
            ('The', 'DT')
        """
        try:
            if not text or not text.strip():
                return []

            tokens = word_tokenize(text)
            return nltk.pos_tag(tokens)

        except Exception as e:
            logger.error(f"POS tagging failed: {str(e)}")
            raise

    def parse_dependencies(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse dependency relationships using spaCy.

        Args:
            text: Input text.

        Returns:
            List of dependency dictionaries.
        """
        try:
            if not text or not text.strip():
                return []

            if self.spacy_nlp is None:
                logger.warning("spaCy not available for dependency parsing")
                return []

            doc = self.spacy_nlp(text)
            dependencies = []

            for token in doc:
                dep_info = {
                    'text': token.text,
                    'pos': token.pos_,
                    'dep': token.dep_,
                    'head': token.head.text,
                    'children': [child.text for child in token.children],
                }
                dependencies.append(dep_info)

            return dependencies

        except Exception as e:
            logger.error(f"Dependency parsing failed: {str(e)}")
            raise

    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the input text using heuristics.

        Args:
            text: Input text.

        Returns:
            Dictionary with language code and confidence.
        """
        try:
            if not text or not text.strip():
                return {'language': 'unknown', 'confidence': 0.0}

            text_lower = text.lower()
            words = set(word_tokenize(text_lower))

            language_scores = {}

            for lang_code, lang_info in self._language_patterns.items():
                common_words = lang_info['common_words']
                matches = len(words.intersection(common_words))
                score = matches / len(common_words) if common_words else 0
                language_scores[lang_code] = score

            # Get language with highest score
            if language_scores:
                detected_lang = max(language_scores.items(), key=lambda x: x[1])
                return {
                    'language': detected_lang[0],
                    'confidence': detected_lang[1],
                    'all_scores': language_scores,
                }

            return {'language': 'unknown', 'confidence': 0.0}

        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            raise

    def classify_intent(self, text: str) -> Dict[str, float]:
        """
        Classify the intent of the input text using pattern matching.

        Args:
            text: Input text.

        Returns:
            Dictionary with intent labels and confidence scores.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> intent = fsa.classify_intent("What is the weather today?")
            >>> print(intent['intent'])
            'question'
        """
        try:
            if not text or not text.strip():
                return {'intent': 'unknown', 'confidence': 0.0, 'all_intents': {}}

            text_lower = text.lower()
            intent_scores = defaultdict(float)

            # Match against patterns
            for intent, patterns in self._intent_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        intent_scores[intent] += 1.0

            # Normalize scores
            total_matches = sum(intent_scores.values())
            if total_matches > 0:
                intent_scores = {
                    intent: score / total_matches
                    for intent, score in intent_scores.items()
                }

            # Get top intent
            if intent_scores:
                top_intent = max(intent_scores.items(), key=lambda x: x[1])
                return {
                    'intent': top_intent[0],
                    'confidence': top_intent[1],
                    'all_intents': dict(intent_scores),
                }

            return {'intent': 'unknown', 'confidence': 0.0, 'all_intents': {}}

        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            raise

    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """
        Summarize text using extractive summarization.

        Args:
            text: Input text to summarize.
            max_length: Maximum number of sentences in summary.

        Returns:
            Summarized text.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> summary = fsa.summarize("Long text here...", max_length=2)
        """
        try:
            if not text or not text.strip():
                return ""

            # Split into sentences
            sentences = sent_tokenize(text)

            if len(sentences) <= 1:
                return text

            # Calculate sentence scores based on word frequency
            word_freq = Counter()
            for sentence in sentences:
                words = word_tokenize(sentence.lower())
                words = [w for w in words if w not in self._stopwords and w not in string.punctuation]
                word_freq.update(words)

            # Normalize frequencies
            max_freq = max(word_freq.values()) if word_freq else 1
            for word in word_freq:
                word_freq[word] /= max_freq

            # Score sentences
            sentence_scores = {}
            for i, sentence in enumerate(sentences):
                words = word_tokenize(sentence.lower())
                score = sum(word_freq.get(w, 0) for w in words)
                sentence_scores[i] = score / len(words) if words else 0

            # Determine number of sentences to include
            if max_length is None:
                num_sentences = max(
                    self.config.min_summary_sentences,
                    min(
                        int(len(sentences) * self.config.summary_ratio),
                        self.config.max_summary_sentences
                    )
                )
            else:
                num_sentences = min(max_length, len(sentences))

            # Get top sentences (preserving order)
            top_indices = sorted(
                sorted(sentence_scores.items(), key=lambda x: x[1], reverse=True)[:num_sentences],
                key=lambda x: x[0]
            )

            summary_sentences = [sentences[i] for i, _ in top_indices]
            return ' '.join(summary_sentences)

        except Exception as e:
            logger.error(f"Summarization failed: {str(e)}")
            raise

    def execute(self, text: str, task: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a specific NLP task on the input text.

        Args:
            text: Input text.
            task: Task to perform ('tokenize', 'sentiment', 'entities', 'pos_tag',
                  'dependencies', 'language', 'intent', 'summarize').
            **kwargs: Additional task-specific parameters.

        Returns:
            Dictionary with task results.

        Example:
            >>> fsa = NaturalLanguageProcessorFSA()
            >>> result = fsa.execute("Hello world!", "tokenize")
            >>> print(result['tokens'])
            ['Hello', 'world', '!']
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(text, task, **kwargs)

            # Check cache
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for task '{task}'")
                return cached_result

            # Execute task
            result = {'success': True, 'task': task}

            if task == 'tokenize':
                result['tokens'] = self.tokenize(text)

            elif task == 'sentiment':
                result['sentiment'] = self.analyze_sentiment(text)

            elif task == 'entities':
                result['entities'] = self.extract_entities(text)

            elif task == 'pos_tag':
                result['pos_tags'] = self.pos_tag(text)

            elif task == 'dependencies':
                result['dependencies'] = self.parse_dependencies(text)

            elif task == 'language':
                result['language'] = self.detect_language(text)

            elif task == 'intent':
                result['intent'] = self.classify_intent(text)

            elif task == 'summarize':
                max_length = kwargs.get('max_length')
                result['summary'] = self.summarize(text, max_length)

            else:
                raise ValueError(f"Unknown task: {task}")

            # Store in cache
            self._store_in_cache(cache_key, result)

            return result

        except Exception as e:
            return self.error_handling(e)
