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

  static async getConstituencyScore(slug) {
    const response = await fetch(`${this.baseURL}/constituency/${slug}/score`);
    return response.json();
  }

  static async getAllConstituencyScores() {
    // Fetch all constituencies and their scores in parallel
    const constituenciesResponse = await this.getAllConstituencies({ limit: 50 });
    const constituencies = constituenciesResponse.constituencies || constituenciesResponse;

    const scores = await Promise.all(
      constituencies.map(c =>
        this.getConstituencyScore(c.slug).catch(() => ({ score: null }))
      )
    );

    return constituencies.map((c, i) => ({
      ...c,
      accountabilityScore: scores[i]?.score ?? c.accountabilityScore ?? null
    }));
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

  // PDF Report endpoints
  static async downloadGovernorPDFReport(governorName) {
    const response = await fetch(`${this.baseURL}/reports/governor/${encodeURIComponent(governorName)}/pdf`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to generate report' }));
      throw new Error(error.error || error.details || 'Failed to generate governor report');
    }
    return response.blob();
  }

  static async downloadConstituencyPDFReport(constituencySlug) {
    const response = await fetch(`${this.baseURL}/reports/constituency/${constituencySlug}/pdf`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to generate report' }));
      throw new Error(error.error || error.details || 'Failed to generate constituency report');
    }
    return response.blob();
  }

  // Anomaly endpoints
  static async getGovernorTopRisks() {
    const response = await fetch(`${this.baseURL}/ai/governor/top_risks`);
    return response.json();
  }

  static async getGovernorDepartmentFlags() {
    const response = await fetch(`${this.baseURL}/ai/governor/department_flags`);
    return response.json();
  }

  static async getGNNAnomalies(constituencySlug) {
    const response = await fetch(`${this.baseURL}/ai/mp/${constituencySlug}/gnn_anomalies`);
    return response.json();
  }

  // MP AI Anomalies
  static async getMPAIAnomalies(constituencySlug) {
    const response = await fetch(`${this.baseURL}/ai/mp/${constituencySlug}/anomalies`);
    return response.json();
  }
}

export default APIService;