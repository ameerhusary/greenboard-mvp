# Political Contribution Monitor

A web application that helps financial services firms monitor political contributions of their employees for compliance with "pay-to-play" regulations using FEC data.

## Features

- **Fast Name-based Search**: Lightning-fast search through 4M+ contribution records using optimized SQLite database with strategic indexing
- **Bulk Search**: Search multiple names simultaneously (comma-separated format) with connection reuse optimization
- **Smart Fuzzy Matching**: Multi-tier search strategy (person group ID → normalized names → exact → initials → partial matching)
- **Advanced Name Normalization**: Handles titles, suffixes, initials, and name variations consistently
- **Data Visualization**: 
  - Timeline charts showing contributions over time per person
  - Top recipients bar chart
  - Highlighted largest contributions with person grouping for consistent identification
- **CSV Export**: Export search results with person group IDs for compliance reporting
- **Real-time Results**: Sub-second search performance through optimized database queries

## Technology Stack
- **Backend**: Python FastAPI with SQLite for persistent storage and optimized search performance
- **Frontend**: React with Chart.js for interactive visualizations
- **Data**: FEC individual contribution records (2017-2018 sample) with normalized indexing
- **Search**: Multi-strategy search engine with person group identification and connection pooling

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+
- Git

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/ameerhusary/greenboard-mvp.git
   cd greenboard-mvp
   ```

2. **Install Python dependencies**
   ```bash
   pip install fastapi uvicorn pandas sqlite3
   ```

3. **Download FEC Data**
   - Download the FEC contribution files from: https://drive.google.com/drive/folders/1JyLpI_JP-b-QqvikBjH2GWnMJIJWWCKx
   - Place the `.txt` files in the `data/` folder

4. **Create the optimized SQLite Database**
   - Run the following in terminal 1:  
   ```bash
   python build_sqlite_db.py 
   ```
   - This creates `contributions.db` with optimized indexes for fast search performance

5. **Start the FastAPI server**
   ```bash
   python -m uvicorn api_server:app --reload
   ```
   - Server will run on http://localhost:8000
   - API documentation available at http://localhost:8000/docs

### Frontend Setup

1. **Install Node.js dependencies**
   - Open another terminal, terminal 2, and run the following:
   ```bash
   cd frontend
   npm install
   ```
   - NOTE: keep both terminals 1 and 2 running

2. **Start the React development server**
   ```bash
   npm start
   ```
   - Application will open at http://localhost:3000

## Usage

### Single Name Search
```
Search: John Smith
City (optional): New York
```

### Bulk Search
```
Search: John Smith, Jane Doe, Paul Paul
City (optional): [leave blank for all cities]
```

### API Endpoints

- `POST /bulk_search` - Unified endpoint for single and multiple contributor searches
  ```json
  {
    "names_input": "John Smith, Jane Doe",
    "city": "New York",
    "limit_per_name": 50
  }
  ```

## Project Structure

```
GREENBOARD_MVP/
├── api_server.py           # FastAPI backend server
├── search_engine.py        # Optimized search engine with SQLite and person grouping
├── extract_data.py         # Data extraction and normalization with person group IDs
├── build_sqlite_db.py      # Script to build optimized SQLite database from FEC data
├── contributions.db        # SQLite database with indexed FEC data (created by build script)
├── data/                   # FEC contribution data files
│   └── *.txt
└── frontend/               # React frontend application
   └── src/
       ├── App.js         # Main application component
       ├── Charts.js      # Data visualization components
       └── App.css        # Styling

```

## Performance Optimizations

- **Person Group IDs**: Consistent identification across searches for the same individual
- **Strategic Indexing**: Composite indexes on normalized names and person group IDs
- **Connection Reuse**: Single database connection for bulk operations
- **Multi-tier Search**: Fastest strategies first (person group ID → normalized → raw → fuzzy)
- **Optimized Queries**: Prepared statements and efficient SQL patterns

## Data Format

The application processes FEC individual contribution data with fields including:
- Contributor name, city, state, zip code
- Contribution amount and date
- Recipient committee information
- Transaction details and identifiers
- **Person Group ID**: Normalized identifier for consistent person tracking

## Development

### Running Tests
```bash
# Test API endpoints
curl -X POST "http://localhost:8000/bulk_search" \
     -H "Content-Type: application/json" \
     -d '{"names_input": "John Smith", "city": null, "limit_per_name": 10}'
```

### Adding New Features
- Backend logic: Modify `search_engine.py`
- API endpoints: Update `api_server.py`
- Frontend features: Update `App.js` or create new components
- Visualizations: Modify `Charts.js`

## Architecture Notes

- **SQLite Primary**: Optimized database with strategic indexing for fast searches
- **Pandas Fallback**: Available for development/testing when SQLite is unavailable
- **Unified API**: Single `bulk_search` endpoint handles both individual and bulk searches
- **Person Consistency**: Person group IDs ensure the same individual is tracked consistently across searches

## Future Development

- Migrate from local SQLite to managed PostgreSQL for multi-user production deployment
- Implement authentication and role-based access control
- Add real-time FEC data updates and automated compliance alerts
- Scale to handle enterprise-level concurrent users and larger datasets

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details