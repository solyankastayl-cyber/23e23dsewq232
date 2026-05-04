import React from 'react';

const OnchainModuleAdminPage = () => {
  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <h1 className="text-2xl font-bold text-white mb-6">Onchain Module Admin</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Active Chains</h3>
          <p className="text-white text-2xl font-bold">5</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Indexed Wallets</h3>
          <p className="text-white text-2xl font-bold">1.2M</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Sync Status</h3>
          <p className="text-green-400">Healthy</p>
        </div>
      </div>
    </div>
  );
};

export default OnchainModuleAdminPage;
