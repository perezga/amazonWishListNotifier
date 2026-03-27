import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { Notification } from '../api/client';
import { 
  Bell, 
  Clock, 
  Tag,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { Link } from 'react-router-dom';

const NotificationsPage = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadNotifications = async () => {
    try {
      const data = await api.getNotifications();
      setNotifications(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadNotifications();
  }, []);

  const handleMarkRead = async (id: number) => {
    try {
      await api.markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: 1 } : n));
    } catch (err) {
      console.error(err);
    }
  };

  const currencyFormatter = new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'EUR',
  });

  if (isLoading) {
    return (
      <div className="flex justify-center p-12">
        <Loader2 size={32} className="animate-spin text-gray-300" />
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-black text-gray-900 mb-6 flex items-center justify-between">
        Notifications
        <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-full uppercase tracking-tighter">
          Recent Alerts
        </span>
      </h1>
      
      {notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 text-center bg-gray-50 rounded-3xl border-2 border-dashed border-gray-100">
          <Bell size={48} className="text-gray-200 mb-4" />
          <p className="text-gray-500 font-medium">No alerts yet. We'll notify you when prices drop!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notifications.map(n => (
            <div 
              key={n.id} 
              className={`group p-4 rounded-3xl border transition-all relative overflow-hidden ${
                n.is_read ? 'bg-white border-gray-100' : 'bg-blue-50 border-blue-100 shadow-sm ring-1 ring-blue-200'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-2xl ${n.is_read ? 'bg-gray-50 text-gray-400' : 'bg-white text-blue-600 shadow-sm'}`}>
                  <Tag size={20} />
                </div>
                
                <div className="flex-grow min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <h3 className={`font-black text-sm truncate leading-tight ${n.is_read ? 'text-gray-500' : 'text-gray-900'}`}>
                      {n.title}
                    </h3>
                    <span className="text-[10px] font-bold text-gray-400 flex items-center gap-1 whitespace-nowrap pt-0.5">
                      <Clock size={10} />
                      {format(parseISO(n.timestamp), 'dd MMM, HH:mm')}
                    </span>
                  </div>
                  
                  <p className={`text-xs mb-3 leading-relaxed ${n.is_read ? 'text-gray-400' : 'text-gray-600'}`}>
                    {n.message}
                  </p>
                  
                  <div className="flex items-center justify-between">
                    <span className={`text-sm font-black ${n.is_read ? 'text-gray-400' : 'text-blue-600'}`}>
                      {currencyFormatter.format(n.price)}
                    </span>
                    
                    <div className="flex items-center gap-2">
                      {!n.is_read && (
                        <button 
                          onClick={() => handleMarkRead(n.id)}
                          className="text-[10px] font-black uppercase text-blue-600 px-3 py-1.5 bg-white border border-blue-100 rounded-full hover:bg-blue-50 transition-colors shadow-sm"
                        >
                          Mark as Read
                        </button>
                      )}
                      <Link 
                        to={`/item/${n.item_id}`}
                        className={`p-1.5 rounded-full transition-colors ${
                          n.is_read ? 'text-gray-300 hover:bg-gray-100' : 'text-blue-600 hover:bg-white shadow-sm'
                        }`}
                      >
                        <ChevronRight size={18} />
                      </Link>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default NotificationsPage;
