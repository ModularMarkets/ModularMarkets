import React, { useState, useEffect } from 'react';
import { apiClient, CreateMerchantRequest } from '../api/client';
import './Modal.css';

interface CreateMerchantModalProps {
  shopId: string;
  platformType: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateMerchantModal: React.FC<CreateMerchantModalProps> = ({ shopId, platformType, onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateMerchantRequest>({
    item: '',
    starting_price: 100,
    algorithm_name: '',
    algorithm_config: {},
    buy_cap: 100,
    sell_cap: 100,
  });
  const [items, setItems] = useState<string[]>([]);
  const [algorithms, setAlgorithms] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [itemsData, algorithmsData] = await Promise.all([
          apiClient.getPlatformItems(platformType),
          apiClient.getAlgorithms(),
        ]);
        setItems(itemsData.items);
        setAlgorithms(algorithmsData.algorithms);
      } catch (err) {
        console.error('Failed to load data:', err);
        setError('Failed to load platform items or algorithms');
      } finally {
        setLoadingData(false);
      }
    };
    loadData();
  }, [platformType]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await apiClient.createMerchant(shopId, formData);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create merchant');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Create New Merchant</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Item:</label>
            {loadingData ? (
              <div>Loading items...</div>
            ) : (
              <select
                value={formData.item}
                onChange={(e) => setFormData({ ...formData, item: e.target.value })}
                required
              >
                <option value="">Select Item</option>
                {items.map(item => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="form-group">
            <label>Starting Price:</label>
            <input
              type="number"
              min="1"
              value={formData.starting_price}
              onChange={(e) => setFormData({ ...formData, starting_price: parseInt(e.target.value) || 100 })}
              required
            />
          </div>
          <div className="form-group">
            <label>Algorithm:</label>
            {loadingData ? (
              <div>Loading algorithms...</div>
            ) : (
              <select
                value={formData.algorithm_name}
                onChange={(e) => setFormData({ ...formData, algorithm_name: e.target.value })}
                required
              >
                <option value="">Select Algorithm</option>
                {algorithms.map(algo => (
                  <option key={algo} value={algo}>
                    {algo}
                  </option>
                ))}
              </select>
            )}
          </div>
          <div className="form-group">
            <label>Buy Cap:</label>
            <input
              type="number"
              min="1"
              value={formData.buy_cap}
              onChange={(e) => setFormData({ ...formData, buy_cap: parseInt(e.target.value) || 100 })}
              required
            />
          </div>
          <div className="form-group">
            <label>Sell Cap:</label>
            <input
              type="number"
              min="1"
              value={formData.sell_cap}
              onChange={(e) => setFormData({ ...formData, sell_cap: parseInt(e.target.value) || 100 })}
              required
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" disabled={loading || !formData.item || !formData.algorithm_name}>
              {loading ? 'Creating...' : 'Create Merchant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

