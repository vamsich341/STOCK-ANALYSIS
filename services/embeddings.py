"""Embeddings Service - Generate and manage embeddings for semantic search"""

import os
import logging
from typing import List, Optional
import openai
import time

logger = logging.getLogger(__name__)

class EmbeddingsService:
    """Service for generating text embeddings using OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize embeddings service
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
            self.model = "text-embedding-ada-002"
            self.dimensions = 1536
            logger.info(f"EmbeddingsService initialized with model {self.model}")
        else:
            logger.warning("No OpenAI API key provided. Embeddings will not be generated.")
            self.model = None
    
    def generate_embedding(self, text: str, retry_count: int = 3) -> Optional[List[float]]:
        """Generate embedding for a single text
        
        Args:
            text: Text to embed
            retry_count: Number of retries on failure
        
        Returns:
            List of floats (embedding vector) or None on error
        """
        if not self.api_key or not text or not text.strip():
            return None
        
        # Truncate text to avoid token limits (max ~8000 tokens for ada-002)
        text = text[:8000]
        
        for attempt in range(retry_count):
            try:
                response = openai.Embedding.create(
                    input=text,
                    model=self.model
                )
                embedding = response['data'][0]['embedding']
                logger.debug(f"Generated embedding for text of length {len(text)}")
                return embedding
            
            except openai.error.RateLimitError as e:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{retry_count})")
                time.sleep(wait_time)
            
            except openai.error.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                if attempt < retry_count - 1:
                    time.sleep(1)
                else:
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error generating embedding: {e}")
                return None
        
        return None
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Maximum texts per API call
        
        Returns:
            List of embeddings (or None for failed texts)
        """
        if not self.api_key:
            return [None] * len(texts)
        
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Filter empty texts
            batch_filtered = [t[:8000] if t else "" for t in batch]
            
            try:
                response = openai.Embedding.create(
                    input=batch_filtered,
                    model=self.model
                )
                
                batch_embeddings = [item['embedding'] for item in response['data']]
                embeddings.extend(batch_embeddings)
                
                logger.info(f"Generated {len(batch_embeddings)} embeddings (batch {i // batch_size + 1})")
                
                # Rate limiting
                time.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Error in batch embedding generation: {e}")
                # Return None for failed batch
                embeddings.extend([None] * len(batch))
        
        return embeddings
    
    def embed_company(self, ticker: str, name: str, description: str, 
                      sector: str = None, industry: str = None) -> Optional[List[float]]:
        """Generate embedding for company data
        
        Args:
            ticker: Company ticker
            name: Company name
            description: Company description
            sector: Company sector (optional)
            industry: Company industry (optional)
        
        Returns:
            Embedding vector or None
        """
        # Combine relevant fields into a rich text representation
        text_parts = [f"Company: {name} ({ticker})"]
        
        if description:
            text_parts.append(f"Description: {description}")
        
        if sector:
            text_parts.append(f"Sector: {sector}")
        
        if industry:
            text_parts.append(f"Industry: {industry}")
        
        combined_text = " ".join(text_parts)
        return self.generate_embedding(combined_text)
    
    def embed_news(self, title: str, summary: str = None, content: str = None) -> Optional[List[float]]:
        """Generate embedding for news article
        
        Args:
            title: Article title
            summary: Article summary (optional)
            content: Article content (optional)
        
        Returns:
            Embedding vector or None
        """
        # Prioritize title + summary, fall back to title + content
        text_parts = [f"Title: {title}"]
        
        if summary:
            text_parts.append(f"Summary: {summary}")
        elif content:
            # Use first 1000 chars of content if no summary
            text_parts.append(f"Content: {content[:1000]}")
        
        combined_text = " ".join(text_parts)
        return self.generate_embedding(combined_text)
