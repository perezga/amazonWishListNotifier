import React, { useState, useEffect } from 'react';
import { api, Wishlist } from '../api/client';
import { 
  Plus, 
  Trash2, 
  ExternalLink, 
  Link as LinkIcon,
  AlertCircle,
  Loader2
} from 'lucide-react';

const WishlistManagementPage = () => {
  const [wishlists, setWishlists] = useState<Wishlist[]>([]);
  const [newUrl, setNewUrl] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isAdding, setIsAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadWishlists = async () => {
    setIsLoading(true);
    try {
      const data = await api.getWishlists();
      setWishlists(data);
    } catch (err) {
      setError('Failed to load wishlists');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWishlists();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl) return;
    
    setIsAdding(true);
    setError(null);
    try {
      await api.addWishlist(newUrl);
      setNewUrl('');
      await loadWishlists();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add wishlist');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this wishlist and all its tracked items?')) return;
    
    try {
      await api.deleteWishlist(id);
      await loadWishlists();
    } catch (err) {
      setError('Failed to delete wishlist');
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-xl font-black text-gray-900 mb-6">Manage Wishlists</h1>
      
      <form onSubmit={handleAdd} className="mb-8">
        <label className="block text-sm font-bold text-gray-700 mb-2">Add Amazon Wishlist URL</label>
        <div className="flex gap-2">
          <div className="relative flex-grow">
            <LinkIcon size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input 
              type="url" 
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://www.amazon.es/hz/wishlist/ls/..."
              className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition-all"
              required
            />
          </div>
          <button 
            type="submit"
            disabled={isAdding}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-bold active:scale-95 transition-all flex items-center justify-center min-w-[100px]"
          >
            {isAdding ? <Loader2 size={20} className="animate-spin" /> : 'Add'}
          </button>
        </div>
        {error && (
          <div className="mt-3 flex items-center gap-2 text-sm text-red-600 font-medium">
            <AlertCircle size={16} />
            {error}
          </div>
        )}
      </form>

      <div className="space-y-4">
        <h2 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Active Wishlists</h2>
        
        {isLoading ? (
          <div className="flex justify-center p-8">
            <Loader2 size={32} className="animate-spin text-gray-300" />
          </div>
        ) : wishlists.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200">
            <p className="text-gray-500">No wishlists added yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {wishlists.map(w => (
              <div key={w.id} className="p-4 bg-white border border-gray-100 rounded-2xl shadow-sm flex items-center justify-between">
                <div className="min-w-0 flex-grow">
                  <h3 className="font-bold text-gray-900 truncate">{w.name}</h3>
                  <p className="text-xs text-gray-400 truncate mt-0.5">{w.url}</p>
                </div>
                <div className="flex items-center gap-1 ml-4">
                  <a 
                    href={w.url} 
                    target="_blank" 
                    rel="noreferrer"
                    className="p-2 text-gray-400 hover:bg-gray-50 hover:text-blue-600 rounded-full transition-colors"
                  >
                    <ExternalLink size={18} />
                  </a>
                  <button 
                    onClick={() => handleDelete(w.id)}
                    className="p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 rounded-full transition-colors"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default WishlistManagementPage;
