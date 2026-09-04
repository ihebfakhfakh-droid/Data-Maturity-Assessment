package org.example.pfebackend.evidence;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.ExchangeStrategies;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class AiAcceptanceCriteriaClientMockWebServerTest {

    private MockWebServer server;
    private AiAcceptanceCriteriaClient client;

    @BeforeEach
    void setUp() throws IOException {
        server = new MockWebServer();
        server.start();

        WebClient webClient = WebClient.builder()
                .baseUrl(server.url("/").toString().replaceAll("/$", ""))
                .exchangeStrategies(ExchangeStrategies.builder().build())
                .build();

        client = new AiAcceptanceCriteriaClient(
                webClient,
                server.url("/").toString().replaceAll("/$", ""),
                30
        );
    }

    @AfterEach
    void tearDown() throws IOException {
        server.shutdown();
    }

    @Test
    void postReportSendsMultipartAndReturnsPdf() throws Exception {
        byte[] pdf = "%PDF-1.4 mock acceptance criteria report".getBytes(StandardCharsets.UTF_8);
        server.enqueue(new MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", MediaType.APPLICATION_PDF_VALUE)
                .setBody(new okio.Buffer().write(pdf)));

        byte[] response = client.generateReportPdf(sampleRequest());
        assertThat(response).startsWith("%PDF".getBytes(StandardCharsets.UTF_8));

        RecordedRequest recorded = server.takeRequest(5, TimeUnit.SECONDS);
        assertThat(recorded).isNotNull();
        assertThat(recorded.getMethod()).isEqualTo("POST");
        assertThat(recorded.getPath()).isEqualTo("/api/acceptance-criteria/report");
        assertThat(recorded.getHeader("Content-Type")).contains("multipart/form-data");
        String body = recorded.getBody().readUtf8();
        assertThat(body).contains("name=\"question_code\"");
        assertThat(body).contains("ndi_dg_01");
        assertThat(body).contains("name=\"selected_score\"");
        assertThat(body).contains("name=\"client_full_name\"");
    }

    @Test
    void nonPdfResponseIsMappedToBadGateway() {
        server.enqueue(new MockResponse()
                .setResponseCode(200)
                .setHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .setBody("{\"ok\":true}"));

        assertThatThrownBy(() -> client.generateReportPdf(sampleRequest()))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> {
                    ResponseStatusException rse = (ResponseStatusException) ex;
                    assertThat(rse.getStatusCode().value()).isEqualTo(502);
                });
    }

    @Test
    void upstream422IsMapped() {
        server.enqueue(new MockResponse()
                .setResponseCode(422)
                .setHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .setBody("{\"message\":\"Type de fichier non accepté\"}"));

        assertThatThrownBy(() -> client.generateReportPdf(sampleRequest()))
                .isInstanceOf(ResponseStatusException.class)
                .satisfies(ex -> {
                    ResponseStatusException rse = (ResponseStatusException) ex;
                    assertThat(rse.getStatusCode().value()).isEqualTo(422);
                    assertThat(rse.getReason()).contains("Type de fichier");
                });
    }

    @Test
    void filenameIsSanitized() {
        String name = AcceptanceCriteriaReportService.buildReportFilename(
                "Client A/B",
                "Projet:Test",
                "ev?.png"
        );
        assertThat(name).startsWith("acceptance-criteria-");
        assertThat(name).endsWith(".pdf");
        assertThat(name).doesNotContain("/");
        assertThat(name).doesNotContain(":");
        assertThat(name).doesNotContain("?");
    }

    private static AiAcceptanceCriteriaClient.AcceptanceCriteriaReportRequest sampleRequest() {
        return new AiAcceptanceCriteriaClient.AcceptanceCriteriaReportRequest(
                "fake-image-bytes".getBytes(StandardCharsets.UTF_8),
                "proof.png",
                "image/png",
                "NDI",
                "Data Governance Domain",
                "DG",
                "Has the entity established a strategy?",
                "ndi_dg_01",
                1,
                "Level 1: Establishing",
                "Client Demo",
                "client@example.com",
                "Projet Alpha",
                2,
                "23/07/2026 17:00"
        );
    }
}
