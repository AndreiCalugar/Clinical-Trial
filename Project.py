from fastapi import FastAPI, HTTPException, Query, Depends, status
from typing import List, Optional, Dict, Any
from pymongo import MongoClient
from neo4j import GraphDatabase
from pydantic import BaseModel, Field, validator
import uuid
from datetime import datetime
from enum import Enum
import os
from dotenv import load_dotenv
from vector_store import TrialVectorStore

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Novo Nordisk Metadata Repository",
    description="API for managing clinical trial metadata with MongoDB and Neo4j",
    version="1.0.0"
)

# Add this after your other initializations, before the API routes
# Initialize vector store
vector_store = None

@app.on_event("startup")
async def initialize_vector_store():
    global vector_store
    vector_store = TrialVectorStore()
    
    try:
        # First try to load existing index
        vector_store.load()
        print("Loaded existing vector store")
    except Exception as e:
        print(f"Creating new vector store: {str(e)}")
        vector_store.create_index()
        
        # Add existing trials from MongoDB
        try:
            db = get_db()
            trials = list(db.trials.find({}))
            if trials:
                # Convert ObjectId to string
                for trial in trials:
                    trial["_id"] = str(trial["_id"])
                vector_store.add_trials(trials)
                vector_store.save()
                print(f"Added {len(trials)} trials to vector store")
        except Exception as e:
            print(f"Error loading trials into vector store: {str(e)}")

# ---- Pydantic Models ----

class TrialPhase(str, Enum):
    PHASE_1 = "1"
    PHASE_2 = "2"
    PHASE_3 = "3"
    PHASE_4 = "4"

class TrialStatus(str, Enum):
    PLANNED = "planned"
    RECRUITING = "recruiting"
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"

class ClinicalTrial(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    nct_id: Optional[str] = None
    title: str
    phase: TrialPhase
    status: TrialStatus
    start_date: datetime
    end_date: Optional[datetime] = None
    description: str
    primary_outcome: str
    secondary_outcomes: List[str] = []
    inclusion_criteria: List[str] = []
    exclusion_criteria: List[str] = []
    locations: List[str] = []
    sponsor: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if v and 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v

    class Config:
        schema_extra = {
            "example": {
                "title": "A Phase 3 Trial of Wegovy in Obesity",
                "nct_id": "NCT04456789",
                "phase": "3",
                "status": "recruiting",
                "start_date": "2023-01-15T00:00:00",
                "end_date": "2025-01-15T00:00:00",
                "description": "Evaluating the efficacy of Wegovy in treatment of obesity",
                "primary_outcome": "Weight loss percentage after 68 weeks",
                "secondary_outcomes": ["Change in BMI", "Glycemic control"],
                "inclusion_criteria": ["BMI ≥ 30", "Age 18-65"],
                "exclusion_criteria": ["Pregnancy", "History of pancreatitis"],
                "locations": ["Copenhagen, Denmark", "Chicago, USA"],
                "sponsor": "Novo Nordisk"
            }
        }

class DrugCompound(BaseModel):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    molecule_type: str
    target_proteins: List[str] = []
    mechanism_of_action: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class Relationship(BaseModel):
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    relationship_type: str
    properties: Dict[str, Any] = {}

# ---- Database Connections ----

# MongoDB Connection
def get_mongo_client():
    client = MongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017/"))
    try:
        yield client
    finally:
        client.close()

def get_db(client=Depends(get_mongo_client)):
    return client[os.getenv("MONGODB_DB", "novo_mdr")]

# Neo4j Connection
def get_neo4j_driver():
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
    )
    try:
        yield driver
    finally:
        driver.close()

# ---- API Routes ----

# Health Check
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# CRUD Operations for Clinical Trials

@app.post("/trials", status_code=status.HTTP_201_CREATED, response_model=ClinicalTrial)
def create_trial(trial: ClinicalTrial, db=Depends(get_db)):
    # Convert to dict for MongoDB
    trial_dict = trial.model_dump()
    
    # Convert datetime to string for MongoDB
    trial_dict["start_date"] = trial_dict["start_date"].isoformat()
    if trial_dict.get("end_date"):
        trial_dict["end_date"] = trial_dict["end_date"].isoformat()
    trial_dict["created_at"] = trial_dict["created_at"].isoformat()
    trial_dict["updated_at"] = trial_dict["updated_at"].isoformat()
    
    result = db.trials.insert_one(trial_dict)
    
    if not result.acknowledged:
        raise HTTPException(status_code=500, detail="Failed to create trial")
    
    # Add to vector store
    global vector_store
    vector_store.add_trials([trial_dict])
    vector_store.save()
    
    return trial

