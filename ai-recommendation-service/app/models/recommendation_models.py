from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class BestPathRequest(BaseModel):
    scoreGlobalActual: Optional[float] = Field(default=None, ge=0, le=5)
    targetScore: float = Field(..., ge=0, le=5)
    totalWeights: Optional[float] = None
    domainWeights: Optional[Dict[str, float]] = None
    domainScores: Optional[Dict[str, int]] = None
    weightedScores: Optional[Dict[str, float]] = None
    currentScores: Dict[str, int] = Field(default_factory=dict)


class GenerateReportRequest(BestPathRequest):
    """Best-path payload plus optional metadata for the PDF report header."""

    framework: str = "NDI"
    projectName: Optional[str] = None
    clientName: Optional[str] = None
    versionNumber: Optional[int] = None
    submittedAt: Optional[str] = None
    generationDate: Optional[str] = None


class ScoreTransition(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    from_level: int = Field(alias="from")
    to: int
    transitionKey: str
    effort: int
    explanation: str = ""


class QuestionToImprove(BaseModel):
    model_config = ConfigDict(populate_by_name=True, ser_json_by_alias=True)

    questionCode: str
    questionId: str = ""
    questionText: str
    currentScore: int
    targetScore: int
    totalQuestionEffort: int
    transitions: list[ScoreTransition]
    groundedRecommendation: str = ""
    recommendationSource: str = "knowledge_base"
    recommendation: str = ""


class BestPathSummary(BaseModel):
    optimizationLogic: str = ""
    selectedDomainsReason: str = ""
    effortInterpretation: str = ""
    finalValidation: str = ""


class BestPathStatus(BaseModel):
    targetReached: bool
    message: str


class ScoreSummary(BaseModel):
    scoreGlobalInitial: float
    scoreGlobalTarget: float
    targetGap: float
    gainTotal: float
    scoreGlobalFinalEstimated: float
    overGain: float
    effortTotal: int


class OptimizationSummary(BaseModel):
    strategy: str
    selectedDomainsCount: int
    selectedQuestionsCount: int
    whyThisPath: str
    effortExplanation: str


class OptimizationValidation(BaseModel):
    algorithm: str = "dynamic_programming"
    objective: str = "minimum_total_effort"
    totalWeight: float
    targetReached: bool
    optimalityVerified: bool
    roundingUsedDuringOptimization: bool = False


class BestPathTableRow(BaseModel):
    priority: int
    domainId: str
    domainName: str
    domainWeight: float
    currentDomainScore: int
    targetDomainScore: int
    globalScoreGain: float
    totalEffort: int
    efficiencyRatio: float


class DetailedActionDomain(BaseModel):
    priority: int
    domainId: str
    domainName: str
    domainObjective: str
    questionsToImprove: list[QuestionToImprove]


class MathematicalValidation(BaseModel):
    formula: str = "scoreGlobalFinalEstimated = scoreGlobalInitial + gainTotal"
    calculation: str
    targetReached: bool


class BestPathResponse(BaseModel):
    success: bool
    status: BestPathStatus
    scoreSummary: ScoreSummary
    optimizationSummary: OptimizationSummary
    optimizationValidation: OptimizationValidation | None = None
    bestPathTable: list[BestPathTableRow] = Field(default_factory=list)
    detailedActions: list[DetailedActionDomain] = Field(default_factory=list)
    mathematicalValidation: MathematicalValidation
    warnings: list[str] = Field(default_factory=list)


class CalculationValidation(BaseModel):
    formula: str = ""
    scoreGlobalInitial: float | None = None
    scoreGlobalTarget: float | None = None
    totalGainFromBestPath: float | None = None
    scoreGlobalFinalEstimated: float | None = None
    overGain: float | None = None
    targetReached: bool | None = None


class BestPathDomainItem(BaseModel):
    priority: int | None = None
    domainId: str
    domainName: str
    domainWeight: float
    currentDomainScore: int
    targetDomainScore: int
    domainScoreGain: int | None = None
    globalScoreGain: float
    totalEffort: int
    efficiencyRatio: float | None = None
    questionsToImprove: list[QuestionToImprove]


# Legacy aliases kept for imports in existing modules.
BestPathSuccessResponse = BestPathResponse
BestPathFailureResponse = BestPathResponse


class ProfessionalAnalysis(BaseModel):
    executiveSummary: str = ""
    detailedActionPlan: str = ""
    finalValidation: str = ""
    strategicConclusion: str = ""


class ConsultingReport(BaseModel):
    introduction: str = ""
    strategicObjective: str = ""
    executiveSummary: str = ""
    bestPathTable: str = ""
    detailedActionPlan: str = ""
    mathematicalProof: str = ""
    strategicConclusion: str = ""


class EffortTransition(BaseModel):
    effort: int
    explanation: str


class FrameworkQuestion(BaseModel):
    id: str
    text: str
    effort_transitions: dict[str, EffortTransition]

    @property
    def questionCode(self) -> str:
        return self.id

    @property
    def questionText(self) -> str:
        return self.text

    @property
    def maxScore(self) -> int:
        return 5

    def effort_for_transition(self, from_score: int, to_score: int) -> int:
        if to_score <= from_score:
            return 0
        total = 0
        for level in range(from_score, to_score):
            key = f"{level}_to_{level + 1}"
            transition = self.effort_transitions.get(key)
            if transition is None:
                raise ValueError(
                    f"Transition effort missing for {self.id}: {key}"
                )
            total += transition.effort
        return total

    def transition_explanations(self, from_score: int, to_score: int) -> list[str]:
        if to_score <= from_score:
            return []
        explanations: list[str] = []
        for level in range(from_score, to_score):
            key = f"{level}_to_{level + 1}"
            transition = self.effort_transitions.get(key)
            if transition is not None:
                explanations.append(transition.explanation)
        return explanations


class FrameworkDomain(BaseModel):
    domain_id: str
    domain_name: str
    weight: float
    questions: list[FrameworkQuestion]

    @property
    def domainId(self) -> str:
        return self.domain_id

    @property
    def domainName(self) -> str:
        return self.domain_name

    @property
    def domainWeight(self) -> float:
        return self.weight


class NDIFramework(BaseModel):
    framework: str
    total_domains: int
    effort_scale: dict[str, str]
    domains: list[FrameworkDomain]

    def get_question(self, question_id: str) -> FrameworkQuestion | None:
        for domain in self.domains:
            for question in domain.questions:
                if question.id == question_id:
                    return question
        return None

    def get_domain(self, domain_id: str) -> FrameworkDomain | None:
        for domain in self.domains:
            if domain.domain_id == domain_id:
                return domain
        return None


class DomainImprovementOption(BaseModel):
    domainId: str
    domainName: str
    domainWeight: float
    currentDomainScore: int
    targetDomainScore: int
    totalEffort: int
    globalScoreGain: float
    questionsToImprove: list[dict[str, Any]]
