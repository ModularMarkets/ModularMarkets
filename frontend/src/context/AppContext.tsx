import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient, User, Shop } from '../api/client';

interface AppContextType {
  currentUser: User | null;
  currentShop: Shop | null;
  users: User[];
  shops: Shop[];
  setCurrentUser: (user: User | null) => void;
  setCurrentShop: (shop: Shop | null) => void;
  refreshUsers: () => Promise<void>;
  refreshShops: () => Promise<void>;
  loading: boolean;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
};

interface AppProviderProps {
  children: ReactNode;
}

export const AppProvider: React.FC<AppProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentShop, setCurrentShop] = useState<Shop | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState(true);

  const refreshUsers = async () => {
    try {
      const data = await apiClient.getUsers();
      setUsers(data);
      // If current user exists, update it
      if (currentUser) {
        const updated = data.find(u => u.username === currentUser.username);
        if (updated) {
          setCurrentUser(updated);
        }
      }
    } catch (error) {
      console.error('Failed to refresh users:', error);
    }
  };

  const refreshShops = async () => {
    try {
      const data = await apiClient.getShops();
      setShops(data);
      // If current shop exists, update it
      if (currentShop) {
        const updated = data.find(s => s.shop_id === currentShop.shop_id);
        if (updated) {
          setCurrentShop(updated);
        }
      }
    } catch (error) {
      console.error('Failed to refresh shops:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        await Promise.all([refreshUsers(), refreshShops()]);
      } catch (error) {
        console.error('Failed to load initial data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  return (
    <AppContext.Provider
      value={{
        currentUser,
        currentShop,
        users,
        shops,
        setCurrentUser,
        setCurrentShop,
        refreshUsers,
        refreshShops,
        loading,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

