import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const OnchainV3Page = () => {
  const [searchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'overview';
  
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'signals', label: 'Signals' },
    { id: 'engine', label: 'Engine' },
    { id: 'wallet', label: 'Wallet' },
    { id: 'assets', label: 'Assets' },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="border-b border-gray-700 px-6 py-4">
        <h1 className="text-2xl font-bold">On-Chain Intelligence V3</h1>
        <div className="flex gap-4 mt-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-gray-800 p-4 rounded-lg">
            <h3 className="text-lg font-semibold">Total Flow</h3>
            <p className="text-2xl font-bold text-green-400">$1.2B</p>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <h3 className="text-lg font-semibold">Active Wallets</h3>
            <p className="text-2xl font-bold">12,450</p>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <h3 className="text-lg font-semibold">Signals</h3>
            <p className="text-2xl font-bold text-yellow-400">28</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnchainV3Page;
