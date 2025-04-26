# Novo Nordisk Metadata Repository

A comprehensive clinical trial metadata management system with graph relationship capabilities.

## Overview

This application provides a robust platform for managing clinical trial data with advanced relationship modeling. It combines the strengths of document and graph databases to offer flexible storage and powerful query capabilities.

## Tech Stack

- **Backend API**: FastAPI
- **Document Database**: MongoDB
- **Graph Database**: Neo4j
- **Frontend**: Streamlit
- **Language**: Python 3.8+

## Features

- Complete CRUD operations for clinical trials
- Relationship management between trials, drugs, and other entities
- Advanced search with multiple filtering options
- User-friendly web interface
- Hybrid database architecture (document + graph)

## Installation

### Prerequisites

- Python 3.8+
- MongoDB
- Neo4j

### Setup

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/novo-nordisk-mdr.git
   cd novo-nordisk-mdr
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables by creating a `.env` file:

   ```
   # MongoDB Configuration
   MONGODB_URI=mongodb://localhost:27017/yourdatabase
   MONGODB_DB=yourdatabase

   # Neo4j Configuration
   NEO4J_URI=neo4j://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=yourpassword
   ```

## Running the Application

1. Start the API server:

   ```
   python Project.py
   ```

2. In a separate terminal, start the Streamlit frontend:

   ```
   streamlit run app.py
   ```

3. Open your browser and navigate to:
   - Frontend: http://localhost:8501
   - API Documentation: http://localhost:8000/docs

## API Documentation

The API provides the following endpoints:

### Health Check

- `GET /health` - Check the API status

### Clinical Trials

- `POST /trials` - Create a new trial
- `GET /trials` - List all trials (with optional filters)
- `GET /trials/{trial_id}` - Get a specific trial
- `PUT /trials/{trial_id}` - Update a trial
- `DELETE /trials/{trial_id}` - Delete a trial

### Relationships

- `POST /relationships` - Create a new relationship
- `POST /trials/{trial_id}/link-drug/{drug_id}` - Link a drug to a trial

### Search

- `GET /search` - Search trials with various filters

## Architecture

### Data Model

The system uses the following core models:

- **ClinicalTrial**: Represents a clinical trial with all its metadata
- **DrugCompound**: Contains information about pharmaceutical compounds
- **Relationship**: Defines connections between entities in the graph database

### Database Architecture

This project implements a hybrid database approach:

- **MongoDB**: Stores complete documents with all trial details, optimized for complex document storage and retrieval
- **Neo4j**: Manages relationships between entities, providing powerful graph query capabilities

This design leverages the strengths of both database types, allowing for complex document management and sophisticated relationship queries.

## User Interface

The Streamlit frontend provides:

1. **View Trials**: Browse all clinical trials with detailed information
2. **Add Trial**: Create new clinical trials with a comprehensive form
3. **Search Trials**: Find trials using multiple filters
4. **Manage Relationships**: Create and manage relationships between entities

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
