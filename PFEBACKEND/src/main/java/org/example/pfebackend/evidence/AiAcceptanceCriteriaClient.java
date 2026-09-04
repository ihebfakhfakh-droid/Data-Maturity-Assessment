package org.example.pfebackend.evidence;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import org.springframework.web.server.ResponseStatusException;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.Duration;

@Component
public class AiAcceptanceCriteriaClient {

    private static final Logger log = LoggerFactory.getLogger(AiAcceptanceCriteriaClient.class);
    private static final String REPORT_PATH = "/api/acceptance-criteria/report";

    private final WebClient webClient;
    private final String baseUrl;
    private final Duration timeout;

    public AiAcceptanceCriteriaClient(
            @Qualifier("aiAcceptanceCriteriaWebClient") WebClient webClient,
            @Value("${app.ai.acceptance-criteria.base-url:http://localhost:8003}") String baseUrl,
            @Value("${app.ai.acceptance-criteria.timeout-seconds:9000}") long timeoutSeconds
    ) {
        this.webClient = webClient;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.timeout = Duration.ofSeconds(Math.max(1, timeoutSeconds));
    }

    public byte[] generateReportPdf(AcceptanceCriteriaReportRequest request) {
        if (request == null || request.fileBytes() == null || request.fileBytes().length == 0) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Le fichier d'évidence est vide.");
        }

        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        String filename = request.originalFileName() == null || request.originalFileName().isBlank()
                ? "evidence.bin"
                : request.originalFileName();
        MediaType partType = MediaType.APPLICATION_OCTET_STREAM;
        if (request.contentType() != null && !request.contentType().isBlank()) {
            try {
                partType = MediaType.parseMediaType(request.contentType());
            } catch (Exception ignored) {
                partType = MediaType.APPLICATION_OCTET_STREAM;
            }
        }
        builder.part("file", new ByteArrayResource(request.fileBytes()) {
            @Override
            public String getFilename() {
                return filename;
            }
        }).contentType(partType);

        addPart(builder, "original_filename", filename);
        addPart(builder, "content_type", request.contentType());
        addPart(builder, "framework", request.framework());
        addPart(builder, "domain_name", request.domainName());
        addPart(builder, "domain_code", request.domainCode());
        addPart(builder, "question_text", request.questionText());
        addPart(builder, "question_code", request.questionCode());
        if (request.selectedScore() != null) {
            addPart(builder, "selected_score", String.valueOf(request.selectedScore()));
        }
        addPart(builder, "maturity_level", request.maturityLevel());
        addPart(builder, "client_full_name", request.clientFullName());
        addPart(builder, "client_email", request.clientEmail());
        addPart(builder, "project_name", request.projectName());
        if (request.assessmentVersion() != null) {
            addPart(builder, "assessment_version", String.valueOf(request.assessmentVersion()));
        }
        addPart(builder, "generation_date", request.generationDate());
        addPart(builder, "evidence_file_name", filename);

        String url = baseUrl + REPORT_PATH;
        try {
            byte[] body = webClient.post()
                    .uri(REPORT_PATH)
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .accept(MediaType.APPLICATION_PDF, MediaType.APPLICATION_JSON)
                    .body(BodyInserters.fromMultipartData(builder.build()))
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, response -> response.bodyToMono(String.class)
                            .defaultIfEmpty("")
                            .flatMap(errorBody -> {
                                log.error(
                                        "Acceptance Criteria service error | url={} | status={} | body={}",
                                        url,
                                        response.statusCode().value(),
                                        truncateForLog(errorBody)
                                );
                                String detail = extractErrorDetail(errorBody);
                                HttpStatus status = mapUpstreamStatus(response.statusCode().value());
                                return Mono.error(new ResponseStatusException(
                                        status,
                                        detail != null && !detail.isBlank()
                                                ? detail
                                                : "Le service Acceptance Criteria a renvoyé une erreur ("
                                                + response.statusCode().value() + ")."
                                ));
                            }))
                    .bodyToMono(byte[].class)
                    .block(timeout);

