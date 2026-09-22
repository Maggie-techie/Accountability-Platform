// src/services/api.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

class APIService {
  // Authentication
  static async login(adminName, password) {
    const response = await fetch(`${API_BASE_URL}/auth/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_name: adminName, password })
    });
    return response.json();
  }

  // Constituency endpoints
  static async getAllConstituencies(filters = {}) {
    const queryParams = new URLSearchParams(filters).toString();
    const response = await fetch(`${API_BASE_URL}/constituency/?${queryParams}`);
    return response.json();
  }

  static async getConstituencyBySlug(slug) {
    const response = await fetch(`${API_BASE_URL}/constituency/${slug}`);
    return response.json();
  }

  static async getConstituencyAllocations(slug) {
    const response = await fetch(`${API_BASE_URL}/constituency/allocations/${slug}`);
    return response.json();
  }

  static async getConstituencyAuditFindings(slug) {
    const response = await fetch(`${API_BASE_URL}/constituency/audit/${slug}`);
    return response.json();
  }

  // Governor endpoints
  static async getGovernorProfile() {
    const response = await fetch(`${API_BASE_URL}/governor`);
    return response.json();
  }

  static async getCountyFinances(year = null) {
    const queryParams = year ? new URLSearchParams({ year }).toString() : '';
    const response = await fetch(`${API_BASE_URL}/governor/finances${queryParams ? '?' + queryParams : ''}`);
    return response.json();
  }

  static async getDepartmentData() {
    const response = await fetch(`${API_BASE_URL}/governor/departments`);
    return response.json();
  }

  static async getCountyAuditFindings() {
    const response = await fetch(`${API_BASE_URL}/governor/audit`);
    return response.json();
  }

  static async getGovernorScore() {
    const response = await fetch(`${API_BASE_URL}/governor/score`);
    return response.json();
  }

  // AI endpoints (examples)
  static async getMPRiskScore(constituencySlug) {
    const response = await fetch(`${API_BASE_URL}/ai/mp/${constituencySlug}/risk_score`);
    return response.json();
  }

  static async compareLeaders(leader1Type, leader1Id, leader2Type, leader2Id) {
    const response = await fetch(`${API_BASE_URL}/ai/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        leader1_type: leader1Type,
        leader1_id: leader1Id,
        leader2_type: leader2Type,
        leader2_id: leader2Id
      })
    });
    return response.json();
  }
}

export default APIService;