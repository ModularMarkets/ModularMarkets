import React from 'react';
import { MerchantInfo } from '../api/client';
import './MerchantCard.css';

interface MerchantCardProps {
  merchant: MerchantInfo;
  shopId: string;
  onClick: () => void;
}

export const MerchantCard: React.FC<MerchantCardProps> = ({ merchant, onClick }) => {
  return (
    <div className="merchant-card" onClick={onClick}>
      <div className="merchant-card-header">
        <h3 className="merchant-item-name">{merchant.item}</h3>
        <span className="merchant-algorithm">{merchant.algorithm_name}</span>
      </div>
      <div className="merchant-card-prices">
        <div className="price-row">
          <span className="price-label">Buy:</span>
          <span className="price-value buy-price">${merchant.buy_price.toFixed(2)}</span>
        </div>
        <div className="price-row">
          <span className="price-label">Sell:</span>
          <span className="price-value sell-price">${merchant.sell_price.toFixed(2)}</span>
        </div>
      </div>
      <div className="merchant-card-caps">
        <span className="cap-info">Buy Cap: {merchant.buy_cap}</span>
        <span className="cap-info">Sell Cap: {merchant.sell_cap}</span>
      </div>
    </div>
  );
};

