// Mock data standing in for the Flask + MongoDB API.
// Every function here mirrors a real endpoint shape, so swapping in
// `fetch('/api/...')` later doesn't change how pages consume the data.

export const governor = {
  id: 'governor-kahiga',
  name: 'Mutahi Kahiga',
  position: 'Governor',
  party: 'UDA',
  tenure: '2022 - 2027',
  county: 'Nyeri',
  accountabilityScore: 68,
  scoreCategory: 'Moderate',
  summary:
    'Above-average development absorption in FY2024/25, offset by two adverse audit findings in county health procurement.',
  photo: null,
}

export const constituencies = [
  {
    slug: 'kieni',
    name: 'Kieni',
    mp: 'Hon. Njoroge Wainaina',
    party: 'UDA',
    auditStatus: 'Qualified',
    accountabilityScore: 74,
    totalAllocationKshm: 760.0,
    misappropriationCount: 1,
    correctAppropriationCount: 4,
  },
  {
    slug: 'mathira',
    name: 'Mathira',
    mp: 'Hon. Eric Mwangi Wamumbi',
    party: 'UDA',
    auditStatus: 'Adverse',
    accountabilityScore: 41,
    totalAllocationKshm: 698.3,
    misappropriationCount: 3,
    correctAppropriationCount: 2,
  },
  {
    slug: 'othaya',
    name: 'Othaya',
    mp: 'Hon. Gichuki Mugambi',
    party: 'DAP-K',
    auditStatus: 'Unqualified',
    accountabilityScore: 88,
    totalAllocationKshm: 512.4,
    misappropriationCount: 0,
    correctAppropriationCount: 5,
  },
  {
    slug: 'tetu',
    name: 'Tetu',
    mp: 'Hon. Geoffrey Wandeto',
    party: 'UDA',
    auditStatus: 'Qualified',
    accountabilityScore: 69,
    totalAllocationKshm: 595.3,
    misappropriationCount: 2,
    correctAppropriationCount: 3,
  },
  {
    slug: 'mukurweini',
    name: 'Mukurwe-ini',
    mp: 'Hon. Beatrice Nyaga',
    party: 'UDA',
    auditStatus: 'Unqualified',
    accountabilityScore: 81,
    totalAllocationKshm: 487.9,
    misappropriationCount: 0,
    correctAppropriationCount: 4,
  },
  {
    slug: 'nyeri_town',
    name: 'Nyeri Town',
    mp: 'Hon. Duncan Mathenge',
    party: 'UDA',
    auditStatus: 'Qualified',
    accountabilityScore: 63,
    totalAllocationKshm: 540.1,
    misappropriationCount: 2,
    correctAppropriationCount: 3,
  },
]

export const allocationTrend = [
  { fy: '2022/23', Kieni: 165.7, Mathira: 151.9, Othaya: 118.0, Tetu: 131.3, 'Mukurwe-ini': 110.2, 'Nyeri Town': 120.8 },
  { fy: '2023/24', Kieni: 181.0, Mathira: 168.0, Othaya: 126.5, Tetu: 141.0, 'Mukurwe-ini': 118.9, 'Nyeri Town': 129.4 },
  { fy: '2024/25', Kieni: 206.6, Mathira: 188.4, Othaya: 133.9, Tetu: 161.5, 'Mukurwe-ini': 127.6, 'Nyeri Town': 138.7 },
  { fy: '2025/26', Kieni: 206.6, Mathira: 188.4, Othaya: 133.9, Tetu: 161.5, 'Mukurwe-ini': 131.2, 'Nyeri Town': 151.2 },
]

export const countyFinances = {
  revenueSources: [
    { source: 'Equitable Share', amountKshb: 5.8 },
    { source: 'Conditional Grants', amountKshb: 1.2 },
    { source: 'Own-Source Revenue', amountKshb: 0.74 },
  ],
  budgetVsExpenditure: [
    { fy: '2022/23', budget: 7.1, expenditure: 6.4 },
    { fy: '2023/24', budget: 7.4, expenditure: 6.9 },
    { fy: '2024/25', budget: 7.8, expenditure: 7.2 },
    { fy: '2025/26', budget: 8.0, expenditure: 3.6 },
  ],
  developmentVsRecurrent: [
    { fy: '2023/24', development: 2.6, recurrent: 4.3 },
    { fy: '2024/25', development: 2.9, recurrent: 4.3 },
    { fy: '2025/26', development: 1.4, recurrent: 2.2 },
  ],
}

