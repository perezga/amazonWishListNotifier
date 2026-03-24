import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  ShoppingBag, 
  Settings, 
  Bell, 
  List, 
  ChevronLeft,
  Search,
  RefreshCw
} from 'lucide-react';

// Pages (to be created)
import WishlistPage from './pages/WishlistPage';
import ItemDetailPage from './pages/ItemDetailPage';
import WishlistManagementPage from './pages/WishlistManagementPage';
import SettingsPage from './pages/SettingsPage';
import NotificationsPage from './pages/NotificationsPage';

const Navbar = () => {
  const location = useLocation();
  const isHome = location.pathname === '/';
  
  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        {!isHome && (
          <Link to="/" className="p-1 hover:bg-gray-100 rounded-full">
            <ChevronLeft size={24} />
          </Link>
        )}
        <Link to="/" className="text-xl font-black text-gray-900">PricePulse</Link>
      </div>
      
      <div className="flex items-center gap-2">
        <Link to="/notifications" className="p-2 hover:bg-gray-100 rounded-full relative">
          <Bell size={22} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        </Link>
        <Link to="/wishlists" className="p-2 hover:bg-gray-100 rounded-full">
          <List size={22} />
        </Link>
        <Link to="/settings" className="p-2 hover:bg-gray-100 rounded-full">
          <Settings size={22} />
        </Link>
      </div>
    </nav>
  );
};

const App = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
        <Navbar />
        <main className="max-w-md mx-auto min-h-[calc(100vh-64px)] bg-white shadow-sm border-x border-gray-100">
          <Routes>
            <Route path="/" element={<WishlistPage />} />
            <Route path="/item/:id" element={<ItemDetailPage />} />
            <Route path="/wishlists" element={<WishlistManagementPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
