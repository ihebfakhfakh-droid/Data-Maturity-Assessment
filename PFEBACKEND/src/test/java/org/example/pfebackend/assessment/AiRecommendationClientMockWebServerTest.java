package org.example.pfebackend.assessment;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.example.pfebackend.assessment.dto.GenerateReportRequestDto;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.http.codec.json.JacksonJsonDecoder;
import org.springframework.http.codec.json.JacksonJsonEncoder;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;

class AiRecommendationClientMockWebServerTest {

    private MockWebServer server;
    private AiRecommendationClient client;
    private final JsonMapper jsonMapper = JsonMapper.builder().build();

    @BeforeEach
    void setUp() throws IOException {
        server = new MockWebServer();
        server.start();

        ExchangeStrategies strategies = ExchangeStrategies.builder()
                .codecs(configurer -> {
                    configurer.defaultCodecs().jacksonJsonEncoder(new JacksonJsonEncoder(jsonMapper));
                    configurer.defaultCodecs().jacksonJsonDecoder(new JacksonJsonDecoder(jsonMapper));
                })
                .build();

        WebClient webClient = WebClient.builder()
                .baseUrl(server.url("/").toString().replaceAll("/$", ""))
                .exchangeStrategies(strategies)
                .build();

        client = new AiRecommendationClient(
                webClient,
                jsonMapper,
                server.url("/").toString().replaceAll("/$", ""),
                30
        );
    }

    @AfterEach
    void tearDown() throws IOException {
        server.shutdown();
    }

    @Test
    void postGenerateReportAttachesJsonBodyWithTargetScoreAnd42CurrentScores() throws Exception {
        byte[] pdf = "%PDF-1.4 mock recommendation report".getBytes(StandardCharsets.UTF_8);
        server.enqueue(new MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", MediaType.APPLICATION_PDF_VALUE)
                .setBody(new okio.Buffer().write(pdf)));

        GenerateReportRequestDto requestDto = sampleRequestWith42Scores(2.83);

        byte[] response = client.generateReportPdf(requestDto);
        assertThat(response).startsWith("%PDF".getBytes(StandardCharsets.UTF_8));

        RecordedRequest recorded = server.takeRequest(5, TimeUnit.SECONDS);
        assertThat(recorded).isNotNull();
        assertThat(recorded.getMethod()).isEqualTo("POST");
        assertThat(recorded.getPath()).isEqualTo("/api/recommendations/generate-report");

        String contentType = recorded.getHeader("Content-Type");
        assertThat(contentType).isNotNull().contains("application/json");

        String body = recorded.getBody().readUtf8();
        assertThat(body).isNotBlank();
        assertThat(body).contains("\"targetScore\":2.83");
        assertThat(body).doesNotContain("\"target_score\"");

        @SuppressWarnings("unchecked")
        Map<String, Object> parsed = jsonMapper.readValue(body, Map.class);
        assertThat(parsed.get("targetScore")).isEqualTo(2.83);

        @SuppressWarnings("unchecked")
        Map<String, Object> currentScores = (Map<String, Object>) parsed.get("currentScores");
        assertThat(currentScores).isNotNull().hasSize(42);
    }

    private static GenerateReportRequestDto sampleRequestWith42Scores(double targetScore) {
        Map<String, Integer> currentScores = new LinkedHashMap<>();
        for (int i = 1; i <= 42; i++) {
            currentScores.put(String.format("ndi_q_%02d", i), (i % 5));
        }

        Map<String, Double> domainWeights = new LinkedHashMap<>();
        domainWeights.put("DG", 11.75);
        Map<String, Integer> domainScores = new LinkedHashMap<>();
        domainScores.put("DG", 2);
        Map<String, Double> weightedScores = new LinkedHashMap<>();
        weightedScores.put("DG", 0.23);

        return new GenerateReportRequestDto(
                1.83,
                targetScore,
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
                "20/07/2026 19:00"
        );
    }
}
