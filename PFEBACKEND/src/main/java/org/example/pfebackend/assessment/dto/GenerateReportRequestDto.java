package org.example.pfebackend.assessment.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Payload for FastAPI {@code GenerateReportRequest}.
 * Property names are fixed with {@link JsonProperty} so Jackson never renames {@code targetScore}.
 */
@JsonInclude(JsonInclude.Include.ALWAYS)
public class GenerateReportRequestDto {

    @JsonProperty("scoreGlobalActual")
    private Double scoreGlobalActual;

    @JsonProperty("targetScore")
    private Double targetScore;

    @JsonProperty("totalWeights")
    private Double totalWeights;

    @JsonProperty("domainWeights")
    private Map<String, Double> domainWeights = new LinkedHashMap<>();

    @JsonProperty("domainScores")
    private Map<String, Integer> domainScores = new LinkedHashMap<>();

    @JsonProperty("weightedScores")
    private Map<String, Double> weightedScores = new LinkedHashMap<>();

    @JsonProperty("currentScores")
    private Map<String, Integer> currentScores = new LinkedHashMap<>();

    @JsonProperty("framework")
    private String framework;

    @JsonProperty("projectName")
    private String projectName;

    @JsonProperty("clientName")
    private String clientName;

    @JsonProperty("versionNumber")
    private Integer versionNumber;

    @JsonProperty("submittedAt")
    private String submittedAt;

    @JsonProperty("generationDate")
    private String generationDate;

    public GenerateReportRequestDto() {
    }

    public GenerateReportRequestDto(
            Double scoreGlobalActual,
            Double targetScore,
            Double totalWeights,
            Map<String, Double> domainWeights,
            Map<String, Integer> domainScores,
            Map<String, Double> weightedScores,
            Map<String, Integer> currentScores,
            String framework,
            String projectName,
            String clientName,
            Integer versionNumber,
            String submittedAt,
            String generationDate
    ) {
        this.scoreGlobalActual = scoreGlobalActual;
        this.targetScore = targetScore;
        this.totalWeights = totalWeights;
        this.domainWeights = domainWeights != null ? domainWeights : new LinkedHashMap<>();
        this.domainScores = domainScores != null ? domainScores : new LinkedHashMap<>();
        this.weightedScores = weightedScores != null ? weightedScores : new LinkedHashMap<>();
        this.currentScores = currentScores != null ? currentScores : new LinkedHashMap<>();
        this.framework = framework;
        this.projectName = projectName;
        this.clientName = clientName;
        this.versionNumber = versionNumber;
        this.submittedAt = submittedAt;
        this.generationDate = generationDate;
    }

    public Double getScoreGlobalActual() {
        return scoreGlobalActual;
    }

    public void setScoreGlobalActual(Double scoreGlobalActual) {
        this.scoreGlobalActual = scoreGlobalActual;
    }

    public Double getTargetScore() {
        return targetScore;
    }

    public void setTargetScore(Double targetScore) {
        this.targetScore = targetScore;
    }

    public Double getTotalWeights() {
        return totalWeights;
    }

    public void setTotalWeights(Double totalWeights) {
        this.totalWeights = totalWeights;
    }

    public Map<String, Double> getDomainWeights() {
        return domainWeights;
    }

    public void setDomainWeights(Map<String, Double> domainWeights) {
        this.domainWeights = domainWeights != null ? domainWeights : new LinkedHashMap<>();
    }

    public Map<String, Integer> getDomainScores() {
        return domainScores;
    }

    public void setDomainScores(Map<String, Integer> domainScores) {
        this.domainScores = domainScores != null ? domainScores : new LinkedHashMap<>();
    }

    public Map<String, Double> getWeightedScores() {
        return weightedScores;
    }

    public void setWeightedScores(Map<String, Double> weightedScores) {
        this.weightedScores = weightedScores != null ? weightedScores : new LinkedHashMap<>();
    }

    public Map<String, Integer> getCurrentScores() {
        return currentScores;
    }

    public void setCurrentScores(Map<String, Integer> currentScores) {
        this.currentScores = currentScores != null ? currentScores : new LinkedHashMap<>();
    }

    public String getFramework() {
        return framework;
    }

    public void setFramework(String framework) {
        this.framework = framework;
    }

    public String getProjectName() {
        return projectName;
    }

    public void setProjectName(String projectName) {
        this.projectName = projectName;
    }

    public String getClientName() {
        return clientName;
    }

    public void setClientName(String clientName) {
        this.clientName = clientName;
    }

    public Integer getVersionNumber() {
        return versionNumber;
    }

    public void setVersionNumber(Integer versionNumber) {
        this.versionNumber = versionNumber;
    }

    public String getSubmittedAt() {
        return submittedAt;
    }

    public void setSubmittedAt(String submittedAt) {
        this.submittedAt = submittedAt;
    }

    public String getGenerationDate() {
        return generationDate;
    }

    public void setGenerationDate(String generationDate) {
        this.generationDate = generationDate;
    }

    /** Compatibility with previous record-style accessors used by the client. */
    public Double scoreGlobalActual() {
        return scoreGlobalActual;
    }

    public Double targetScore() {
        return targetScore;
    }

    public Map<String, Integer> currentScores() {
        return currentScores;
    }
}
