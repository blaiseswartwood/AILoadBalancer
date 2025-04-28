from transformers import pipeline
import numpy as np

class SemanticCache:
    """Cache for storing semantic embeddings and their corresponding values.

    The cache is formatted as a list of tuples, where each tuple contains an embedding and its corresponding value.
    The cache uses cosine similarity to determine if a new message is similar to any existing messages in the cache.
    """
    def __init__(self, similarity_threshold=0.95, CACHE_LOGS=True):
        self.cache = [] # (list of tuples (embedding, value))
        self.semantic_pipeline = pipeline("feature-extraction", model="distilbert-base-uncased")
        self.similarity_threshold = similarity_threshold
        self.CACHE_LOGS = CACHE_LOGS
    
    def get(self, msg):
        """Iterates through the cache checking for semantic similarity to the given message.

        Args:
            msg (str): The message to be checked against the cache.
        """
        query_embedding = self.semantic_key(msg)

        for cached_embedding, value in self.cache:
            similarity = self.cosine_similarity(query_embedding, cached_embedding)
            if similarity >= self.similarity_threshold:
            
                if self.CACHE_LOGS:
                    print("Got a cache hit! Simliarity: ", similarity)
                    
                return str(value)
            
        if self.CACHE_LOGS:
            print("Cache miss - no semantic similarity!")
            
        return None
    
    def add(self, msg, value):
        emb_vec = self.semantic_key(msg)
        self.cache.append((emb_vec, value))
    
    def clear(self):
        self.cache.clear()
        
    def semantic_key(self, data):
        # (1, num_tokens, 768)
        embedding = self.semantic_pipeline(data)
        mean_embedding = np.mean(embedding[0], axis=0)
        return mean_embedding

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

