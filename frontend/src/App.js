import React, { useState } from 'react';
import axios from 'axios';
import './App.css';
import Charts from './Charts';

function App() {
  const [searchInput, setSearchInput] = useState('');
  const [city, setCity] = useState('');
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // CHANGED: Use PERSON_GROUP_ID for consistent grouping of same person
  const getPersonGroupColor = (result) => {
    const personKey = result.PERSON_GROUP_ID || `${result.FIRST_NAME_RAW}_${result.LAST_NAME_RAW}_${result.CITY}_${result.STATE}`;

    // Hash the personKey
    let hash = 0;
    for (let i = 0; i < personKey.length; i++) {
      const char = personKey.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash |= 0; // Convert to 32-bit int
    }

    // NEW: use hash to generate a unique HSL color
    const hue = Math.abs(hash) % 360;        // gives 0–359
    const saturation = 70;                   // nicer default
    const lightness = 60;                    // readable on white 
    return `hsla(${hue}, ${saturation}%, ${lightness}%, 0.3)`;  // keep alpha similar to before
  };

  const handleSearch = async () => {
    if (!searchInput.trim()) {
      setError('Please enter at least one name');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await axios.post('http://localhost:8000/bulk_search', {
        names: searchInput.split(',').map(name => name.trim()).filter(Boolean),
        city: city || null,
        limit: 50
      });

      setResults(response.data.results || []);
      setSummary(response.data.summary || []);
      } catch (err) {
          console.error('Full error:', err);
          console.error('Error response:', err.response?.data);

          // Check if no results found
          if (err.response?.data?.summary?.every(item => item.matches_found === 0)) {
            const notFoundNames = err.response.data.summary.map(item => item.search_term).join(', ');
            setError(`No contributions found for: ${notFoundNames}`);
          } else {
            setError('Error searching contributions: ' + JSON.stringify(err.response?.data || err.message));
          }
      } finally {
          setLoading(false);
      }
  };

  const exportToCsv = () => {
    if (results.length === 0) return;

    // Convert results to CSV
    const headers = Object.keys(results[0]);
    const csvContent = [
      headers.join(','),
      ...results.map(row => headers.map(header => `"${row[header] || ''}"`).join(','))
    ].join('\n');

    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'political_contributions.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Political Contribution Monitor</h1>
        <p>Search political contributions for compliance monitoring</p>
      </header>

      <main className="search-container">
        <div className="search-form">
          <div className="input-group">
            <label htmlFor="names">Names (comma-separated):</label>
            <input
              id="names"
              type="text"
              placeholder="John Smith, Jane Doe, Paul Paul"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="name-input"
            />
            <small>Enter one or more names separated by commas</small>
          </div>

          <div className="input-group">
            <label htmlFor="city">City (optional):</label>
            <input
              id="city"
              type="text"
              placeholder="New York"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="city-input"
            />
          </div>

          <button 
            onClick={handleSearch} 
            disabled={loading}
            className="search-button"
          >
            {loading ? 'Searching...' : 'Search Contributions'}
          </button>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {summary.length > 0 && (
          <div className="summary-section">
            <h3>Search Summary</h3>
              <div className="summary-grid">
                {summary.map((item, index) => (
                  <div key={index} className="summary-item">
                    <span className="summary-name">{item.search_term}</span>
                    <span className="summary-stats">
                      {item.matches_found} matches (${Number(item.total_amount || 0).toLocaleString()})
                    </span>
                  </div>
                ))}
              </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h3>Results ({results.length} contributions found)</h3>
              <button onClick={exportToCsv} className="export-button">
                Export to CSV
              </button>
            </div>

            <div className="table-container">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>Search Term</th>
                    <th>Name</th>
                    <th>City</th>
                    <th>State</th>
                    <th>Amount</th>
                    <th>Date</th>
                    <th>Recipient</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, index) => {
                    // CHANGED: Use result object directly for consistent coloring
                    const bgColor = getPersonGroupColor(result);
                    
                    return (
                      <tr key={index} style={{ backgroundColor: bgColor }}>
                        <td>{result.search_term}</td>
                        <td>{result.NAME}</td>
                        <td>{result.CITY}</td>
                        <td>{result.STATE}</td>
                        <td>${Number(result.TRANSACTION_AMT || 0).toLocaleString()}</td>
                        <td>{result.TRANSACTION_DT}</td>
                        <td>{result.CMTE_ID}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && results.length === 0 && summary.length === 0 && (
          <div className="no-results">
            Enter names above to search for political contributions
          </div>
        )}
        {results.length > 0 && <Charts results={results} getPersonGroupColor={getPersonGroupColor} />}
      </main>
    </div>
  );
}

export default App;