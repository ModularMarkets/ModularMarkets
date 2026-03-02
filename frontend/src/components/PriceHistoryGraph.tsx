import React, { useEffect, useState, useMemo } from 'react';
import { apiClient, Transaction } from '../api/client';
import './PriceHistoryGraph.css';

interface PriceHistoryGraphProps {
  shopId: string;
  item: string;
}

export const PriceHistoryGraph: React.FC<PriceHistoryGraphProps> = ({ shopId, item }) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTransactions = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getTransactions(shopId, item);
        setTransactions(data.transactions);
        setError(null);
      } catch (err) {
        console.error('Failed to load transactions:', err);
        setError('Failed to load price history');
      } finally {
        setLoading(false);
      }
    };
    loadTransactions();
  }, [shopId, item]);

  // Process transactions for chart
  const chartData = useMemo(() => {
    if (transactions.length === 0) return null;

    // Sort by timestamp (oldest first)
    const sorted = [...transactions].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    // Group by time periods and calculate average prices
    const dataPoints: Array<{ time: number; price: number; buyPrice?: number; sellPrice?: number }> = [];
    
    // For simplicity, use each transaction as a data point
    // In a real implementation, you might want to aggregate by time periods
    sorted.forEach(txn => {
      dataPoints.push({
        time: new Date(txn.timestamp).getTime(),
        price: txn.price,
      });
    });

    return dataPoints;
  }, [transactions]);

  if (loading) {
    return (
      <div className="price-history-graph">
        <h3>Price History</h3>
        <div className="graph-loading">Loading price history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="price-history-graph">
        <h3>Price History</h3>
        <div className="graph-error">{error}</div>
      </div>
    );
  }

  if (!chartData || chartData.length === 0) {
    return (
      <div className="price-history-graph">
        <h3>Price History</h3>
        <div className="graph-empty">No transaction history available</div>
      </div>
    );
  }

  // Calculate chart dimensions and scales
  const width = 800;
  const height = 300;
  const padding = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const prices = chartData.map(d => d.price);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const priceRange = maxPrice - minPrice || 1;
  const pricePadding = priceRange * 0.1;

  const times = chartData.map(d => d.time);
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const timeRange = maxTime - minTime || 1;

  // Scale functions
  const scaleX = (time: number) => 
    padding.left + ((time - minTime) / timeRange) * chartWidth;
  const scaleY = (price: number) => 
    padding.top + chartHeight - ((price - minPrice + pricePadding) / (priceRange + pricePadding * 2)) * chartHeight;

  // Generate path for price line
  const pathData = chartData
    .map((d, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(d.time)} ${scaleY(d.price)}`)
    .join(' ');

  // Generate area path (for fill)
  const areaPath = `M ${scaleX(chartData[0].time)} ${scaleY(chartData[0].price)} ${pathData.substring(1)} L ${scaleX(chartData[chartData.length - 1].time)} ${scaleY(minPrice - pricePadding)} Z`;

  // Format price for display
  const formatPrice = (price: number) => `$${price.toFixed(2)}`;
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Generate Y-axis labels
  const yAxisSteps = 5;
  const yAxisLabels = Array.from({ length: yAxisSteps + 1 }, (_, i) => {
    const price = minPrice - pricePadding + ((maxPrice + pricePadding - (minPrice - pricePadding)) / yAxisSteps) * i;
    return { price, y: scaleY(price) };
  });

  return (
    <div className="price-history-graph">
      <h3>Price History</h3>
      <div className="graph-container">
        <svg width={width} height={height} className="price-chart">
          {/* Grid lines */}
          <defs>
            <linearGradient id="priceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="var(--accent-primary)" stopOpacity="0.3" />
              <stop offset="100%" stopColor="var(--accent-primary)" stopOpacity="0.05" />
            </linearGradient>
          </defs>
          
          {/* Y-axis grid lines */}
          {yAxisLabels.map((label, i) => (
            <g key={i}>
              <line
                x1={padding.left}
                y1={label.y}
                x2={width - padding.right}
                y2={label.y}
                stroke="var(--border-color)"
                strokeWidth="1"
                strokeDasharray="2,2"
                opacity="0.3"
              />
              <text
                x={padding.left - 10}
                y={label.y + 4}
                textAnchor="end"
                fill="var(--text-secondary)"
                fontSize="11"
                fontFamily="JetBrains Mono, monospace"
              >
                {formatPrice(label.price)}
              </text>
            </g>
          ))}

          {/* X-axis */}
          <line
            x1={padding.left}
            y1={height - padding.bottom}
            x2={width - padding.right}
            y2={height - padding.bottom}
            stroke="var(--border-color)"
            strokeWidth="2"
          />

          {/* Y-axis */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={height - padding.bottom}
            stroke="var(--border-color)"
            strokeWidth="2"
          />

          {/* Area fill */}
          <path
            d={areaPath}
            fill="url(#priceGradient)"
          />

          {/* Price line */}
          <path
            d={pathData}
            fill="none"
            stroke="var(--accent-primary)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data points */}
          {chartData.map((point, i) => (
            <circle
              key={i}
              cx={scaleX(point.time)}
              cy={scaleY(point.price)}
              r="3"
              fill="var(--accent-primary)"
              stroke="var(--bg-primary)"
              strokeWidth="2"
              className="data-point"
            />
          ))}

          {/* Tooltip area (invisible, for hover) */}
          {chartData.map((point, i) => (
            <circle
              key={`tooltip-${i}`}
              cx={scaleX(point.time)}
              cy={scaleY(point.price)}
              r="8"
              fill="transparent"
              className="tooltip-area"
            />
          ))}
        </svg>
      </div>
      <div className="graph-stats">
        <div className="stat-item">
          <span className="stat-label">Transactions:</span>
          <span className="stat-value">{transactions.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Min Price:</span>
          <span className="stat-value">{formatPrice(minPrice)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Max Price:</span>
          <span className="stat-value">{formatPrice(maxPrice)}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Avg Price:</span>
          <span className="stat-value">{formatPrice(prices.reduce((a, b) => a + b, 0) / prices.length)}</span>
        </div>
      </div>
    </div>
  );
};


