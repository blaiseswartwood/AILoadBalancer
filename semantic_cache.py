from transformers import pipeline
import numpy as np

CACHE_LOGS = True
class SemanticCache:
    def __init__(self, similarity_threshold=0.95):
        self.cache = [] # (list of tuples (embedding, value))
        print("Initializing semantic cache...")
        self.semantic_pipeline = pipeline("feature-extraction", model="distilbert-base-uncased")
        print("Semantic cache ready.")
        self.similarity_threshold = similarity_threshold
    
    def get(self, msg):
        query_embedding = self.semantic_key(msg)

        for cached_embedding, value in self.cache:
            similarity = self.cosine_similarity(query_embedding, cached_embedding)
            if similarity >= self.similarity_threshold:
            
                if CACHE_LOGS:
                    print("Got a cache hit! Simliarity: ", similarity)
                    
                return str(value)
            
        if CACHE_LOGS:
            print("Cache miss - no semantic similarity!")
            
        return None
    
    def add(self, msg, value):
        emb_vec = self.semantic_key(msg)
        self.cache.append((emb_vec, value))
    
    def clear(self):
        self.cache.clear()
        
    def semantic_key(self, data):
        embedding = self.semantic_pipeline(data)
        # (1, num_tokens, 768)
        mean_embedding = np.mean(embedding[0], axis=0)
        if CACHE_LOGS:
            print("Mean embedding shape: ", mean_embedding.shape)
        return mean_embedding

    def cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