@app.get("/trials", response_model=List[ClinicalTrial])
def list_trials(
    phase: Optional[TrialPhase] = None,
    status: Optional[TrialStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db)
):
    query = {}
    
    if phase:
        query["phase"] = phase
    if status:
        query["status"] = status
        
    trials = list(db.trials.find(query).skip(skip).limit(limit))
    
    # Convert string dates back to datetime for Pydantic validation
    for trial in trials:
        trial["_id"] = str(trial["_id"])  # Convert ObjectId to string
        trial["start_date"] = datetime.fromisoformat(trial["start_date"])
        if trial.get("end_date"):
            trial["end_date"] = datetime.fromisoformat(trial["end_date"])
        trial["created_at"] = datetime.fromisoformat(trial["created_at"])
        trial["updated_at"] = datetime.fromisoformat(trial["updated_at"])
    
    return trials

@app.get("/trials/{trial_id}", response_model=ClinicalTrial)
def get_trial(trial_id: str):
    db = get_db()
    trial = db.trials.find_one({"id": trial_id})
    
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial with ID {trial_id} not found")
    
    # Convert string dates back to datetime for Pydantic validation
    trial["_id"] = str(trial["_id"])
    trial["start_date"] = datetime.fromisoformat(trial["start_date"])
    if trial.get("end_date"):
        trial["end_date"] = datetime.fromisoformat(trial["end_date"])
    trial["created_at"] = datetime.fromisoformat(trial["created_at"])
    trial["updated_at"] = datetime.fromisoformat(trial["updated_at"])
    
    return trial

@app.put("/trials/{trial_id}", response_model=ClinicalTrial)
def update_trial(trial_id: str, trial_update: ClinicalTrial):
    db = get_db()
    existing_trial = db.trials.find_one({"id": trial_id})
    
    if not existing_trial:
        raise HTTPException(status_code=404, detail=f"Trial with ID {trial_id} not found")
    
    # Preserve the original ID
    trial_update.id = trial_id
    trial_update.created_at = datetime.fromisoformat(existing_trial["created_at"])
    trial_update.updated_at = datetime.now()
    
    # Convert to dict for MongoDB update
    update_data = trial_update.dict()
    
    # Convert datetime to string for MongoDB
    update_data["start_date"] = update_data["start_date"].isoformat()
    if update_data.get("end_date"):
        update_data["end_date"] = update_data["end_date"].isoformat()
    update_data["created_at"] = update_data["created_at"].isoformat()
    update_data["updated_at"] = update_data["updated_at"].isoformat()
    
    result = db.trials.update_one({"id": trial_id}, {"$set": update_data})
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update trial")
    
    return trial_update

