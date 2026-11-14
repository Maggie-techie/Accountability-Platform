"""
Pydantic output schemas for AI endpoints.
All LLM responses must validate against these schemas.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# Base Schemas
# ============================================================

class ChartData(BaseModel):
    """Chart data structure - frontend renders charts separately."""
    sample_array: list = Field(default_factory=list)
    sample_labels: list = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standardized error response that won't be cached."""
    _error: bool = True
    narrative_fields: dict
    chart_data: ChartData = Field(default_factory=ChartData)


# ============================================================
# MP / Constituency Module Schemas
# ============================================================

class RiskScoreNarrative(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["High", "Medium", "Low"]
    summary: str = Field(min_length=50)
    key_drivers: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class RiskScoreOutput(BaseModel):
    narrative_fields: RiskScoreNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class RiskLevelNarrative(BaseModel):
    risk_level: Literal["High", "Medium", "Low"]
    summary: str = Field(min_length=50)
    anomalies_found: int = Field(ge=0)
    top_anomalies: list[dict] = Field(default_factory=list)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class RiskLevelOutput(BaseModel):
    narrative_fields: RiskLevelNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class SummaryNarrative(BaseModel):
    constituency_name: str
    mp_name: str
    financial_health: Literal["Strong", "Moderate", "Weak"]
    summary: str = Field(min_length=100)
    key_achievements: list[str] = Field(min_length=1, max_length=5)
    key_concerns: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class SummaryOutput(BaseModel):
    narrative_fields: SummaryNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class AnomalyItem(BaseModel):
    title: str
    description: str = Field(min_length=30)
    severity: Literal["High", "Medium", "Low"]
    amount_at_risk: str
    category: Literal["procurement", "payroll", "budget", "project", "other"]
    year: str
    source: str


class AnomaliesNarrative(BaseModel):
    anomalies_found: int = Field(ge=0)
    summary: str = Field(min_length=50)
    anomalies: list[AnomalyItem] = Field(default_factory=list)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class AnomaliesOutput(BaseModel):
    narrative_fields: AnomaliesNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class PeerRankNarrative(BaseModel):
    rank: int = Field(ge=1)
    total_constituencies: int = Field(ge=1)
    percentile: int = Field(ge=0, le=100)
    summary: str = Field(min_length=50)
    strengths: list[str] = Field(min_length=1, max_length=5)
    weaknesses: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class PeerRankOutput(BaseModel):
    narrative_fields: PeerRankNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class PriorityAction(BaseModel):
    title: str
    description: str = Field(min_length=30)
    difficulty: Literal["Easy", "Medium", "Hard"]
    impact: Literal["High", "Medium", "Low"]
    timeframe: Literal["Immediate", "Short-term", "Long-term"]
    channels: list[str] = Field(min_length=1, max_length=5)


class CitizenActionsNarrative(BaseModel):
    summary: str = Field(min_length=50)
    priority_actions: list[PriorityAction] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class CitizenActionsOutput(BaseModel):
    narrative_fields: CitizenActionsNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class DataSourceItem(BaseModel):
    name: str
    type: Literal["audit", "financial", "project", "other"]
    coverage: Literal["Full", "Partial", "Limited"]
    reliability: Literal["High", "Medium", "Low"]
    notes: str


class DataSourcesNarrative(BaseModel):
    summary: str = Field(min_length=50)
    sources: list[DataSourceItem] = Field(min_length=1, max_length=10)
    gaps: list[str] = Field(default_factory=list)
    what_this_means: str = Field(min_length=30)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class DataSourcesOutput(BaseModel):
    narrative_fields: DataSourcesNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


# ============================================================
# Governor Module Schemas
# ============================================================

class FiscalHealthNarrative(BaseModel):
    overall_rating: Literal["Strong", "Moderate", "Weak"]
    summary: str = Field(min_length=100)
    revenue_analysis: str = Field(min_length=50)
    expenditure_analysis: str = Field(min_length=50)
    debt_position: str = Field(min_length=30)
    audit_outcomes: str = Field(min_length=50)
    key_strengths: list[str] = Field(min_length=1, max_length=5)
    key_risks: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class FiscalHealthOutput(BaseModel):
    narrative_fields: FiscalHealthNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class DepartmentAbsorptionItem(BaseModel):
    name: str
    absorption_rate: float = Field(ge=0, le=100)
    rating: Literal["Excellent", "Good", "Fair", "Poor"]
    narrative: str = Field(min_length=30)


class DeptAbsorptionNarrative(BaseModel):
    summary: str = Field(min_length=50)
    departments: list[DepartmentAbsorptionItem] = Field(min_length=1)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class DeptAbsorptionOutput(BaseModel):
    narrative_fields: DeptAbsorptionNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class RevenueStream(BaseModel):
    name: str
    target: float = Field(ge=0)
    actual: float = Field(ge=0)
    performance: Literal["On Target", "Below Target", "Above Target"]
    narrative: str = Field(min_length=30)


class OSRAnalysisNarrative(BaseModel):
    summary: str = Field(min_length=50)
    trend: Literal["Improving", "Stable", "Declining"]
    revenue_streams: list[RevenueStream] = Field(min_length=1)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class OSRAnalysisOutput(BaseModel):
    narrative_fields: OSRAnalysisNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class DepartmentFlagItem(BaseModel):
    department: str
    flag_type: Literal["absorption", "audit", "procurement", "payroll", "project", "other"]
    severity: Literal["High", "Medium", "Low"]
    description: str = Field(min_length=30)
    amount_at_risk: str
    recommended_action: str


class DepartmentFlagsNarrative(BaseModel):
    summary: str = Field(min_length=50)
    flags: list[DepartmentFlagItem] = Field(default_factory=list)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class DepartmentFlagsOutput(BaseModel):
    narrative_fields: DepartmentFlagsNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class RiskItem(BaseModel):
    title: str
    description: str = Field(min_length=50)
    category: Literal["fiscal", "governance", "service_delivery", "corruption", "compliance", "other"]
    severity: Literal["Critical", "High", "Medium", "Low"]
    likelihood: Literal["Very Likely", "Likely", "Possible", "Unlikely"]
    affected_areas: list[str] = Field(min_length=1)
    mitigation: str = Field(min_length=30)


class TopRisksNarrative(BaseModel):
    summary: str = Field(min_length=50)
    risks: list[RiskItem] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class TopRisksOutput(BaseModel):
    narrative_fields: TopRisksNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


# ============================================================
# County / Cross-Leader Schemas
# ============================================================

class CountyNarrativeNarrative(BaseModel):
    county_name: str
    governor_name: str
    mps: list[str] = Field(min_length=1)
    executive_summary: str = Field(min_length=100)
    ngcdf_overview: str = Field(min_length=50)
    executive_overview: str = Field(min_length=50)
    cross_leader_analysis: str = Field(min_length=50)
    shared_risks: list[str] = Field(min_length=1, max_length=5)
    collaborative_opportunities: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class CountyNarrativeOutput(BaseModel):
    narrative_fields: CountyNarrativeNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class FindingItem(BaseModel):
    title: str
    description: str = Field(min_length=50)
    severity: Literal["High", "Medium", "Low"]
    category: Literal["misappropriation", "procurement", "payroll", "budget", "project", "compliance", "other"]
    entity: Literal["MP", "Governor", "Department", "Constituency"]
    amount_at_risk: str
    year: str
    recommendation: str = Field(min_length=30)
    citizen_action: str = Field(min_length=20)


class FindingClassifierNarrative(BaseModel):
    summary: str = Field(min_length=50)
    findings: list[FindingItem] = Field(default_factory=list)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class FindingClassifierOutput(BaseModel):
    narrative_fields: FindingClassifierNarrative
    chart_data: ChartData = Field(default_factory=ChartData)


class CompareNarrative(BaseModel):
    summary: str = Field(min_length=100)
    mp_strengths: list[str] = Field(min_length=1, max_length=5)
    mp_weaknesses: list[str] = Field(min_length=1, max_length=5)
    governor_strengths: list[str] = Field(min_length=1, max_length=5)
    governor_weaknesses: list[str] = Field(min_length=1, max_length=5)
    shared_challenges: list[str] = Field(min_length=1, max_length=5)
    what_this_means: str = Field(min_length=50)
    citizen_actions: list[str] = Field(min_length=1, max_length=5)
    data_quality_note: str


class CompareOutput(BaseModel):
    narrative_fields: CompareNarrative
    chart_data: dict = Field(default_factory=dict)  # radar_data merged server-side


# ============================================================
# Schema Registry - maps module to output schema
# ============================================================

MP_SCHEMAS = {
    "risk_score": RiskScoreOutput,
    "risk_level": RiskLevelOutput,
    "summary": SummaryOutput,
    "anomalies": AnomaliesOutput,
    "peer_rank": PeerRankOutput,
    "citizen_actions": CitizenActionsOutput,
    "data_sources": DataSourcesOutput,
}

GOVERNOR_SCHEMAS = {
    "fiscal_health": FiscalHealthOutput,
    "dept_absorption": DeptAbsorptionOutput,
    "osr_analysis": OSRAnalysisOutput,
    "department_flags": DepartmentFlagsOutput,
    "top_risks": TopRisksOutput,
}

COUNTY_SCHEMAS = {
    "county_narrative": CountyNarrativeOutput,
    "finding_classifier": FindingClassifierOutput,
    "compare": CompareOutput,
}


def get_schema(module: str, leader_type: str = "mp") -> type[BaseModel]:
    """Get the output schema for a module."""
    if leader_type == "mp":
        return MP_SCHEMAS.get(module)
    elif leader_type == "governor":
        return GOVERNOR_SCHEMAS.get(module)
    elif leader_type == "county":
        return COUNTY_SCHEMAS.get(module)
    return None