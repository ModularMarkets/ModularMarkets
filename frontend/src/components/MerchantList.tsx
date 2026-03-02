import React, { useState, useMemo } from 'react';
import { useApp } from '../context/AppContext';
import { MerchantCard } from './MerchantCard';
import { CreateMerchantModal } from './CreateMerchantModal';
import { MerchantDetail } from './MerchantDetail';
import { PriceHistoryGraph } from './PriceHistoryGraph';
import { MerchantInfo } from '../api/client';
import './MerchantList.css';

export const MerchantList: React.FC = () => {
  const { currentShop, refreshShops, currentUser } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedMerchant, setSelectedMerchant] = useState<MerchantInfo | null>(null);

  const filteredMerchants = useMemo(() => {
    if (!currentShop) return [];
    if (!searchQuery) return currentShop.merchants;
    return currentShop.merchants.filter(merchant =>
      merchant.item.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [currentShop, searchQuery]);

  if (!currentShop) {
    return (
      <div className="merchant-list-empty">
        <p>Please select a shop to view merchants</p>
      </div>
    );
  }

  return (
    <div className="merchant-list">
      {currentShop && currentShop.merchants.length > 0 && (
        <PriceHistoryGraph 
          shopId={currentShop.shop_id} 
          item={currentShop.merchants[0].item} 
        />
      )}
      <div className="merchant-list-header">
        <div className="search-bar">
          <input
            type="text"
            placeholder="Search merchants..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>
        {currentUser && currentUser.role === 100 && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-create-merchant"
          >
            + Create Merchant
          </button>
        )}
      </div>
      <div className="merchants-grid">
        {filteredMerchants.length === 0 ? (
          <div className="no-merchants">
            {searchQuery ? 'No merchants found matching your search' : 'No merchants yet. Create one to get started!'}
          </div>
        ) : (
          filteredMerchants.map(merchant => (
            <MerchantCard
              key={merchant.item}
              merchant={merchant}
              shopId={currentShop.shop_id}
              onClick={() => setSelectedMerchant(merchant)}
            />
          ))
        )}
      </div>
      {showCreateModal && (
        <CreateMerchantModal
          shopId={currentShop.shop_id}
          platformType={currentShop.platform_type}
          onClose={() => setShowCreateModal(false)}
          onSuccess={async () => {
            setShowCreateModal(false);
            await refreshShops();
          }}
        />
      )}
      {selectedMerchant && (
        <MerchantDetail
          merchant={selectedMerchant}
          shopId={currentShop.shop_id}
          onClose={() => setSelectedMerchant(null)}
        />
      )}
    </div>
  );
};