export const departments = [
  { department: 'Health', financialYear: '2024/25', approvedBudgetKshm: 1240, q3SpendKshm: 812, absorptionRate: 65.5, status: 'On Track' },
  { department: 'Water & Irrigation', financialYear: '2024/25', approvedBudgetKshm: 640, q3SpendKshm: 298, absorptionRate: 46.6, status: 'Behind' },
  { department: 'Roads & Infrastructure', financialYear: '2024/25', approvedBudgetKshm: 980, q3SpendKshm: 701, absorptionRate: 71.5, status: 'On Track' },
  { department: 'Agriculture', financialYear: '2024/25', approvedBudgetKshm: 410, q3SpendKshm: 129, absorptionRate: 31.5, status: 'Critical' },
  { department: 'Education', financialYear: '2024/25', approvedBudgetKshm: 355, q3SpendKshm: 240, absorptionRate: 67.6, status: 'On Track' },
]

export const auditFindings = [
  {
    id: 'AF-001',
    entity: 'Mathira NG-CDF',
    entityType: 'constituency',
    category: 'Procurement irregularity',
    financialYear: '2023/24',
    amountKshm: 18.4,
    severity: 'High',
    finding:
      'Payment made for a bursary disbursement exercise with no supporting beneficiary list.',
  },
  {
    id: 'AF-002',
    entity: 'County Health Department',
    entityType: 'department',
    category: 'Unsupported expenditure',
    financialYear: '2024/25',
    amountKshm: 32.1,
    severity: 'High',
    finding: 'Medical supplies procurement lacked competitive tendering documentation.',
  },
  {
    id: 'AF-003',
    entity: 'Nyeri Town NG-CDF',
    entityType: 'constituency',
    category: 'Delayed project',
    financialYear: '2023/24',
    amountKshm: 9.7,
    severity: 'Medium',
    finding: 'Classroom construction project stalled at 40% completion for 14 months.',
  },
  {
    id: 'AF-004',
    entity: 'Tetu NG-CDF',
    entityType: 'constituency',
    category: 'Procurement irregularity',
    financialYear: '2024/25',
    amountKshm: 6.2,
    severity: 'Medium',
    finding: 'Water project contractor paid in full before completion certificate was issued.',
  },
]

