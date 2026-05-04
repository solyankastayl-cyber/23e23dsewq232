import React from 'react';
import { useParams } from 'react-router-dom';

const WalletPage = () => {
  const { address } = useParams();
  
  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-2xl font-bold mb-6">Wallet Intelligence</h1>
      {address && (
        <div className="bg-gray-800 p-4 rounded-lg mb-4">
          <p className="text-gray-400 text-sm">Address</p>
          <p className="text-lg font-mono">{address}</p>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg font-semibold">Balance</h3>
          <p className="text-2xl font-bold">$245,000</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg font-semibold">Transactions</h3>
          <p className="text-2xl font-bold">1,234</p>
        </div>
      </div>
    </div>
  );
};

export default WalletPage;
