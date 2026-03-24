import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '/api' : 'http://localhost:8010');

export interface Wishlist {
  id: number;
  name: string;
  url: string;
}

export interface WishlistItem {
  id: string;
  title: string;
  url: string;
  imageURL: string;
  price: number | null;
  priceUsed: number | null;
  savings: number;
  bestUsedPrice: number | null;
  wishlistName: string;
  wishlistUrl: string;
}

export interface PriceHistory {
  id: number;
  item_id: string;
  price: number | null;
  price_used: number | null;
  savings: number | null;
  timestamp: string;
}

export interface Notification {
  id: number;
  item_id: string;
  title: string;
  message: string;
  price: number;
  timestamp: string;
  is_read: number;
}

export interface Settings {
  [key: string]: string;
}

const client = axios.create({
  baseURL: API_BASE_URL,
});

export const api = {
  getSettings: () => client.get<Settings>('/settings').then(r => r.data),
  updateSettings: (settings: Settings) => client.post('/settings', settings).then(r => r.data),
  
  getWishlists: () => client.get<Wishlist[]>('/wishlists').then(r => r.data),
  addWishlist: (url: string) => client.post<Wishlist>('/wishlists', { url }).then(r => r.data),
  deleteWishlist: (id: number) => client.delete(`/wishlists/${id}`).then(r => r.data),
  
  getItems: () => client.get<WishlistItem[]>('/items').then(r => r.data),
  getItemHistory: (id: string) => client.get<PriceHistory[]>(`/items/${id}/history`).then(r => r.data),
  
  getNotifications: () => client.get<Notification[]>('/notifications').then(r => r.data),
  markNotificationRead: (id: number) => client.post(`/notifications/${id}/read`).then(r => r.data),
};
