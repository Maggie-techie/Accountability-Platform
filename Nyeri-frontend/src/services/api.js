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

    // Fetch scores, allocations, and audit findings for each constituency in parallel
    const [scores, allocations, auditFindings, mps] = await Promise.all([
      Promise.all(constituencies.map(c => this.getConstituencyScore(c.slug).catch(() => ({ score: null })))),
      Promise.all(constituencies.map(c => this.getConstituencyAllocations(c.slug).catch(() => ({ allocations: [] })))),
      Promise.all(constituencies.map(c => this.getConstituencyAuditFindings(c.slug).catch(() => ({ audit_findings: [] })))),
      Promise.all(constituencies.map(c => this.getMPByConstituency(c.slug).catch(() => ({ }))))
    ]);

    return constituencies.map((c, i) => {
      const constituencyAllocations = allocations[i]?.allocations || allocations[i] || [];
      const constituencyAudit = auditFindings[i]?.audit_findings || auditFindings[i] || [];
      const mpData = mps[i] || {};

      // Calculate total allocation
      const totalAllocationKshm = constituencyAllocations.reduce((sum, a) => sum + (a.amount_kshm || 0), 0);

      // Count misappropriations
      const misappropriationCount = constituencyAudit.filter(f => f.finding_type?.toLowerCase() === 'misappropriation').length;

      // Get audit status from MP data
      const auditStatus = mpData.audit_status || mpData.auditStatus || 'Unknown';

      return {
        ...c,
        accountabilityScore: scores[i]?.score ?? c.accountabilityScore ?? null,
        totalAllocationKshm: totalAllocationKshm,
        misappropriationCount: misappropriationCount,
        auditStatus: auditStatus,
        mp: mpData.name ? { name: mpData.name, party: mpData.party } : c.mp
      };
    });
  }

  // Get MP by constituency slug
  static async getMPByConstituency(slug) {
    const response = await fetch(`${this.baseURL}/constituency/mps/${slug}`);
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

  // County-wide aggregated report (Governor + all Constituencies)
  static async downloadCountyPDFReport() {
    const response = await fetch(`${this.baseURL}/reports/county/pdf`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to generate report' }));
      throw new Error(error.error || error.details || 'Failed to generate county report');
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

  // County findings classifier (for anomalies with severity)
  static async getCountyFindingsClassifier(findingId = null, findingText = null) {
    const body = {};
    if (findingId) body.finding_id = findingId;
    if (findingText) body.finding_text = findingText;

    const response = await fetch(`${this.baseURL}/ai/findings/classifier`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    return response.json();
  }

  // Helper method for authenticated requests
  static async _authenticatedFetch(path, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${this.baseURL}${path}`, {
      ...options,
      headers
    });
    return response.json();
  }

  // =============================================================================
  // CRUD - Constituencies
  // =============================================================================
  static async createConstituency(data) {
    return this._authenticatedFetch('/constituency/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateConstituency(slug, data) {
    return this._authenticatedFetch(`/constituency/${slug}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteConstituency(slug) {
    return this._authenticatedFetch(`/constituency/${slug}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - MPs
  // =============================================================================
  static async createMP(data) {
    return this._authenticatedFetch('/constituency/mps', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateMP(slug, data) {
    return this._authenticatedFetch(`/constituency/mps/${slug}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteMP(slug) {
    return this._authenticatedFetch(`/constituency/mps/${slug}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - Allocations
  // =============================================================================
  static async createAllocation(data) {
    return this._authenticatedFetch('/constituency/allocations', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateAllocation(allocationId, data) {
    return this._authenticatedFetch(`/constituency/allocations/${allocationId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteAllocation(allocationId) {
    return this._authenticatedFetch(`/constituency/allocations/${allocationId}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - Constituency Audit Findings
  // =============================================================================
  static async createConstituencyAuditFinding(data) {
    return this._authenticatedFetch('/constituency/audit', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateConstituencyAuditFinding(findingId, data) {
    return this._authenticatedFetch(`/constituency/audit/${findingId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteConstituencyAuditFinding(findingId) {
    return this._authenticatedFetch(`/constituency/audit/${findingId}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - Governor Profile
  // =============================================================================
  static async createGovernor(data) {
    return this._authenticatedFetch('/governor/', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateGovernor(data) {
    return this._authenticatedFetch('/governor/', {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteGovernor() {
    return this._authenticatedFetch('/governor/', {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - County Finances
  // =============================================================================
  static async createFinance(data) {
    return this._authenticatedFetch('/governor/finances', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateFinance(financeId, data) {
    return this._authenticatedFetch(`/governor/finances/${financeId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteFinance(financeId) {
    return this._authenticatedFetch(`/governor/finances/${financeId}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - Departments
  // =============================================================================
  static async createDepartment(data) {
    return this._authenticatedFetch('/governor/departments', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateDepartment(deptId, data) {
    return this._authenticatedFetch(`/governor/departments/${deptId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteDepartment(deptId) {
    return this._authenticatedFetch(`/governor/departments/${deptId}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // CRUD - County Audit Findings
  // =============================================================================
  static async createCountyAuditFinding(data) {
    return this._authenticatedFetch('/governor/audit', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  static async updateCountyAuditFinding(auditId, data) {
    return this._authenticatedFetch(`/governor/audit/${auditId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  static async deleteCountyAuditFinding(auditId) {
    return this._authenticatedFetch(`/governor/audit/${auditId}`, {
      method: 'DELETE'
    });
  }

  // =============================================================================
  // Dataset Upload
  // =============================================================================
  static async uploadDataset(file, datasetType) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('dataset_type', datasetType)

    const response = await fetch(`${this.baseURL}/dataset/upload`, {
      method: 'POST',
      body: formData
    })
    return response.json()
  }

  static async previewDataset(file, datasetType) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('dataset_type', datasetType)

    const response = await fetch(`${this.baseURL}/dataset/preview`, {
      method: 'POST',
      body: formData
    })
    return response.json()
  }

  static async validateDataset(file, datasetType, county, financialYear) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('dataset_type', datasetType)
    formData.append('county', county)
    formData.append('financial_year', financialYear)

    const response = await fetch(`${this.baseURL}/dataset/validate`, {
      method: 'POST',
      body: formData
    })
    return response.json()
  }

  static async importDataset(file, datasetType, county, financialYear) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('dataset_type', datasetType)
    formData.append('county', county)
    formData.append('financial_year', financialYear)

    const response = await fetch(`${this.baseURL}/dataset/import`, {
      method: 'POST',
      body: formData
    })
    return response.json()
  }

  // =============================================================================
  // Admin Users
  // =============================================================================
  static async getAdminUsers() {
    return this._authenticatedFetch('/admin/users')
  }

  static async createAdminUser(email) {
    return this._authenticatedFetch('/admin/users', {
      method: 'POST',
      body: JSON.stringify({ email })
    })
  }

  static async deleteAdminUser(email) {
    return this._authenticatedFetch(`/admin/users/${encodeURIComponent(email)}`, {
      method: 'DELETE'
    })
  }
}

export default APIService;