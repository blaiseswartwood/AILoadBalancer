from transformers import pipeline
import numpy as np
from collections import deque

class SemanticCache:
    """Cache for storing semantic embeddings and their corresponding values.

    The cache is formatted as a dictionary of embedding, value.
    The cache uses cosine similarity to determine if a new message is similar to any existing messages in the cache.
    """
    def __init__(self, similarity_threshold=0.95, CACHE_LOGS=True):
        self.cache = {} # dict of (embedding, value)
        self.ordering = deque()
        self.max_cache_size = 2
        self.semantic_pipeline = pipeline("feature-extraction", model="distilbert-base-uncased")
        self.similarity_threshold = similarity_threshold
        self.CACHE_LOGS = CACHE_LOGS
    
    def get(self, msg):
        """Iterates through the cache checking for semantic similarity to the given message.

        Args:
            msg (str): The message to be checked against the cache.
        """
        query_embedding = self.semantic_key(msg)

        for cached_key, value in self.cache.items():
            cached_embedding = np.array(cached_key)
            similarity = self.cosine_similarity(query_embedding, cached_embedding)
            if similarity >= self.similarity_threshold:
            
                if self.CACHE_LOGS:
                    print("Got a cache hit! Simliarity: ", similarity)
                    
                # make it the most recent entry in the cache
                self.ordering.remove(cached_key)
                self.ordering.append(cached_key)
                return str(value)
            
        if self.CACHE_LOGS:
            print("Cache miss - no semantic similarity!")
            
        return None
    
    def add(self, msg, value):
        if len(self.cache) >= self.max_cache_size:
            oldest_entry = self.ordering.popleft()
            del self.cache[oldest_entry]            
            if self.CACHE_LOGS:
                print("Max cache size reached! Removing oldest entry.")
        emb_vec = self.semantic_key(msg)
        emb_key = tuple(emb_vec)
        self.cache[emb_key] = value
        self.ordering.append(emb_key)
    
    def clear(self):
        self.cache.clear()
        self.ordering.clear()
        
    def semantic_key(self, data):
        # (1, num_tokens, 768)
        embedding = self.semantic_pipeline(data)
        mean_embedding = np.mean(embedding[0], axis=0)
        return mean_embedding

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

