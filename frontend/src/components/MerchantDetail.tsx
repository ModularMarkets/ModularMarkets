import React, { useState, useEffect } from 'react';
import { MerchantInfo, apiClient } from '../api/client';
import { useApp } from '../context/AppContext';
import './Modal.css';
import './MerchantDetail.css';

interface MerchantDetailProps {
  merchant: MerchantInfo;
  shopId: string;
  onClose: () => void;
}

export const MerchantDetail: React.FC<MerchantDetailProps> = ({ merchant: initialMerchant, shopId, onClose }) => {
  const { currentUser, refreshUsers, refreshShops } = useApp();
  const [merchant, setMerchant] = useState<MerchantInfo>(initialMerchant);
  const [stock, setStock] = useState<number | null>(null);
  const [buyQuantity, setBuyQuantity] = useState(1);
  const [sellQuantity, setSellQuantity] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loadingStock, setLoadingStock] = useState(true);

  // Update merchant when prop changes
  useEffect(() => {
    setMerchant(initialMerchant);
  }, [initialMerchant]);

  useEffect(() => {
    const loadStock = async () => {
      try {
        const data = await apiClient.getStock(shopId, merchant.item);
        setStock(data.stock);
      } catch (err) {
        console.error('Failed to load stock:', err);
        setStock(-1);
      } finally {
        setLoadingStock(false);
      }
    };
    loadStock();
  }, [shopId, merchant.item]);

  const handleBuy = async () => {
    if (!currentUser) {
      setError('Please select a user first');
      return;
    }
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const result = await apiClient.buyItem(shopId, merchant.item, buyQuantity, currentUser.username);
      setSuccess(result.message);
      // Update merchant with new prices from response
      if (result.merchant) {
        setMerchant(result.merchant);
      }
      await refreshUsers();
      await refreshShops(); // Refresh shops to update merchant list
      // Reload stock
      const stockData = await apiClient.getStock(shopId, merchant.item);
      setStock(stockData.stock);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to buy item');
    } finally {
      setLoading(false);
    }
  };

  const handleSell = async () => {
    if (!currentUser) {
      setError('Please select a user first');
      return;
    }
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const result = await apiClient.sellItem(shopId, merchant.item, sellQuantity, currentUser.username);
      setSuccess(result.message);
      // Update merchant with new prices from response
      if (result.merchant) {
        setMerchant(result.merchant);
      }
      await refreshUsers();
      await refreshShops(); // Refresh shops to update merchant list
      // Reload stock
      const stockData = await apiClient.getStock(shopId, merchant.item);
      setStock(stockData.stock);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to sell item');
    } finally {
      setLoading(false);
    }
  };

  const adjustBuyQuantity = (delta: number) => {
    const newQty = Math.max(1, Math.min(merchant.buy_cap, buyQuantity + delta));
    setBuyQuantity(newQty);
  };

  const adjustSellQuantity = (delta: number) => {
    const newQty = Math.max(1, Math.min(merchant.sell_cap, sellQuantity + delta));
    setSellQuantity(newQty);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content merchant-detail-modal" onClick={(e) => e.stopPropagation()}>
        <h2>{merchant.item}</h2>
        
        <div className="merchant-detail-info">
          <div className="info-row">
            <span className="info-label">Buy Price:</span>
            <span className="info-value buy-price">${merchant.buy_price.toFixed(2)}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Sell Price:</span>
            <span className="info-value sell-price">${merchant.sell_price.toFixed(2)}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Algorithm:</span>
            <span className="info-value">{merchant.algorithm_name}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Stock:</span>
            <span className="info-value">
              {loadingStock ? 'Loading...' : stock === -1 ? 'Unknown' : stock}
            </span>
          </div>
          <div className="info-row">
            <span className="info-label">Buy Cap:</span>
            <span className="info-value">{merchant.buy_cap}</span>
          </div>
          <div className="info-row">
            <span className="info-label">Sell Cap:</span>
            <span className="info-value">{merchant.sell_cap}</span>
          </div>
        </div>

        {currentUser && (
          <div className="user-balance">
            Current Balance: ${currentUser.balance.toFixed(2)}
          </div>
        )}

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <div className="trading-section">
          <div className="trade-action">
            <h3>Buy</h3>
            <div className="quantity-control">
              <button onClick={() => adjustBuyQuantity(-1)} disabled={buyQuantity <= 1}>-</button>
              <input
                type="number"
                min="1"
                max={merchant.buy_cap}
                value={buyQuantity}
                onChange={(e) => {
                  const val = parseInt(e.target.value) || 1;
                  setBuyQuantity(Math.max(1, Math.min(merchant.buy_cap, val)));
                }}
              />
              <button onClick={() => adjustBuyQuantity(1)} disabled={buyQuantity >= merchant.buy_cap}>+</button>
            </div>
            <div className="trade-total">
              Total: ${(merchant.buy_price * buyQuantity).toFixed(2)}
            </div>
            <button
              onClick={handleBuy}
              disabled={loading || !currentUser}
              className="btn-buy"
            >
              {loading ? 'Processing...' : 'Buy'}
            </button>
          </div>

          <div className="trade-action">
            <h3>Sell</h3>
            <div className="quantity-control">
              <button onClick={() => adjustSellQuantity(-1)} disabled={sellQuantity <= 1}>-</button>
              <input
                type="number"
                min="1"
                max={merchant.sell_cap}
                value={sellQuantity}
                onChange={(e) => {
                  const val = parseInt(e.target.value) || 1;
                  setSellQuantity(Math.max(1, Math.min(merchant.sell_cap, val)));
                }}
              />
              <button onClick={() => adjustSellQuantity(1)} disabled={sellQuantity >= merchant.sell_cap}>+</button>
            </div>
            <div className="trade-total">
              Total: ${(merchant.sell_price * sellQuantity).toFixed(2)}
            </div>
            <button
              onClick={handleSell}
              disabled={loading || !currentUser}
              className="btn-sell"
            >
              {loading ? 'Processing...' : 'Sell'}
            </button>
          </div>
        </div>

        <div className="modal-actions">
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

