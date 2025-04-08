import os
import re
import nltk
from typing import List, Dict, Any, Union, Optional
import logging
from transformers import AutoTokenizer, AutoModel
import numpy as np
import torch

# Download NLTK resources if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
nltk.data.path.append(current_dir)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', download_dir=current_dir)
    nltk.download('punkt_tab', download_dir=current_dir)
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')

class SegmentationStrategy:
    """Base class for segmentation strategies"""
    def segment(self, text: str, **kwargs) -> List[str]:
        raise NotImplementedError

class SentenceSegmenter(SegmentationStrategy):
    """Segments text into sentences"""
    def segment(self, text: str, **kwargs) -> List[str]:
        return nltk.sent_tokenize(text)

class ParagraphSegmenter(SegmentationStrategy):
    """Segments text into paragraphs"""
    def segment(self, text: str, **kwargs) -> List[str]:
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text)]
        # I'm not returning empty paragraphs..
        return [p for p in paragraphs if p]

class FixedLengthSegmenter(SegmentationStrategy):
    """Segments text into chunks of approximately fixed length"""
    def segment(self, text: str, chunk_size: int = 100, overlap: int = 10, **kwargs) -> List[str]:
        words = text.split()
        segments = []

        i = 0
        while i < len(words):
            chunk_end = min(i + chunk_size, len(words))
            segments.append(' '.join(words[i:chunk_end]))
            i += chunk_size - overlap

        return segments

class SemanticSegmenter(SegmentationStrategy):
    """Segments text by semantic similarity using embeddings"""
    def __init__(self):
        self.tokenizer = None
        self.model = None

    def _load_model(self):
        if self.tokenizer is None or self.model is None:
            self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            self.model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

    def _get_embeddings(self, sentences: List[str]) -> np.ndarray:
        self._load_model()
        embeddings = []

        for sentence in sentences:
            inputs = self.tokenizer(sentence, return_tensors="pt", padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
            embeddings.append(outputs.last_hidden_state.mean(dim=1).squeeze().numpy())

        return np.array(embeddings)

    def _find_segment_boundaries(self, embeddings: np.ndarray, threshold: float = 0.5) -> List[int]:
        """Find segment boundaries based on cosine similarity"""
        cos_sims = np.zeros(len(embeddings) - 1)
        for i in range(len(embeddings) - 1):
            cos_sim = np.dot(embeddings[i], embeddings[i+1]) / (np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i+1]))
            cos_sims[i] = cos_sim

        # Find points where similarity drops below threshold
        boundaries = [i+1 for i, sim in enumerate(cos_sims) if sim < threshold]
        return boundaries

    def segment(self, text: str, threshold: float = 0.5, **kwargs) -> List[str]:
        sentences = nltk.sent_tokenize(text)
        if len(sentences) <= 1:
            return sentences
        try:
            embeddings = self._get_embeddings(sentences)

            # Find segment boundaries
            boundaries = self._find_segment_boundaries(embeddings, threshold)

            # create segments
            segments = []
            start = 0
            for boundary in boundaries:
                segments.append(' '.join(sentences[start:boundary]))
                start = boundary
            segments.append(' '.join(sentences[start:]))

            return segments
        except Exception as e:
            logging.error(f"Error in semantic segmentation: {e}")
            return sentences  # Fall back to sentence segmentation., if error out

# Registry of available segmentation strategies
_SEGMENTATION_STRATEGIES = {
    'sentence': SentenceSegmenter(),
    'paragraph': ParagraphSegmenter(),
    'fixed_length': FixedLengthSegmenter(),
    'semantic': SemanticSegmenter()
}

def register_segmentation_strategy(name: str, strategy: SegmentationStrategy):
    """Register a new segmentation strategy"""
    _SEGMENTATION_STRATEGIES[name] = strategy

def segmentation_tool(doc: Dict[str, Any],
                     strategy: str = 'paragraph',
                     feature_key: str = 'content',
                     output_key: str = 'segments',
                     **kwargs) -> List[str]:
    """
    Segments text into parts using the specified strategy, see _SEGMENTATION_STRATEGIES

    Args:
        doc: Input document in json format
        strategy: Segmentation strategy to use (default: "paragraph"), see _SEGMENTATION_STRATEGIES
        feature_key: Key in the input document containing the text to segment
        output_key: Key to store the segments in the result
        **kwargs: Additional parameters to pass to the segmentation strategy

    Returns:
        List of text segments
    """
    try:
        # Check if strategy exists
        if strategy not in _SEGMENTATION_STRATEGIES:
            logging.warning(f"Unknown segmentation strategy: {strategy}, falling back to paragraph")
            strategy = 'paragraph'
            
        # Process based on type of doc[feature_key]
        if feature_key not in doc:
            logging.warning(f"Content key '{feature_key}' not found in document, force to use the entire doc for segmentation")
            text = str(doc)
            segments = _SEGMENTATION_STRATEGIES[strategy].segment(text, **kwargs)
            return segments
            
        content = doc[feature_key]
        
        # Case 1: If content is an array, segment each element separately
        if isinstance(content, list):
            # Process each item in the list separately and merge results
            all_segments = []
            for item in content:
                item_text = str(item)
                if item_text:
                    item_segments = _SEGMENTATION_STRATEGIES[strategy].segment(item_text, **kwargs)
                    all_segments.extend(item_segments)
            return all_segments
            
        elif isinstance(content, dict) and len(content) == 1:
            single_value = list(content.values())[0]
            # Case 2: If content is a dict with a single key containing a list
            if isinstance(single_value, list):
                # Process each item in the list separately and merge results
                all_segments = []
                for item in single_value:
                    item_text = str(item)
                    if item_text:
                        item_segments = _SEGMENTATION_STRATEGIES[strategy].segment(item_text, **kwargs)
                        all_segments.extend(item_segments)
                return all_segments
            else:
                # Case 3: Single key with non-list value
                text = str(single_value)
                if not text:
                    return []
                segments = _SEGMENTATION_STRATEGIES[strategy].segment(text, **kwargs)
                return segments
        
        # Case 4: MOST COMMON CASE: If content is a string, segment it
        elif isinstance(content, str):
            if not content:
                return []
            segments = _SEGMENTATION_STRATEGIES[strategy].segment(content, **kwargs)
            return segments
            
        # Other dict cases
        elif isinstance(content, dict):
            # Join all values
            text = ' '.join([str(v) for v in content.values()])
            if not text:
                return []
            segments = _SEGMENTATION_STRATEGIES[strategy].segment(text, **kwargs)
            return segments
            
        # Fallback case
        else:
            logging.warning(f"Invalid text in document for key {feature_key}, force to use the input object for segmentation")
            text = str(doc)
            if not text:
                return []
            segments = _SEGMENTATION_STRATEGIES[strategy].segment(text, **kwargs)
            return segments
    except Exception as e:
        logging.error(f"Error in segmentation_tool: {e}")
        return []