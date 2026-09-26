// src/services/api.js

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

class APIService {
  static get baseURL() {
    return API_BASE_URL;
  }

  // Authentication
  static async login(adminName, password) {
    const response = await fetch(`${this.baseURL}/auth/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_name: adminName, password })
    });
    return response.json();
  }

  // Constituency endpoints
  static async getAllConstituencies(filters = {}) {
    const queryParams = new URLSearchParams(filters).toString();
    const response = await fetch(`${this.baseURL}/constituency/?${queryParams}`);
    return response.json();
  }

  static async getConstituencyBySlug(slug) {
    const response = await fetch(`${this.baseURL}/constituency/${slug}`);
    return response.json();
  }

  static async getConstituencyAllocations(slug) {
    const response = await fetch(`${this.baseURL}/constituency/allocations/${slug}`);
    return response.json();
  }

  static async getConstituencyAuditFindings(slug) {
    const response = await fetch(`${this.baseURL}/constituency/audit/${slug}`);
    return response.json();
  }

  // Governor endpoints
  static async getGovernorProfile() {
    const response = await fetch(`${this.baseURL}/governor`);
    return response.json();
  }

  static async getCountyFinances(year = null) {
    const queryParams = year ? new URLSearchParams({ year }).toString() : '';
    const response = await fetch(`${this.baseURL}/governor/finances${queryParams ? '?' + queryParams : ''}`);
    return response.json();
  }

  static async getDepartmentData() {
    const response = await fetch(`${this.baseURL}/governor/departments`);
    return response.json();
  }

  static async getCountyAuditFindings() {
    const response = await fetch(`${this.baseURL}/governor/audit`);
    return response.json();
  }

  static async getGovernorScore() {
    const response = await fetch(`${this.baseURL}/governor/score`);
    return response.json();
  }

  // AI endpoints (examples)
  static async getMPRiskScore(constituencySlug) {
    const response = await fetch(`${this.baseURL}/ai/mp/${constituencySlug}/risk_score`);
    return response.json();
  }

  static async compareLeaders(leader1Type, leader1Id, leader2Type, leader2Id) {
    const response = await fetch(`${this.baseURL}/ai/compare`, {
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