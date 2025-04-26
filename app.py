import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# API base URL
API_URL = "http://localhost:8000"

# Set page config
st.set_page_config(
    page_title="Novo Nordisk Trial Repository",
    page_icon="💊",
    layout="wide"
)

# Title and introduction
st.title("Novo Nordisk Clinical Trial Repository")
st.markdown("Manage and explore clinical trials data using this interface.")

# Sidebar navigation
page = st.sidebar.selectbox(
    "Select Page",
    ["View Trials", "Add Trial", "Search Trials", "Manage Relationships"]
)

# Helper function to format dates for display
def format_date(date_str):
    if not date_str:
        return None
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime("%Y-%m-%d")
    except:
        return date_str

# View Trials Page
if page == "View Trials":
    st.header("Clinical Trials")
    
    # Fetch trials from API
    with st.spinner("Loading trials..."):
        try:
            response = requests.get(f"{API_URL}/trials")
            if response.status_code == 200:
                trials = response.json()
                
                if not trials:
                    st.info("No trials found in the database.")
                else:
                    # Convert to DataFrame for better display
                    df = pd.DataFrame([{
                        "ID": t["id"],
                        "Title": t["title"],
                        "Phase": t["phase"],
                        "Status": t["status"],
                        "Start Date": format_date(t["start_date"]),
                        "End Date": format_date(t["end_date"]) if t.get("end_date") else "Not set",
                        "Sponsor": t["sponsor"]
                    } for t in trials])
                    
                    st.dataframe(df)
                    
                    # Trial details section
                    st.subheader("Trial Details")
                    trial_id = st.selectbox("Select a trial to view details:", 
                                            [t["id"] for t in trials],
                                            format_func=lambda x: next((t["title"] for t in trials if t["id"] == x), x))
                    
                    if trial_id:
                        selected_trial = next((t for t in trials if t["id"] == trial_id), None)
                        if selected_trial:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Title:** {selected_trial['title']}")
                                st.markdown(f"**Phase:** {selected_trial['phase']}")
                                st.markdown(f"**Status:** {selected_trial['status']}")
                                st.markdown(f"**NCT ID:** {selected_trial.get('nct_id', 'N/A')}")
                                st.markdown(f"**Start Date:** {format_date(selected_trial['start_date'])}")
                                st.markdown(f"**End Date:** {format_date(selected_trial.get('end_date', '')) or 'Not set'}")
                                st.markdown(f"**Sponsor:** {selected_trial['sponsor']}")
                            
                            with col2:
                                st.markdown("**Description:**")
                                st.markdown(selected_trial['description'])
                                st.markdown(f"**Primary Outcome:** {selected_trial['primary_outcome']}")
                                
                                st.markdown("**Secondary Outcomes:**")
                                for outcome in selected_trial.get('secondary_outcomes', []):
                                    st.markdown(f"- {outcome}")
                                
                                st.markdown("**Locations:**")
                                for location in selected_trial.get('locations', []):
                                    st.markdown(f"- {location}")
                            
                            # Inclusion/Exclusion criteria
                            st.subheader("Eligibility Criteria")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Inclusion Criteria:**")
                                for criteria in selected_trial.get('inclusion_criteria', []):
                                    st.markdown(f"- {criteria}")
                            
                            with col2:
                                st.markdown("**Exclusion Criteria:**")
                                for criteria in selected_trial.get('exclusion_criteria', []):
                                    st.markdown(f"- {criteria}")
                            
                            # Delete trial button
                            if st.button("Delete This Trial", key="delete_trial"):
                                with st.spinner("Deleting trial..."):
                                    delete_response = requests.delete(f"{API_URL}/trials/{trial_id}")
                                    if delete_response.status_code == 204:
                                        st.success("Trial deleted successfully!")
                                        st.experimental_rerun()
                                    else:
                                        st.error(f"Failed to delete trial: {delete_response.text}")
            else:
                st.error(f"Failed to fetch trials: {response.text}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the API. Make sure the FastAPI server is running.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

# Add Trial Page
elif page == "Add Trial":
    st.header("Add New Clinical Trial")
    
    with st.form("trial_form"):
        title = st.text_input("Trial Title", max_chars=200)
        nct_id = st.text_input("NCT ID (optional)")
        
        col1, col2 = st.columns(2)
        with col1:
            phase = st.selectbox("Phase", ["1", "2", "3", "4"])
            status = st.selectbox("Status", ["planned", "recruiting", "active", "completed", "terminated"])
        
        with col2:
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date (optional)")
        
        description = st.text_area("Description", height=100)
        primary_outcome = st.text_input("Primary Outcome")
        
        st.subheader("Secondary Outcomes")
        secondary_outcomes = []
        for i in range(3):  # Allow up to 3 secondary outcomes
            outcome = st.text_input(f"Secondary Outcome {i+1}", key=f"secondary_{i}")
            if outcome:
                secondary_outcomes.append(outcome)
        
        st.subheader("Inclusion Criteria")
        inclusion_criteria = []
        for i in range(3):  # Allow up to 3 inclusion criteria
            criteria = st.text_input(f"Inclusion Criteria {i+1}", key=f"inclusion_{i}")
            if criteria:
                inclusion_criteria.append(criteria)
        
        st.subheader("Exclusion Criteria")
        exclusion_criteria = []
        for i in range(3):  # Allow up to 3 exclusion criteria
            criteria = st.text_input(f"Exclusion Criteria {i+1}", key=f"exclusion_{i}")
            if criteria:
                exclusion_criteria.append(criteria)
        
        st.subheader("Locations")
        locations = []
        for i in range(3):  # Allow up to 3 locations
            location = st.text_input(f"Location {i+1}", key=f"location_{i}")
            if location:
                locations.append(location)
        
        sponsor = st.text_input("Sponsor")
        
        submit_button = st.form_submit_button("Create Trial")
        
    if submit_button:
        # Validate required fields
        if not (title and phase and status and start_date and description and primary_outcome and sponsor):
            st.error("Please fill in all required fields.")
        else:
            # Create trial payload
            trial_data = {
                "title": title,
                "phase": phase,
                "status": status,
                "start_date": start_date.isoformat() + "T00:00:00",
                "description": description,
                "primary_outcome": primary_outcome,
                "sponsor": sponsor,
                "secondary_outcomes": secondary_outcomes,
                "inclusion_criteria": inclusion_criteria,
                "exclusion_criteria": exclusion_criteria,
                "locations": locations
            }
            
            # Add optional fields if present
            if nct_id:
                trial_data["nct_id"] = nct_id
            if end_date and end_date > start_date:
                trial_data["end_date"] = end_date.isoformat() + "T00:00:00"
            
            # Submit to API
            with st.spinner("Creating trial..."):
                try:
                    response = requests.post(f"{API_URL}/trials", json=trial_data)
                    if response.status_code == 201:
                        st.success("Trial created successfully!")
                        st.json(response.json())
                    else:
                        st.error(f"Failed to create trial: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the API. Make sure the FastAPI server is running.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

# Search Trials Page
elif page == "Search Trials":
    st.header("Search Clinical Trials")
    
    col1, col2 = st.columns(2)
    
    with col1:
        phase = st.selectbox("Phase", ["", "1", "2", "3", "4"])
        status = st.selectbox("Status", ["", "planned", "recruiting", "active", "completed", "terminated"])
    
    with col2:
        sponsor = st.text_input("Sponsor (contains)")
        drug_name = st.text_input("Drug Name (contains)")
    
    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date_from = st.date_input("Start Date From", value=None)
    with date_col2:
        start_date_to = st.date_input("Start Date To", value=None)
    
    if st.button("Search"):
        # Build query parameters
        params = {}
        if phase:
            params["phase"] = phase
        if status:
            params["status"] = status
        if sponsor:
            params["sponsor"] = sponsor
        if drug_name:
            params["drug_name"] = drug_name
        if start_date_from:
            params["start_date_from"] = start_date_from.isoformat() + "T00:00:00"
        if start_date_to:
            params["start_date_to"] = start_date_to.isoformat() + "T00:00:00"
        
        # Execute search
        with st.spinner("Searching..."):
            try:
                response = requests.get(f"{API_URL}/search", params=params)
                if response.status_code == 200:
                    trials = response.json()
                    
                    if not trials:
                        st.info("No trials match your search criteria.")
                    else:
                        st.success(f"Found {len(trials)} trials matching your criteria.")
                        
                        # Display results
                        df = pd.DataFrame([{
                            "ID": t["id"],
                            "Title": t["title"],
                            "Phase": t["phase"],
                            "Status": t["status"],
                            "Start Date": format_date(t["start_date"]),
                            "End Date": format_date(t["end_date"]) if t.get("end_date") else "Not set",
                            "Sponsor": t["sponsor"]
                        } for t in trials])
                        
                        st.dataframe(df)
                else:
                    st.error(f"Search failed: {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the API. Make sure the FastAPI server is running.")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Manage Relationships Page
elif page == "Manage Relationships":
    st.header("Manage Trial Relationships")
    
    tab1, tab2 = st.tabs(["Link Drug to Trial", "Create Custom Relationship"])
    
    with tab1:
        st.subheader("Link Drug to Trial")
        
        # Try to get trials
        try:
            trials_response = requests.get(f"{API_URL}/trials")
            trials = trials_response.json() if trials_response.status_code == 200 else []
            
            if not trials:
                st.warning("No trials available. Please create a trial first.")
            else:
                # Create a simple form for drug creation
                st.markdown("#### Create a Drug")
                with st.form("drug_form"):
                    drug_name = st.text_input("Drug Name")
                    molecule_type = st.text_input("Molecule Type")
                    moa = st.text_input("Mechanism of Action")
                    targets = st.text_input("Target Proteins (comma separated)")
                    
                    create_drug = st.form_submit_button("Create Drug")
                
                if create_drug and drug_name and molecule_type and moa:
                    # We'll need to create a drug record directly in MongoDB
                    # This would normally be done through an API endpoint
                    st.info("This would create a drug record in MongoDB. For this demo, we'll simulate it.")
                    
                    # Display simulated drug
                    drug_id = "drug-" + drug_name.lower().replace(" ", "-")
                    st.success(f"Drug created with ID: {drug_id}")
                    
                    # Link drug to trial
                    st.markdown("#### Link Drug to Trial")
                    trial_id = st.selectbox(
                        "Select Trial",
                        [t["id"] for t in trials],
                        format_func=lambda x: next((t["title"] for t in trials if t["id"] == x), x)
                    )
                    
                    if st.button("Link Drug to Trial"):
                        with st.spinner("Creating relationship..."):
                            try:
                                # Simulate relationship creation
                                st.success(f"Drug {drug_id} linked to trial {trial_id}")
                                
                                # This would use the actual API in a real implementation:
                                # response = requests.post(f"{API_URL}/trials/{trial_id}/link-drug/{drug_id}")
                                # if response.status_code == 200:
                                #     st.success(f"Drug {drug_id} linked to trial {trial_id}")
                                # else:
                                #     st.error(f"Failed to link drug to trial: {response.text}")
                            except Exception as e:
                                st.error(f"An error occurred: {str(e)}")
        except requests.exceptions.ConnectionError:
            st.error("Could not connect to the API. Make sure the FastAPI server is running.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
    
    with tab2:
        st.subheader("Create Custom Relationship")
        
        with st.form("relationship_form"):
            source_id = st.text_input("Source ID")
            source_type = st.text_input("Source Type", value="Drug")
            target_id = st.text_input("Target ID")
            target_type = st.text_input("Target Type", value="ClinicalTrial")
            relationship_type = st.text_input("Relationship Type", value="USED_IN")
            
            # Properties as key-value pairs
            st.markdown("#### Relationship Properties")
            prop_key1 = st.text_input("Property 1 Key", value="dosage")
            prop_value1 = st.text_input("Property 1 Value", value="")
            prop_key2 = st.text_input("Property 2 Key", value="frequency")
            prop_value2 = st.text_input("Property 2 Value", value="")
            
            create_rel = st.form_submit_button("Create Relationship")
        
        if create_rel:
            if not (source_id and source_type and target_id and target_type and relationship_type):
                st.error("Please fill in all required fields.")
            else:
                # Create relationship payload
                rel_data = {
                    "source_id": source_id,
                    "source_type": source_type,
                    "target_id": target_id,
                    "target_type": target_type,
                    "relationship_type": relationship_type,
                    "properties": {}
                }
                
                # Add properties if provided
                if prop_key1 and prop_value1:
                    rel_data["properties"][prop_key1] = prop_value1
                if prop_key2 and prop_value2:
                    rel_data["properties"][prop_key2] = prop_value2
                
                # Submit to API
                with st.spinner("Creating relationship..."):
                    try:
                        response = requests.post(f"{API_URL}/relationships", json=rel_data)
                        if response.status_code == 201:
                            st.success("Relationship created successfully!")
                            st.json(response.json())
                        else:
                            st.error(f"Failed to create relationship: {response.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to the API. Make sure the FastAPI server is running.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

# Instructions in sidebar
with st.sidebar:
    st.markdown("## Instructions")
    st.markdown("""
    1. Make sure the API server is running
    2. Use the navigation to switch between pages
    3. View, create, and search for trials
    4. Manage relationships between trials and drugs
    """)
    
    st.markdown("---")
    st.markdown("### API Status")
    
    # Check API connection
    try:
        health_response = requests.get(f"{API_URL}/health")
        if health_response.status_code == 200:
            st.success("API is online ✅")
            health_data = health_response.json()
            st.markdown(f"Server time: {health_data.get('timestamp', 'Unknown')}")
        else:
            st.error("API is not responding correctly ❌")
    except:
        st.error("Cannot connect to API ❌")
        st.markdown("Make sure the FastAPI server is running on http://localhost:8000") 