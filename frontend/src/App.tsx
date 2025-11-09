import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Layout } from './components/Layout';
import { MerchantList } from './components/MerchantList';
import './App.css';

const AppContent: React.FC = () => {
  const { loading } = useApp();

  if (loading) {
    return (
      <Layout>
        <div className="loading-container">
          <div className="loading-spinner">Loading...</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <MerchantList />
    </Layout>
  );
};

export const App: React.FC = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

