import React from 'react';

const SentimentModuleAdminPage = () => {
  return (
    <div className="p-6 bg-gray-900 min-h-screen">
      <h1 className="text-2xl font-bold text-white mb-6">Sentiment Module Admin</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Reliability Score</h3>
          <p className="text-green-400 text-2xl font-bold">94.2%</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Active Sources</h3>
          <p className="text-white text-2xl font-bold">12</p>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-lg text-white">Last Update</h3>
          <p className="text-gray-400">2 min ago</p>
        </div>
      </div>
    </div>
  );
};

export default SentimentModuleAdminPage;