@app.delete("/trials/{trial_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trial(trial_id: str):
    db = get_db()
    result = db.trials.delete_one({"id": trial_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Trial with ID {trial_id} not found")
    
    return None

# Neo4j Relationship Management

@app.post("/relationships", status_code=status.HTTP_201_CREATED)
def create_relationship(relationship: Relationship, driver=Depends(get_neo4j_driver)):
    with driver.session() as session:
        # Create or get source node
        session.run(
            """
            MERGE (source:{source_type} {{id: $source_id}})
            """.format(source_type=relationship.source_type),
            source_id=relationship.source_id
        )
        
        # Create or get target node
        session.run(
            """
            MERGE (target:{target_type} {{id: $target_id}})
            """.format(target_type=relationship.target_type),
            target_id=relationship.target_id
        )
        
        # Create relationship with properties
        props_string = ", ".join([f"{k}: ${k}" for k in relationship.properties.keys()])
        if props_string:
            props_string = " {" + props_string + "}"
        else:
            props_string = ""
            
        query = """
        MATCH (source:{source_type} {{id: $source_id}}), 
              (target:{target_type} {{id: $target_id}})
        CREATE (source)-[r:{rel_type}{props}]->(target)
        RETURN r
        """.format(
            source_type=relationship.source_type,
            target_type=relationship.target_type,
            rel_type=relationship.relationship_type,
            props=props_string
        )
        
        params = {
            "source_id": relationship.source_id,
            "target_id": relationship.target_id,
            **relationship.properties
        }
        
        result = session.run(query, params)
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create relationship")
    
    return {"message": "Relationship created successfully", "relationship": relationship.dict()}

# Simplified convenience endpoint for linking trials to drugs
@app.post("/trials/{trial_id}/link-drug/{drug_id}")
def link_trial_to_drug(
    trial_id: str, 
    drug_id: str,
    driver=Depends(get_neo4j_driver),
    db=Depends(get_db)
):
    # Verify trial exists
    trial = db.trials.find_one({"id": trial_id})
    if not trial:
        raise HTTPException(status_code=404, detail=f"Trial with ID {trial_id} not found")
    
    # Verify drug exists
    drug = db.drugs.find_one({"id": drug_id})
    if not drug:
        raise HTTPException(status_code=404, detail=f"Drug with ID {drug_id} not found")
    
    # Create relationship
    with driver.session() as session:
        session.run(
            """
            MERGE (trial:ClinicalTrial {id: $trial_id})
            MERGE (drug:Drug {id: $drug_id})
            MERGE (drug)-[r:TESTED_IN]->(trial)
            RETURN r
            """,
            trial_id=trial_id,
            drug_id=drug_id
        )
    
    return {"message": f"Drug {drug_id} linked to trial {trial_id}"}

# Search endpoint
@app.get("/search", response_model=List[ClinicalTrial])
def search_trials(
    phase: Optional[TrialPhase] = None,
    status: Optional[TrialStatus] = None,
    sponsor: Optional[str] = None,
    drug_name: Optional[str] = None,
    start_date_from: Optional[datetime] = None,
    start_date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db),
    driver=Depends(get_neo4j_driver)
):
    # Start with basic MongoDB query
    query = {}
    
    if phase:
        query["phase"] = phase
    if status:
        query["status"] = status
    if sponsor:
        query["sponsor"] = {"$regex": sponsor, "$options": "i"}  # Case-insensitive search
    
    # Date range query
    if start_date_from or start_date_to:
        query["start_date"] = {}
        if start_date_from:
            query["start_date"]["$gte"] = start_date_from.isoformat()
        if start_date_to:
            query["start_date"]["$lte"] = start_date_to.isoformat()
    
    # Basic search using MongoDB
    if not drug_name:
        trials = list(db.trials.find(query).skip(skip).limit(limit))
        
        # Convert ObjectId and dates
        for trial in trials:
            trial["_id"] = str(trial["_id"])
            trial["start_date"] = datetime.fromisoformat(trial["start_date"])
            if trial.get("end_date"):
                trial["end_date"] = datetime.fromisoformat(trial["end_date"])
            trial["created_at"] = datetime.fromisoformat(trial["created_at"])
            trial["updated_at"] = datetime.fromisoformat(trial["updated_at"])
        
        return trials
    
    # If drug name is specified, use Neo4j for relationship query
    else:
        with driver.session() as session:
            result = session.run(
                """
                MATCH (d:Drug)-[:TESTED_IN]->(t:ClinicalTrial)
                WHERE d.name =~ $drug_name
                RETURN t.id as trial_id
                """,
                drug_name=f"(?i).*{drug_name}.*"  # Case-insensitive regex
            )
            
            trial_ids = [record["trial_id"] for record in result]
            
        if not trial_ids:
            return []
            
        # Add trial IDs to query
        query["id"] = {"$in": trial_ids}
        trials = list(db.trials.find(query).skip(skip).limit(limit))
        
        # Convert ObjectId and dates
        for trial in trials:
            trial["_id"] = str(trial["_id"])
            trial["start_date"] = datetime.fromisoformat(trial["start_date"])
            if trial.get("end_date"):
                trial["end_date"] = datetime.fromisoformat(trial["end_date"])
            trial["created_at"] = datetime.fromisoformat(trial["created_at"])
            trial["updated_at"] = datetime.fromisoformat(trial["updated_at"])
        
        return trials

# Add a new endpoint for semantic search
@app.get("/semantic-search")
def semantic_search(query: str, top_k: int = 5, db=Depends(get_db)):
    global vector_store
    
    # Check if vector store is initialized
    if vector_store is None or vector_store.index is None:
        # Try to initialize it
        try:
            vector_store = TrialVectorStore()
            vector_store.create_index()
            
            # Add existing trials
            trials = list(db.trials.find({}))
            for trial in trials:
                trial["_id"] = str(trial["_id"])
            vector_store.add_trials(trials)
            vector_store.save()
        except Exception as e:
            raise HTTPException(status_code=500, 
                               detail=f"Failed to initialize vector store: {str(e)}")
    
    try:
        # Search vector store
        results = vector_store.search(query, top_k)
        
        # Get full trial data
        trial_ids = [r["trial_id"] for r in results]
        trials = []
        
        for trial_id in trial_ids:
            trial = db.trials.find_one({"id": trial_id})
            if trial:
                trial["_id"] = str(trial["_id"])
                trial["similarity_score"] = next(r["similarity_score"] for r in results if r["trial_id"] == trial_id)
                
                # Convert dates back to string
                if isinstance(trial.get("start_date"), datetime):
                    trial["start_date"] = trial["start_date"].isoformat()
                if isinstance(trial.get("end_date"), datetime):
                    trial["end_date"] = trial["end_date"].isoformat()
                if isinstance(trial.get("created_at"), datetime):
                    trial["created_at"] = trial["created_at"].isoformat()
                if isinstance(trial.get("updated_at"), datetime):
                    trial["updated_at"] = trial["updated_at"].isoformat()
                    
                trials.append(trial)
        
        return trials
    except Exception as e:
        raise HTTPException(status_code=500, 
                           detail=f"Semantic search failed: {str(e)}")

# Add this endpoint to force a vector store refresh
@app.post("/refresh-vector-store")
def refresh_vector_store(db=Depends(get_db)):
    global vector_store
    
    try:
        # Create new vector store
        vector_store = TrialVectorStore()
        vector_store.create_index()
        
        # Add all trials
        trials = list(db.trials.find({}))
        for trial in trials:
            trial["_id"] = str(trial["_id"])
        
        if trials:
            vector_store.add_trials(trials)
            vector_store.save()
            return {"status": "success", "message": f"Refreshed vector store with {len(trials)} trials"}
        else:
            return {"status": "warning", "message": "No trials found to index"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh vector store: {str(e)}")

# Main entry point
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)