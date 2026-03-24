import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, WishlistItem, PriceHistory } from '../api/client';
import { 
  ShoppingCart, 
  Share2, 
  ChevronLeft, 
  TrendingDown, 
  TrendingUp,
  ExternalLink,
  Calendar
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend
} from 'recharts';
import { format, parseISO } from 'date-fns';

const ItemDetailPage = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [item, setItem] = useState<WishlistItem | null>(null);
  const [history, setHistory] = useState<PriceHistory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!id) return;
      try {
        const [items, historyData] = await Promise.all([
          api.getItems(),
          api.getItemHistory(id)
        ]);
        
        const foundItem = items.find(i => i.id === id);
        if (foundItem) {
          setItem(foundItem);
          setHistory(historyData);
        } else {
          setError('Item not found');
        }
      } catch (err) {
        setError('Failed to load item details');
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [id]);

  const chartData = history.map(h => ({
    date: format(parseISO(h.timestamp), 'dd/MM'),
    new: h.price,
    used: h.price_used,
  }));

  const currencyFormatter = new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="p-8 text-center text-red-500 font-medium">
        {error || 'Item not found'}
      </div>
    );
  }

  return (
    <div className="pb-12">
      <div className="p-4 bg-white">
        <div className="flex gap-6 mb-8">
          <div className="w-32 h-32 flex-shrink-0 bg-white border border-gray-100 rounded-lg p-2">
            <img src={item.imageURL} alt="" className="w-full h-full object-contain" />
          </div>
          <div className="flex-grow pt-2">
            <h1 className="text-lg font-black text-gray-900 leading-tight mb-3">{item.title}</h1>
            <div className="space-y-1">
              <p className="text-sm text-gray-500 flex items-center justify-between">
                <span>New Price:</span>
                <span className="font-medium text-gray-700">{item.price ? currencyFormatter.format(item.price) : 'N/A'}</span>
              </p>
              <p className="text-base font-bold text-blue-600 flex items-center justify-between">
                <span>Used Price:</span>
                <span className="text-lg">{item.priceUsed ? currencyFormatter.format(item.priceUsed) : 'N/A'}</span>
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-8">
          <a 
            href={item.url} 
            target="_blank" 
            rel="noreferrer"
            className="flex items-center justify-center gap-2 py-3 bg-blue-600 text-white rounded-xl font-bold active:scale-95 transition-transform"
          >
            <ShoppingCart size={20} />
            Buy Now
          </a>
          <button 
            onClick={() => {
              if (navigator.share) {
                navigator.share({
                  title: item.title,
                  url: item.url
                });
              } else {
                navigator.clipboard.writeText(item.url);
                alert('URL copied to clipboard');
              }
            }}
            className="flex items-center justify-center gap-2 py-3 bg-gray-100 text-gray-700 rounded-xl font-bold active:scale-95 transition-transform"
          >
            <Share2 size={20} />
            Share
          </button>
        </div>

        <div className="mb-4">
          <h2 className="text-lg font-black text-gray-900 mb-4 flex items-center gap-2">
            <TrendingDown size={22} className="text-blue-600" />
            Price History
          </h2>
          
          {history.length > 0 ? (
            <div className="h-64 w-full -ml-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 12, fill: '#9ca3af' }}
                    dy={10}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fontSize: 12, fill: '#9ca3af' }}
                    tickFormatter={(val) => `€${val}`}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                  />
                  <Legend verticalAlign="top" height={36}/>
                  <Line 
                    type="monotone" 
                    dataKey="new" 
                    name="New"
                    stroke="#ef4444" 
                    strokeWidth={3} 
                    dot={{ r: 4, fill: '#ef4444' }}
                    activeDot={{ r: 6 }} 
                  />
                  <Line 
                    type="monotone" 
                    dataKey="used" 
                    name="Used"
                    stroke="#2563eb" 
                    strokeWidth={3} 
                    dot={{ r: 4, fill: '#2563eb' }}
                    activeDot={{ r: 6 }} 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
              <Calendar size={48} className="text-gray-300 mb-2" />
              <p className="text-gray-500">No price history available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ItemDetailPage;
