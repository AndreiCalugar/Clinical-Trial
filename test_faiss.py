from vector_store import TrialVectorStore

def test_vector_store():
    # Create a new vector store
    vs = TrialVectorStore()
    vs.create_index()
    
    # Add some test trials
    test_trials = [
        {
            "id": "test-1", 
            "title": "Obesity Treatment Trial", 
            "description": "A study on treating obesity with GLP-1 agonists", 
            "primary_outcome": "Weight loss"
        },
        {
            "id": "test-2", 
            "title": "Diabetes Study", 
            "description": "A study on Type 2 diabetes management", 
            "primary_outcome": "Blood glucose control"
        }
    ]
    
    vs.add_trials(test_trials)
    
    # Test search
    results = vs.search("obesity treatment", 2)
    print("Search Results:")
    for r in results:
        print(f"Trial ID: {r['trial_id']}, Similarity: {r['similarity_score']:.4f}")
    
    # Save and reload
    vs.save("test_vector_store")
    print("Saved vector store")
    
    # Load and test again
    new_vs = TrialVectorStore()
    new_vs.load("test_vector_store")
    results = new_vs.search("obesity", 2)
    print("\nAfter reload - Search Results:")
    for r in results:
        print(f"Trial ID: {r['trial_id']}, Similarity: {r['similarity_score']:.4f}")

if __name__ == "__main__":
    try:
        test_vector_store()
        print("\nTest completed successfully!")
    except Exception as e:
        print(f"\nTest failed: {str(e)}") 