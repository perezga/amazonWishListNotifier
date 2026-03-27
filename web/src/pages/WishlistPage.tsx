import { useState, useEffect, useMemo } from 'react';
import { api } from '../api/client';
import type { WishlistItem } from '../api/client';
import { 
  RefreshCw, 
  SortAsc, 
  Check, 
  ChevronRight, 
  ChevronDown, 
  ChevronUp, 
  ExternalLink,
  ShoppingBag,
  AlertCircle
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';

type SortOrder = 'ALPHABETICAL' | 'PRICE_LOW_HIGH' | 'SAVINGS_HIGH_LOW';

const WishlistPage = () => {
  const [items, setItems] = useState<WishlistItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>('ALPHABETICAL');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [expandedWishlists, setExpandedWishlists] = useState<Record<string, boolean>>({});

  const loadItems = async (refresh = false) => {
    if (refresh) setIsRefreshing(true);
    else setIsLoading(true);
    
    try {
      const data = await api.getItems();
      setItems(data);
      setError(null);
      
      // Expand all by default if not set
      const wishlists = Array.from(new Set(data.map(i => i.wishlistName || 'Default')));
      setExpandedWishlists(prev => {
        const next = { ...prev };
        wishlists.forEach(name => {
          if (next[name] === undefined) next[name] = true;
        });
        return next;
      });
    } catch (err) {
      setError('Failed to load items. Please try again.');
      console.error(err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const sortedItems = useMemo(() => {
    const sorted = [...items];
    switch (sortOrder) {
      case 'ALPHABETICAL':
        return sorted.sort((a, b) => a.title.localeCompare(b.title));
      case 'PRICE_LOW_HIGH':
        return sorted.sort((a, b) => (a.priceUsed ?? Infinity) - (b.priceUsed ?? Infinity));
      case 'SAVINGS_HIGH_LOW':
        return sorted.sort((a, b) => b.savings - a.savings);
      default:
        return sorted;
    }
  }, [items, sortOrder]);

  const groupedItems = useMemo(() => {
    const groups: Record<string, WishlistItem[]> = {};
    sortedItems.forEach(item => {
      const name = item.wishlistName || 'Default';
      if (!groups[name]) groups[name] = [];
      groups[name].push(item);
    });
    return groups;
  }, [sortedItems]);

  const toggleWishlist = (name: string) => {
    setExpandedWishlists(prev => ({ ...prev, [name]: !prev[name] }));
  };

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-100 animate-pulse rounded-lg"></div>
        ))}
      </div>
    );
  }

  if (error && items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <AlertCircle size={48} className="text-red-500 mb-4" />
        <p className="text-gray-600 mb-6">{error}</p>
        <button 
          onClick={() => loadItems()}
          className="px-6 py-2 bg-blue-600 text-white rounded-full font-bold"
        >
          Retry
        </button>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center">
        <ShoppingBag size={48} className="text-gray-300 mb-4" />
        <p className="text-gray-600 mb-6">No items in your wishlist yet.</p>
        <button 
          onClick={() => loadItems()}
          className="px-6 py-2 bg-blue-600 text-white rounded-full font-bold"
        >
          Refresh
        </button>
      </div>
    );
  }

  return (
    <div className="pb-8">
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 sticky top-14 z-40">
        <span className="text-sm font-medium text-gray-500">{items.length} items tracked</span>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => loadItems(true)}
            className="p-2 hover:bg-gray-100 rounded-full text-gray-600"
            disabled={isRefreshing}
          >
            <RefreshCw size={20} className={clsx(isRefreshing && "animate-spin")} />
          </button>
          
          <div className="relative">
            <button 
              onClick={() => setShowSortMenu(!showSortMenu)}
              className="p-2 hover:bg-gray-100 rounded-full text-gray-600"
            >
              <SortAsc size={20} />
            </button>
            
            {showSortMenu && (
              <>
                <div className="fixed inset-0 z-50" onClick={() => setShowSortMenu(false)}></div>
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-[60]">
                  {(['ALPHABETICAL', 'PRICE_LOW_HIGH', 'SAVINGS_HIGH_LOW'] as SortOrder[]).map(order => (
                    <button
                      key={order}
                      className="w-full flex items-center justify-between px-4 py-2 text-sm hover:bg-gray-50 text-gray-700"
                      onClick={() => {
                        setSortOrder(order);
                        setShowSortMenu(false);
                      }}
                    >
                      <span>{order.replace(/_/g, ' ')}</span>
                      {sortOrder === order && <Check size={16} className="text-blue-600" />}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {Object.entries(groupedItems).map(([name, wishlistItems]) => (
          <div key={name}>
            <div 
              className="flex items-center justify-between px-4 py-3 bg-gray-50 cursor-pointer"
              onClick={() => toggleWishlist(name)}
            >
              <div className="flex items-center gap-3">
                {expandedWishlists[name] ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                <div>
                  <h3 className="text-sm font-bold text-gray-900">{name}</h3>
                  <p className="text-xs text-gray-500">{wishlistItems.length} items</p>
                </div>
              </div>
              <a 
                href={wishlistItems[0].wishlistUrl} 
                target="_blank" 
                rel="noreferrer"
                className="p-2 text-blue-600 hover:bg-blue-50 rounded-full"
                onClick={e => e.stopPropagation()}
              >
                <ExternalLink size={18} />
              </a>
            </div>
            
            {expandedWishlists[name] && (
              <div className="divide-y divide-gray-50 px-2">
                {wishlistItems.map(item => (
                  <ItemCard key={item.id} item={item} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const ItemCard = ({ item }: { item: WishlistItem }) => {
  const currencyFormatter = new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  });

  return (
    <Link to={`/item/${item.id}`} className="flex items-center p-3 gap-4 hover:bg-gray-50 active:bg-gray-100 transition-colors">
      <div className="w-16 h-16 flex-shrink-0 bg-white border border-gray-100 rounded p-1">
        <img src={item.imageURL} alt="" className="w-full h-full object-contain" />
      </div>
      
      <div className="flex-grow min-w-0">
        <h4 className="text-sm font-bold text-gray-900 truncate">{item.title}</h4>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-xs text-gray-500">
            New: {item.price ? currencyFormatter.format(item.price) : 'N/A'}
          </span>
          <span className="text-sm font-black text-blue-600">
            Used: {item.priceUsed ? currencyFormatter.format(item.priceUsed) : 'N/A'}
          </span>
          {item.savings > 0 && (
            <span className="text-xs font-bold text-green-600 bg-green-50 px-1.5 py-0.5 rounded">
              -{Math.round(item.savings)}%
            </span>
          )}
        </div>
      </div>
      
      <ChevronRight size={20} className="text-gray-300" />
    </Link>
  );
};

export default WishlistPage;
