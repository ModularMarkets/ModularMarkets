import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { CreateShopModal } from './CreateShopModal';
import './ShopSelector.css';

export const ShopSelector: React.FC = () => {
  const { currentShop, shops, setCurrentShop, refreshShops, currentUser } = useApp();
  const [showCreateModal, setShowCreateModal] = useState(false);

  const handleShopChange = (shopId: string) => {
    const shop = shops.find(s => s.shop_id === shopId);
    setCurrentShop(shop || null);
  };

  const handleShopCreated = async () => {
    await refreshShops();
    setShowCreateModal(false);
  };

  return (
    <div className="shop-selector">
      <select
        value={currentShop?.shop_id || ''}
        onChange={(e) => handleShopChange(e.target.value)}
        className="shop-select"
      >
        <option value="">Select Shop</option>
        {shops.map(shop => (
          <option key={shop.shop_id} value={shop.shop_id}>
            {shop.platform_type}
          </option>
        ))}
      </select>
      {currentUser && currentUser.role === 100 && (
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-create-shop"
          title="Create New Shop"
        >
          + Create Shop
        </button>
      )}
      {showCreateModal && (
        <CreateShopModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleShopCreated}
        />
      )}
    </div>
  );
};