            if (body == null || body.length == 0 || !startsWithPdf(body)) {
                log.warn("Acceptance Criteria service returned invalid PDF | url={} | bytes={}",
                        url, body == null ? 0 : body.length);
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "Le service Acceptance Criteria a renvoyé un PDF invalide ou vide."
                );
            }
            log.info("Acceptance Criteria PDF received | bytes={}", body.length);
            return body;
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (WebClientResponseException ex) {
            String responseBody = ex.getResponseBodyAsString(StandardCharsets.UTF_8);
            log.error(
                    "Acceptance Criteria service error | url={} | status={} | body={}",
                    url,
                    ex.getStatusCode().value(),
                    truncateForLog(responseBody)
            );
            throw new ResponseStatusException(
                    mapUpstreamStatus(ex.getStatusCode().value()),
                    extractErrorDetail(responseBody) != null
                            ? extractErrorDetail(responseBody)
                            : "Le service Acceptance Criteria a renvoyé une erreur (" + ex.getStatusCode().value() + ")."
            );
        } catch (WebClientRequestException ex) {
            log.error("Acceptance Criteria service unreachable | url={} | reason={}", url, ex.getMessage());
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Le microservice Acceptance Criteria est arrêté ou indisponible. Réessayez plus tard."
            );
        } catch (RuntimeException ex) {
            Throwable cause = ex.getCause();
            if (cause instanceof ResponseStatusException responseStatusException) {
                throw responseStatusException;
            }
            String message = ex.getMessage() == null ? "" : ex.getMessage().toLowerCase();
            if (message.contains("timeout") || message.contains("timed out")
                    || cause instanceof java.util.concurrent.TimeoutException) {
                throw new ResponseStatusException(
                        HttpStatus.GATEWAY_TIMEOUT,
                        "Timeout du modèle Acceptance Criteria. Réessayez plus tard."
                );
            }
            log.error("Acceptance Criteria unexpected error | url={} | reason={}", url, ex.getMessage());
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "Le service Acceptance Criteria a renvoyé une erreur."
            );
        }
    }

    private static void addPart(MultipartBodyBuilder builder, String name, String value) {
        if (value == null || value.isBlank()) {
            return;
        }
        builder.part(name, value);
    }

    private static HttpStatus mapUpstreamStatus(int upstreamStatus) {
        if (upstreamStatus == 400) {
            return HttpStatus.BAD_REQUEST;
        }
        if (upstreamStatus == 401) {
            return HttpStatus.UNAUTHORIZED;
        }
        if (upstreamStatus == 403) {
            return HttpStatus.FORBIDDEN;
        }
        if (upstreamStatus == 404) {
            return HttpStatus.NOT_FOUND;
        }
        if (upstreamStatus == 422) {
            return HttpStatus.UNPROCESSABLE_ENTITY;
        }
        if (upstreamStatus == 504) {
            return HttpStatus.GATEWAY_TIMEOUT;
        }
        if (upstreamStatus >= 500) {
            return HttpStatus.BAD_GATEWAY;
        }
        return HttpStatus.BAD_GATEWAY;
    }

    private static boolean startsWithPdf(byte[] body) {
        return body.length >= 4
                && body[0] == '%'
                && body[1] == 'P'
                && body[2] == 'D'
                && body[3] == 'F';
    }

    private static String truncateForLog(String body) {
        if (body == null || body.isBlank()) {
            return "";
        }
        String trimmed = body.trim();
        return trimmed.length() > 800 ? trimmed.substring(0, 800) + "…" : trimmed;
    }

    private static String extractErrorDetail(String body) {
        if (body == null || body.isBlank()) {
            return null;
        }
        String trimmed = body.trim();
        try {
            // Lightweight parse for {"message":"..."} / {"detail":"..."}
            for (String key : new String[]{"\"message\"", "\"detail\""}) {
                int idx = trimmed.indexOf(key);
                if (idx < 0) {
                    continue;
                }
                int colon = trimmed.indexOf(':', idx);
                if (colon < 0) {
                    continue;
                }
                String after = trimmed.substring(colon + 1).trim();
                if (after.startsWith("\"")) {
                    int end = after.indexOf('"', 1);
                    if (end > 1) {
                        return after.substring(1, end);
                    }
                }
            }
        } catch (Exception ignored) {
            // fall through
        }
        return trimmed.length() > 400 ? trimmed.substring(0, 400) : trimmed;
    }

    public record AcceptanceCriteriaReportRequest(
            byte[] fileBytes,
            String originalFileName,
            String contentType,
            String framework,
            String domainName,
            String domainCode,
            String questionText,
            String questionCode,
            Integer selectedScore,
            String maturityLevel,
            String clientFullName,
            String clientEmail,
            String projectName,
            Integer assessmentVersion,
            String generationDate
    ) {
    }
}
