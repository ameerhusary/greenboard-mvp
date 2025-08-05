# Political Contribution Monitor

A web application that helps financial services firms monitor political contributions for compliance with "pay-to-play" regulations using FEC data.

## Features

- **Name-based Search**: Search for political contributions by first/last name with optional city filtering
- **Bulk Search**: Search multiple names simultaneously (comma-separated format)
- **Fuzzy Matching**: Handles name variations and partial matches
- **Data Visualization**: 
  - Timeline charts showing contributions over time per person
  - Top recipients bar chart
  - Highlighted largest contributions
- **CSV Export**: Export search results for compliance reporting
- **Real-time Results**: Fast search through 4M+ contribution records

## Technology Stack

- **Backend**: Python FastAPI with pandas for data processing
- **Frontend**: React with Chart.js for visualizations
- **Data**: FEC individual contribution records (2017-2018 sample)

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
   pip install fastapi uvicorn pandas fuzzywuzzy python-levenshtein
   ```

3. **Download FEC Data**
   - Download the FEC contribution files from: https://drive.google.com/drive/folders/1JyLpI_JP-b-QqvikBjH2GWnMJIJWWCKx
   - Place the `.txt` files in the `data/` folder

4. **Start the FastAPI server**
   ```bash
   uvicorn api_server:app --reload
   ```
   - Server will run on http://localhost:8000
   - API documentation available at http://localhost:8000/docs

### Frontend Setup

1. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

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

- `POST /bulk_search` - Search for multiple contributors
  ```json
  {
    "names_input": "John Smith, Jane Doe",
    "city": "New York",
    "limit_per_name": 50
  }
  ```

## Project Structure

```
political-contribution-monitor/
├── api_server.py           # FastAPI backend server
├── search_engine.py        # Search logic and data processing
├── extract_data.py         # FEC data loading utilities
├── data/                   # FEC contribution data files
│   ├── file1.txt
│   └── file2.txt
└── frontend/               # React frontend application
    ├── src/
    │   ├── App.js         # Main application component
    │   ├── Charts.js      # Data visualization components
    │   └── App.css        # Styling
    ├── package.json
    └── public/
```

## Data Format

The application processes FEC individual contribution data with fields including:
- Contributor name, city, state, zip code
- Contribution amount and date
- Recipient committee information
- Transaction details and identifiers

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

## Future Development

For future development:
- Use PostgreSQL or similar database instead of in-memory pandas
- Implement proper authentication and rate limiting
- Add error logging and monitoring
- Use production WSGI server (Gunicorn) for FastAPI
- Build and serve React frontend statically

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details