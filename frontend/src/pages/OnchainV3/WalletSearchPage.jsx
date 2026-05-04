import React, { useState } from 'react';

const WalletSearchPage = () => {
  const [search, setSearch] = useState('');
  
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-6">Wallet Search</h1>
      <div className="max-w-2xl">
        <input
          type="text"
          placeholder="Search wallet address..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-4 py-3 bg-gray-800 rounded-lg border border-gray-700 focus:border-blue-500 focus:outline-none"
        />
        <div className="mt-4 text-gray-400">
          Enter a wallet address to view its activity and intelligence data.
        </div>
      </div>
    </div>
  );
};

export default WalletSearchPage;
