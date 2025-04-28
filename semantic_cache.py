from transformers import pipeline
import numpy as np
import hashlib

class SemanticCache:
    def __init__(self):
        self.cache = {}
        print("Initializing semantic cache...")
        self.semantic_pipeline = pipeline("feature-extraction", model="distilbert-base-uncased")
        print("Semantic cache ready.")
    
    def get(self, key):
        return self.cache.get(key, None)
    
    def add(self, key, value):
        self.cache[key] = value
    
    def clear(self):
        self.cache.clear()
        
    def semantic_key(self, data):
        embedding = self.semantic_pipeline(data)
        embedding = np.array(embedding).flatten()
        
        emb_bytes = embedding.tobytes()
        hash_value = hashlib.sha256(emb_bytes).hexdigest()
        return str(hash_value)


