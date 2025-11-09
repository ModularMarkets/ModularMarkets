import React, { useState, useEffect } from 'react';
import { apiClient, User } from '../api/client';
import './Modal.css';

interface LinkAccountModalProps {
  user: User;
  onClose: () => void;
  onSuccess: () => void;
}

export const LinkAccountModal: React.FC<LinkAccountModalProps> = ({ user, onClose, onSuccess }) => {
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [linkedAccounts, setLinkedAccounts] = useState<Record<string, string>>({ ...user.linked_accounts });
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
        setError('Failed to load platforms');
      } finally {
        setLoadingPlatforms(false);
      }
    };
    loadPlatforms();
  }, []);

  const handleUuidChange = (platform: string, uuid: string) => {
    setLinkedAccounts(prev => ({
      ...prev,
      [platform]: uuid
    }));
  };

  const handleRemove = (platform: string) => {
    setLinkedAccounts(prev => {
      const newAccounts = { ...prev };
      delete newAccounts[platform];
      return newAccounts;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await apiClient.updateLinkedAccounts(user.username, linkedAccounts);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update linked accounts');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Link Accounts for {user.display_name}</h2>
        <form onSubmit={handleSubmit}>
          {loadingPlatforms ? (
            <div>Loading platforms...</div>
          ) : (
            <>
              <div className="form-group">
                <label>Linked Accounts:</label>
                <div className="linked-accounts-list">
                  {platforms.map(platform => {
                    const currentUuid = linkedAccounts[platform] || '';
                    return (
                      <div key={platform} className="linked-account-item">
                        <label className="platform-label">{platform}:</label>
                        <input
                          type="text"
                          value={currentUuid}
                          onChange={(e) => handleUuidChange(platform, e.target.value)}
                          placeholder={`Enter ${platform} UUID`}
                          className="uuid-input"
                        />
                        {currentUuid && (
                          <button
                            type="button"
                            onClick={() => handleRemove(platform)}
                            className="btn-remove"
                            title="Remove"
                          >
                            ×
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
              {Object.keys(linkedAccounts).length === 0 && (
                <div className="info-message">
                  No accounts linked. Enter a UUID for any platform above.
                </div>
              )}
            </>
          )}
          {error && <div className="error-message">{error}</div>}
          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" disabled={loading || loadingPlatforms}>
              {loading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

