import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const Charts = ({ results }) => {
  if (!results || results.length === 0) return null;

  // 1. Contributions over time (by person)
  const getTimelineData = () => {
    const personData = {};
    
    results.forEach(result => {
      const date = result.TRANSACTION_DT;
      const personKey = `${result.search_term || 'Unknown'}`;
      
      if (date && date.length === 8) {
        // Convert MMDDYYYY to YYYY-MM format for grouping
        const year = date.substring(4);
        const month = date.substring(0, 2);
        const yearMonth = `${year}-${month}`;
        
        if (!personData[personKey]) {
          personData[personKey] = {};
        }
        if (!personData[personKey][yearMonth]) {
          personData[personKey][yearMonth] = 0;
        }
        personData[personKey][yearMonth] += Number(result.TRANSACTION_AMT || 0);
      }
    });

    // Get all unique dates
    const allDates = new Set();
    Object.values(personData).forEach(person => {
      Object.keys(person).forEach(date => allDates.add(date));
    });
    const sortedDates = Array.from(allDates).sort();

    // Create datasets for each person
    const colors = [
      'rgb(75, 192, 192)', 'rgb(255, 99, 132)', 'rgb(54, 162, 235)', 
      'rgb(255, 205, 86)', 'rgb(153, 102, 255)', 'rgb(255, 159, 64)'
    ];
    
    const datasets = Object.keys(personData).map((person, index) => ({
      label: person,
      data: sortedDates.map(date => personData[person][date] || 0),
      borderColor: colors[index % colors.length],
      backgroundColor: colors[index % colors.length].replace('rgb', 'rgba').replace(')', ', 0.2)'),
      tension: 0.1
    }));
    
    return {
      labels: sortedDates.map(date => {
        const [year, month] = date.split('-');
        return `${month}/${year}`;
      }),
      datasets
    };
  };

  // 2. Top recipients (by committee ID)
  const getRecipientsData = () => {
    const recipients = {};
    
    results.forEach(result => {
      const cmte = result.CMTE_ID || 'Unknown';
      if (!recipients[cmte]) {
        recipients[cmte] = 0;
      }
      recipients[cmte] += Number(result.TRANSACTION_AMT || 0);
    });

    // Get top 10 recipients
    const sortedRecipients = Object.entries(recipients)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10);

    return {
      labels: sortedRecipients.map(([cmte]) => cmte.substring(0, 15) + '...'),
      datasets: [{
        data: sortedRecipients.map(([, amount]) => amount),
        backgroundColor: [
          'rgba(255, 99, 132, 0.8)',
          'rgba(54, 162, 235, 0.8)',
          'rgba(255, 205, 86, 0.8)',
          'rgba(75, 192, 192, 0.8)',
          'rgba(153, 102, 255, 0.8)',
          'rgba(255, 159, 64, 0.8)',
          'rgba(199, 199, 199, 0.8)',
          'rgba(83, 102, 146, 0.8)',
          'rgba(255, 99, 255, 0.8)',
          'rgba(99, 255, 132, 0.8)'
        ]
      }]
    };
  };

  // 3. Largest contributions
  const getLargestContributions = () => {
    return results
      .sort((a, b) => Number(b.TRANSACTION_AMT || 0) - Number(a.TRANSACTION_AMT || 0))
      .slice(0, 5);
  };

  const recipientsChartOptions = {
    responsive: true,
    plugins: {
      legend: {
        display: false  // Hide legend since committee names are on x-axis
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: function(value) {
            return '$' + value.toLocaleString();
          }
        }
      }
    }
  };

  // You may want to define timelineChartOptions similarly, or reuse recipientsChartOptions

  const timelineData = getTimelineData();
  const recipientsData = getRecipientsData();
  const largestContributions = getLargestContributions();

  return (
    <div className="charts-section">
      <h3>Data Visualizations</h3>
      
      {/* Timeline Chart */}
      <div className="chart-container">
        <h4>Contributions Over Time (by Person)</h4>
        <Line data={timelineData} options={recipientsChartOptions} />
      </div>

      {/* Recipients Chart */}
      <div className="chart-container">
        <h4>Top Recipients (Total from All Contributors)</h4>
        <Bar data={recipientsData} options={recipientsChartOptions} />
      </div>

      {/* Largest Contributions Table */}
      <div className="largest-contributions">
        <h4>🔥 Largest Contributions</h4>
        <div className="large-contributions-grid">
          {largestContributions.map((contribution, index) => (
            <div key={index} className="large-contribution-card">
              <div className="contribution-rank">#{index + 1}</div>
              <div className="contribution-amount">
                ${Number(contribution.TRANSACTION_AMT || 0).toLocaleString()}
              </div>
              <div className="contribution-details">
                <div><strong>{contribution.NAME}</strong></div>
                <div>{contribution.CITY}, {contribution.STATE}</div>
                <div className="contribution-date">
                  {contribution.TRANSACTION_DT ? 
                    `${contribution.TRANSACTION_DT.substring(0,2)}/${contribution.TRANSACTION_DT.substring(2,4)}/${contribution.TRANSACTION_DT.substring(4)}` 
                    : 'N/A'}
                </div>
                <div className="contribution-recipient">→ {contribution.CMTE_ID}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Charts;