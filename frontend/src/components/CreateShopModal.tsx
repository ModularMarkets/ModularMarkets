import React, { useState, useEffect } from 'react';
import { apiClient, CreateShopRequest } from '../api/client';
import './Modal.css';

interface CreateShopModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

export const CreateShopModal: React.FC<CreateShopModalProps> = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState<CreateShopRequest>({
    shop_id: '',
    platform_type: '',
  });
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingPlatforms, setLoadingPlatforms] = useState(true);

  useEffect(() => {
    const loadPlatforms = async () => {
      try {
        const data = await apiClient.getPlatforms();
        setPlatforms(data.platforms);
      } catch (err) {
        console.error('Failed to load platforms:', err);
      } finally {
        setLoadingPlatforms(false);
      }
    };
    loadPlatforms();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await apiClient.createShop(formData);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create shop');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Create New Shop</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Shop ID:</label>
            <input
              type="text"
              value={formData.shop_id}
              onChange={(e) => setFormData({ ...formData, shop_id: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label>Platform Type:</label>
            {loadingPlatforms ? (
              <div>Loading platforms...</div>
            ) : (
              <select
                value={formData.platform_type}
                onChange={(e) => setFormData({ ...formData, platform_type: e.target.value })}
                required
              >
                <option value="">Select Platform</option>
                {platforms.map(platform => (
                  <option key={platform} value={platform}>
                    {platform}
                  </option>
                ))}
              </select>
            )}
          </div>
          {error && <div className="error-message">{error}</div>}
          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" disabled={loading || !formData.platform_type}>
              {loading ? 'Creating...' : 'Create Shop'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

