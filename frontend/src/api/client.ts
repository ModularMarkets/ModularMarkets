import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface User {
  username: string;
  display_name: string;
  balance: number;
  role: number;
  linked_accounts: Record<string, string>;
}

export interface MerchantInfo {
  item: string;
  buy_price: number;
  sell_price: number;
  buy_cap: number;
  sell_cap: number;
  algorithm_name: string;
}

export interface Shop {
  shop_id: string;
  platform_type: string;
  merchants: MerchantInfo[];
}

export interface CreateUserRequest {
  username: string;
  display_name: string;
  balance: number;
  password: string;
  role?: number;
  linked_accounts?: Record<string, string>;
}

export interface CreateShopRequest {
  shop_id: string;
  platform_type: string;
}

export interface CreateMerchantRequest {
  item: string;
  starting_price: number;
  algorithm_name: string;
  algorithm_config?: Record<string, any>;
  buy_cap: number;
  sell_cap: number;
}

// API Functions
export const apiClient = {
  // Users
  getUsers: async (): Promise<User[]> => {
    const response = await api.get<User[]>('/users');
    return response.data;
  },

  getUser: async (username: string): Promise<User> => {
    const response = await api.get<User>(`/users/${username}`);
    return response.data;
  },

  createUser: async (data: CreateUserRequest): Promise<User> => {
    const response = await api.post<User>('/users', data);
    return response.data;
  },

  updateLinkedAccounts: async (username: string, linkedAccounts: Record<string, string>): Promise<User> => {
    const response = await api.put<User>(`/users/${username}/linked-accounts`, { linked_accounts: linkedAccounts });
    return response.data;
  },

  // Shops
  getShops: async (): Promise<Shop[]> => {
    const response = await api.get<Shop[]>('/shops');
    return response.data;
  },

  getShop: async (shopId: string): Promise<Shop> => {
    const response = await api.get<Shop>(`/shops/${shopId}`);
    return response.data;
  },

  createShop: async (data: CreateShopRequest): Promise<Shop> => {
    const response = await api.post<Shop>('/shops', data);
    return response.data;
  },

  // Merchants
  getMerchant: async (shopId: string, item: string): Promise<MerchantInfo> => {
    const response = await api.get<MerchantInfo>(`/shops/${shopId}/merchants/${item}`);
    return response.data;
  },

  createMerchant: async (shopId: string, data: CreateMerchantRequest): Promise<MerchantInfo> => {
    const response = await api.post<MerchantInfo>(`/shops/${shopId}/merchants`, data);
    return response.data;
  },

  getStock: async (shopId: string, item: string): Promise<{ item: string; stock: number }> => {
    const response = await api.get<{ item: string; stock: number }>(`/shops/${shopId}/merchants/${item}/stock`);
    return response.data;
  },

  buyItem: async (shopId: string, item: string, quantity: number, username: string): Promise<{ success: boolean; message: string; new_balance: number; merchant: MerchantInfo }> => {
    const response = await api.post(`/shops/${shopId}/merchants/${item}/buy`, { quantity, username });
    return response.data;
  },

  sellItem: async (shopId: string, item: string, quantity: number, username: string): Promise<{ success: boolean; message: string; new_balance: number; merchant: MerchantInfo }> => {
    const response = await api.post(`/shops/${shopId}/merchants/${item}/sell`, { quantity, username });
    return response.data;
  },

  // Platforms & Algorithms
  getPlatforms: async (): Promise<{ platforms: string[] }> => {
    const response = await api.get<{ platforms: string[] }>('/platforms');
    return response.data;
  },

  getAlgorithms: async (): Promise<{ algorithms: string[] }> => {
    const response = await api.get<{ algorithms: string[] }>('/algorithms');
    return response.data;
  },

  getPlatformItems: async (platformType: string): Promise<{ platform_type: string; items: string[] }> => {
    const response = await api.get<{ platform_type: string; items: string[] }>(`/platforms/${platformType}/items`);
    return response.data;
  },
};

