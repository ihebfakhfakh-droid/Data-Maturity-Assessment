package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.GenerateReportRequestDto;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.util.LinkedHashMap;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class GenerateReportRequestDtoSerializationTest {

    private final JsonMapper objectMapper = JsonMapper.builder().build();

    @Test
    void serializesTargetScoreWithExactPropertyName() {
        Map<String, Integer> currentScores = new LinkedHashMap<>();
        currentScores.put("ndi_dg_01", 2);
        currentScores.put("ndi_dq_01", 1);

        Map<String, Double> domainWeights = new LinkedHashMap<>();
        domainWeights.put("DG", 11.75);
        domainWeights.put("DQ", 11.93);

        Map<String, Integer> domainScores = new LinkedHashMap<>();
        domainScores.put("DG", 2);
        domainScores.put("DQ", 1);

        Map<String, Double> weightedScores = new LinkedHashMap<>();
        weightedScores.put("DG", 0.995);
        weightedScores.put("DQ", 0.505);

        GenerateReportRequestDto dto = new GenerateReportRequestDto(
                1.83,
                2.83,
                100.01,
                domainWeights,
                domainScores,
                weightedScores,
                currentScores,
                "NDI",
                "Projet Demo",
                "oussema lazez",
                1,
                "20/07/2026 18:00",
                "20/07/2026 18:30"
        );

        String json = objectMapper.writeValueAsString(dto);

        assertThat(json).contains("\"targetScore\":2.83");
        assertThat(json).doesNotContain("\"target_score\"");
        assertThat(json).doesNotContain("\"TargetScore\"");
        assertThat(json).contains("\"scoreGlobalActual\":1.83");
        assertThat(json).contains("\"totalWeights\":100.01");
        assertThat(json).contains("\"framework\":\"NDI\"");
        assertThat(json).contains("\"clientName\":\"oussema lazez\"");
        assertThat(json).contains("\"versionNumber\":1");
        assertThat(json).contains("\"generationDate\"");
        assertThat(json).contains("\"currentScores\"");
        assertThat(json).contains("\"domainWeights\"");

        @SuppressWarnings("unchecked")
        Map<String, Object> parsed = objectMapper.readValue(json, Map.class);
        assertThat(parsed).containsKey("targetScore");
        assertThat(parsed.get("targetScore")).isEqualTo(2.83);
        assertThat(parsed).doesNotContainKey("target_score");
    }

    @Test
    void sanitizeLogKeepsTargetScoreVisible() {
        String json = "{\"targetScore\":2.83,\"currentScores\":{\"ndi_dg_01\":2},\"framework\":\"NDI\"}";
        String sanitized = AiRecommendationClient.sanitizeJsonForLog(json);
        assertThat(sanitized).contains("\"targetScore\":2.83");
        assertThat(sanitized).contains("framework");
        assertThat(sanitized).contains("redacted");
    }
}
