import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { Settings } from '../api/client';
import { 
  Save, 
  Percent, 
  Info,
  CheckCircle2,
  Loader2
} from 'lucide-react';

const SettingsPage = () => {
  const [settings, setSettings] = useState<Settings>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await api.getSettings();
        setSettings(data);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setMessage(null);
    try {
      await api.updateSettings(settings);
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to save settings' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (key: string, value: string) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  if (isLoading) {
    return (
      <div className="flex justify-center p-12">
        <Loader2 size={32} className="animate-spin text-gray-300" />
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-xl font-black text-gray-900 mb-6">Settings</h1>
      
      <form onSubmit={handleSave} className="space-y-6">
        <div className="p-6 bg-white border border-gray-100 rounded-3xl shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-xl">
              <Percent size={22} />
            </div>
            <div>
              <h2 className="font-black text-gray-900 leading-tight">Price Drops</h2>
              <p className="text-xs text-gray-400">Configure notification thresholds</p>
            </div>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                Minimum Savings Percentage
              </label>
              <div className="relative">
                <input 
                  type="number" 
                  step="0.01"
                  value={settings.min_savings_percentage || ''}
                  onChange={(e) => handleChange('min_savings_percentage', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all pr-12"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold">%</span>
              </div>
              <p className="mt-2 text-xs text-gray-400 flex items-start gap-1.5 px-1">
                <Info size={14} className="mt-0.5 flex-shrink-0" />
                Example: 0.10 will notify you when price drops by 10% or more.
              </p>
            </div>
          </div>
        </div>

        <button 
          type="submit"
          disabled={isSaving}
          className="w-full py-4 bg-gray-900 text-white rounded-2xl font-black text-lg shadow-lg active:scale-95 transition-all flex items-center justify-center gap-2"
        >
          {isSaving ? (
            <Loader2 size={24} className="animate-spin" />
          ) : (
            <>
              <Save size={24} />
              Save Settings
            </>
          )}
        </button>
        
        {message && (
          <div className={`p-4 rounded-xl flex items-center gap-3 font-bold animate-in fade-in slide-in-from-bottom-2 ${
            message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            <CheckCircle2 size={20} />
            {message.text}
          </div>
        )}
      </form>
    </div>
  );
};

export default SettingsPage;
