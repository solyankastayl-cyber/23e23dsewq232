/**
 * Ideas API - Idea Timeline System
 * =================================
 * 
 * Endpoints:
 *   POST /api/ideas - Create idea
 *   GET /api/ideas/:id - Get idea with history
 *   PUT /api/ideas/:id/update - Update idea (new version)
 *   GET /api/ideas/user/:user_id - Get user's ideas
 *   GET /api/ideas/asset/:asset - Get ideas for asset
 */

import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Create new idea from analysis
 */
export async function createIdea(data) {
  try {
    const response = await api.post('/ideas', data);
    return response.data;
  } catch (error) {
    console.error('Failed to create idea:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Get idea with version history
 */
export async function getIdea(ideaId) {
  try {
    const response = await api.get(`/ideas/${ideaId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get idea:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Update idea (creates new version)
 */
export async function updateIdea(ideaId, data) {
  try {
    const response = await api.put(`/ideas/${ideaId}/update`, data);
    return response.data;
  } catch (error) {
    console.error('Failed to update idea:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Get all ideas for a user
 */
export async function getUserIdeas(userId = 'anonymous') {
  try {
    const response = await api.get(`/ideas/user/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get user ideas:', error);
    return { success: false, ideas: [], error: error.message };
  }
}

/**
 * Get all ideas for an asset
 */
export async function getAssetIdeas(asset) {
  try {
    const response = await api.get(`/ideas/asset/${asset}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get asset ideas:', error);
    return { success: false, ideas: [], error: error.message };
  }
}

/**
 * Add idea to favorites
 */
export async function addFavorite(ideaId, userId = 'anonymous') {
  try {
    const response = await api.post(`/ideas/${ideaId}/favorite`, { user_id: userId });
    return response.data;
  } catch (error) {
    console.error('Failed to add favorite:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Remove idea from favorites
 */
export async function removeFavorite(ideaId, userId = 'anonymous') {
  try {
    const response = await api.delete(`/ideas/${ideaId}/favorite?user_id=${userId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to remove favorite:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Get user's favorites
 */
export async function getUserFavorites(userId = 'anonymous') {
  try {
    const response = await api.get(`/favorites/${userId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get favorites:', error);
    return { success: false, favorites: [], error: error.message };
  }
}

export default {
  createIdea,
  getIdea,
  updateIdea,
  getUserIdeas,
  getAssetIdeas,
  addFavorite,
  removeFavorite,
  getUserFavorites,
};
