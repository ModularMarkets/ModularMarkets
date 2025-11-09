import React from 'react';
import { ShopSelector } from './ShopSelector';
import { UserSelector } from './UserSelector';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="layout">
      <header className="header">
        <div className="header-left">
          <ShopSelector />
        </div>
        <div className="header-right">
          <UserSelector />
        </div>
      </header>
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

