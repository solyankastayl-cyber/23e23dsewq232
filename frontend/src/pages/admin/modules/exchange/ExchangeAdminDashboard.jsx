import React from 'react';

const ExchangeAdminDashboard = () => {
  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <h1 className="text-2xl font-bold text-white mb-6">Exchange Admin Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Providers</h3>
          <p className="text-gray-400">Active: 3</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Jobs</h3>
          <p className="text-gray-400">Running: 5</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Data Sync</h3>
          <p className="text-green-400">Healthy</p>
        </div>
      </div>
    </div>
  );
};

export default ExchangeAdminDashboard;
