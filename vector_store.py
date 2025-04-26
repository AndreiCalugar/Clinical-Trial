from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import json
import os
from typing import List, Dict, Any

class TrialVectorStore:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        # Initialize sentence transformer model
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.trial_ids = []
        self.dimension = self.model.get_sentence_embedding_dimension()
        
    def create_index(self):
        # Create a new FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)
        return self
        
    def add_trials(self, trials: List[Dict[str, Any]]):
        # Extract text from trials and create embeddings
        texts = []
        trial_ids = []
        
        for trial in trials:
            # Combine relevant text fields for embedding
            text = f"{trial['title']} {trial['description']} {trial['primary_outcome']}"
            texts.append(text)
            trial_ids.append(trial['id'])
        
        # Generate embeddings
        embeddings = self.model.encode(texts)
        
        # Add to FAISS index
        if self.index is None:
            self.create_index()
            
        # Convert to float32 (required by FAISS)
        embeddings = np.array(embeddings).astype('float32')
        
        # Add to index
        self.index.add(embeddings)
        self.trial_ids.extend(trial_ids)
        
        return self
    
    def search(self, query: str, top_k: int = 5):
        # Make sure we have an index
        if self.index is None:
            raise ValueError("No index available. Create or load an index first.")
        
        # Make sure we have trials in the index
        if len(self.trial_ids) == 0:
            return []
        
        # Encode query
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search
        distances, indices = self.index.search(query_embedding, min(top_k, len(self.trial_ids)))
        
        # Get results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.trial_ids):
                results.append({
                    "trial_id": self.trial_ids[idx],
                    "similarity_score": float(1.0 - distances[0][i]/10)  # Convert distance to similarity
                })
        
        return results
    
    def save(self, path: str = "vector_store"):
        # Create directory if it doesn't exist
        os.makedirs(path, exist_ok=True)
        
        # Save index
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        
        # Save trial IDs
        with open(os.path.join(path, "trial_ids.json"), "w") as f:
            json.dump(self.trial_ids, f)
            
    def load(self, path: str = "vector_store"):
        # Load index
        self.index = faiss.read_index(os.path.join(path, "index.faiss"))
        
        # Load trial IDs
        with open(os.path.join(path, "trial_ids.json"), "r") as f:
            self.trial_ids = json.load(f)
            
        return self 