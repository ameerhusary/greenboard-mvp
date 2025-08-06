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

const Charts = ({ results, getPersonGroupColor }) => {
  if (!results || results.length === 0) return null;

  // CHANGED: Helper function to get person key for consistent grouping
  const getPersonKey = (result) => {
    if (result.PERSON_GROUP_ID) {
      return result.PERSON_GROUP_ID.toLowerCase();
    }
    // Fallback to raw fields if PERSON_GROUP_ID is missing
    return `${result.FIRST_NAME_RAW || ''}_${result.LAST_NAME_RAW || ''}_${result.CITY || ''}_${result.STATE || ''}`.toLowerCase();
  };

  // CHANGED: Helper function to convert rgba to rgb
  const convertToRgb = (rgbaColor) => {
    return rgbaColor.replace('rgba', 'rgb').replace(', 0.3)', ')');
  };

  // 1. Contributions over time (by person with city)
  const getTimelineData = () => {
    const personData = {};
    
    results.forEach(result => {
      const date = result.TRANSACTION_DT;
      // CHANGED: Use consistent person grouping
      const personKey = getPersonKey(result);
      
      if (date && date.length === 8) {
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

    // CHANGED: Use consistent color function for datasets
    const datasets = Object.keys(personData).map((personKey) => {
      // Find a result for this person to get consistent color
      const sampleResult = results.find(r => getPersonKey(r) === personKey);
      const color = sampleResult ? convertToRgb(getPersonGroupColor(sampleResult)) : 'rgb(75, 192, 192)';
      
      return {
        label: personKey,
        data: sortedDates.map(date => personData[personKey][date] || 0),
        borderColor: color,
        backgroundColor: color.replace('rgb', 'rgba').replace(')', ', 0.2)'),
        tension: 0.1
      };
    });
    
    return {
      labels: sortedDates.map(date => {
        const [year, month] = date.split('-');
        return `${month}/${year}`;
      }),
      datasets
    };
  };

  // 2. Top recipients (color-coded by contributor)
  const getRecipientsData = () => {
    const recipients = {};
    const contributorColors = {};
    
    // CHANGED: Get unique contributors using consistent grouping and assign colors
    const uniqueContributors = [...new Set(results.map(r => getPersonKey(r)))];
    
    uniqueContributors.forEach((personKey) => {
      // Find a result for this person to get consistent color
      const sampleResult = results.find(r => getPersonKey(r) === personKey);
      contributorColors[personKey] = sampleResult ? getPersonGroupColor(sampleResult) : 'rgba(75, 192, 192, 0.8)';
    });
    
    // Group by recipient and track which contributors gave to each
    results.forEach(result => {
      const cmte = result.CMTE_ID || 'Unknown';
      const contributor = getPersonKey(result);
      
      if (!recipients[cmte]) {
        recipients[cmte] = { total: 0, contributors: {} };
      }
      if (!recipients[cmte].contributors[contributor]) {
        recipients[cmte].contributors[contributor] = 0;
      }
      
      const amount = Number(result.TRANSACTION_AMT || 0);
      recipients[cmte].total += amount;
      recipients[cmte].contributors[contributor] += amount;
    });

    // Get top 10 recipients
    const sortedRecipients = Object.entries(recipients)
      .sort(([,a], [,b]) => b.total - a.total)
      .slice(0, 10);

    // Create stacked bar chart data
    const datasets = uniqueContributors.map(contributor => ({
      label: contributor,
      data: sortedRecipients.map(([cmte, data]) => data.contributors[contributor] || 0),
      backgroundColor: contributorColors[contributor]
    }));

    return {
      labels: sortedRecipients.map(([cmte]) => cmte.substring(0, 15) + '...'),
      datasets
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
        position: 'top'  // Show legend to identify contributors
      }
    },
    scales: {
      x: {
        stacked: true
      },
      y: {
        stacked: true,
        beginAtZero: true,
        ticks: {
          callback: function(value) {
            return '$' + value.toLocaleString();
          }
        }
      }
    }
  };

  const timelineData = getTimelineData();
  const recipientsData = getRecipientsData();
  const largestContributions = getLargestContributions();

  return (
    <div className="charts-section">
      <h3>Data Visualizations</h3>
      
      {/* Timeline Chart */}
      <div className="chart-container">
        <h4>Contributions Over Time (by Person & Location)</h4>
        <Line data={timelineData} options={recipientsChartOptions} />
      </div>

      {/* Recipients Chart */}
      <div className="chart-container">
        <h4>Top Recipients (Stacked by Contributor)</h4>
        <Bar data={recipientsData} options={recipientsChartOptions} />
      </div>

      {/* Largest Contributions Table */}
      <div className="largest-contributions">
        <h4>🔥 Largest Contributions</h4>
        <div className="large-contributions-grid">
          {largestContributions.map((contribution, index) => {
            // CHANGED: Apply consistent colors to largest contributions cards
            const bgColor = getPersonGroupColor(contribution);
            
            return (
              <div key={index} className="large-contribution-card" style={{ backgroundColor: bgColor }}>
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
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Charts;