export const anomalies = [
  {
    id: 'AN-1042',
    title: 'Unusual spike in bursary disbursement, Mathira',
    entity: 'Mathira Constituency',
    entityType: 'Constituency',
    category: 'Expenditure pattern',
    financialYear: '2023/24',
    severity: 'High',
    status: 'Under review',
    expected: 42.0,
    observed: 71.5,
    unit: 'KSh M',
    summary:
      'Bursary disbursements in Q3 were 70% above the constituency’s five-year seasonal average, with no matching increase in registered beneficiaries.',
    limeFeatures: [
      { feature: 'Disbursement-to-beneficiary ratio', weight: 0.41 },
      { feature: 'Quarter-on-quarter change', weight: 0.27 },
      { feature: 'Vendor concentration', weight: 0.18 },
      { feature: 'Prior-year seasonal pattern', weight: -0.09 },
    ],
    relatedFindingId: 'AF-001',
  },
  {
    id: 'AN-1039',
    title: 'Absorption rate anomaly, Agriculture department',
    entity: 'Agriculture Department',
    entityType: 'Department',
    category: 'Budget absorption',
    financialYear: '2024/25',
    severity: 'Medium',
    status: 'Flagged',
    expected: 55.0,
    observed: 31.5,
    unit: '% absorption',
    summary:
      'Absorption rate is significantly below both the department’s own trend and peer departments at the same point in the financial year.',
    limeFeatures: [
      { feature: 'Deviation from peer departments', weight: 0.38 },
      { feature: 'Quarter-on-quarter change', weight: 0.24 },
      { feature: 'Procurement cycle delay', weight: 0.21 },
      { feature: 'Prior-year absorption', weight: -0.05 },
    ],
    relatedFindingId: null,
  },
  {
    id: 'AN-1031',
    title: 'Contractor payment sequencing, Tetu water project',
    entity: 'Tetu Constituency',
    entityType: 'Constituency',
    category: 'Payment pattern',
    financialYear: '2024/25',
    severity: 'Medium',
    status: 'Under review',
    expected: 0,
    observed: 1,
    unit: 'full payment before completion',
    summary:
      'Full contract value was paid out before a completion certificate was logged, which is atypical against the constituency’s own payment history.',
    limeFeatures: [
      { feature: 'Payment-to-milestone ratio', weight: 0.44 },
      { feature: 'Certificate lag time', weight: 0.31 },
      { feature: 'Contractor payment history', weight: 0.12 },
    ],
    relatedFindingId: 'AF-004',
  },
  {
    id: 'AN-1024',
    title: 'Minor variance in Othaya development spend',
    entity: 'Othaya Constituency',
    entityType: 'Constituency',
    category: 'Expenditure pattern',
    financialYear: '2024/25',
    severity: 'Low',
    status: 'Reviewed - no issue',
    expected: 118.0,
    observed: 126.4,
    unit: 'KSh M',
    summary: 'Spend is slightly above projection, consistent with an approved mid-year reallocation.',
    limeFeatures: [
      { feature: 'Approved reallocation flag', weight: -0.36 },
      { feature: 'Quarter-on-quarter change', weight: 0.14 },
    ],
    relatedFindingId: null,
  },
]

export const reports = [
  { id: 'R-01', title: 'Nyeri County Accountability Report FY2024/25', category: 'Accountability Reports', entity: 'Nyeri County', financialYear: '2024/25', datePublished: '2025-08-12' },
  { id: 'R-02', title: 'Mathira NG-CDF Audit Summary FY2023/24', category: 'Auditor-General Reports', entity: 'Mathira', financialYear: '2023/24', datePublished: '2024-11-03' },
  { id: 'R-03', title: 'County Budget Implementation Review Q3', category: 'County Budget Reports', entity: 'Nyeri County', financialYear: '2024/25', datePublished: '2025-04-22' },
  { id: 'R-04', title: 'Departmental Absorption Performance Report', category: 'Departmental Performance Reports', entity: 'Nyeri County', financialYear: '2024/25', datePublished: '2025-05-30' },
  { id: 'R-05', title: 'Tetu NG-CDF Allocations & Utilisation', category: 'NG-CDF Reports', entity: 'Tetu', financialYear: '2024/25', datePublished: '2025-02-18' },
]

export const adminSummary = {
  totalLeaders: 7,
  totalDatasets: 6,
  totalRecords: 4213,
  recentImports: 3,
  validationStatus: 'Attention needed',
  detectedAnomalies: 12,
  modelStatus: 'Trained',
  lastTrained: '2025-08-30',
}

export const importHistory = [
  { id: 'IMP-201', filename: 'Nyeri_Governor_Fiscal_2022_2027.xlsx', category: 'County Finance', status: 'Completed', records: 96, date: '2025-08-30' },
  { id: 'IMP-200', filename: 'Nyeri_NGCDF_2022_2027.xlsx', category: 'NG-CDF Allocations', status: 'Completed', records: 24, date: '2025-08-30' },
  { id: 'IMP-199', filename: 'dept_spending_q2.xlsx', category: 'Departmental Data', status: 'Failed - format error', records: 0, date: '2025-08-14' },
]

export function scoreCategory(score) {
  if (score >= 75) return { label: 'Strong', tone: 'good' }
  if (score >= 55) return { label: 'Moderate', tone: 'watch' }
  return { label: 'Needs Attention', tone: 'risk' }
}
