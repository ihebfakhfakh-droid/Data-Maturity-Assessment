package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.GenerateReportRequestDto;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import org.springframework.web.server.ResponseStatusException;
import reactor.core.publisher.Mono;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component
public class AiRecommendationClient {

    private static final Logger log = LoggerFactory.getLogger(AiRecommendationClient.class);
    private static final String GENERATE_REPORT_PATH = "/api/recommendations/generate-report";
    private static final Pattern TARGET_SCORE_PATTERN = Pattern.compile("\"targetScore\"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)");

    private final WebClient webClient;
    private final JsonMapper jsonMapper;
    private final String baseUrl;
    private final Duration timeout;

    public AiRecommendationClient(
            @Qualifier("aiRecommendationWebClient") WebClient webClient,
            JsonMapper jsonMapper,
            @Value("${app.ai.recommendation.base-url:http://localhost:8002}") String baseUrl,
            @Value("${app.ai.recommendation.timeout-seconds:9000}") long timeoutSeconds
    ) {
        this.webClient = webClient;
        this.jsonMapper = jsonMapper;
        this.baseUrl = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.timeout = Duration.ofSeconds(Math.max(1, timeoutSeconds));
    }

    public byte[] generateReportPdf(GenerateReportRequestDto requestDto) {
        if (requestDto == null) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Le payload de recommandations IA est vide."
            );
        }
        if (requestDto.getTargetScore() == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Aucune cible de score n'a été définie pour cette évaluation soumise."
            );
        }
        if (requestDto.getCurrentScores() == null || requestDto.getCurrentScores().isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "Aucun score NDI exploitable n'a été trouvé pour générer les recommandations."
            );
        }

        // Diagnostic serialization only (logs). The HTTP request uses bodyValue(requestDto).
        try {
            String jsonPreview = jsonMapper.writeValueAsString(requestDto);
            Matcher targetMatcher = TARGET_SCORE_PATTERN.matcher(jsonPreview);
            if (!targetMatcher.find()) {
                throw new ResponseStatusException(
                        HttpStatus.INTERNAL_SERVER_ERROR,
                        "Le payload JSON ne contient pas le champ obligatoire targetScore."
                );
            }
            log.info(
                    "AI generate-report JSON ready | url={}{} | hasTargetScore=true | targetScore={} | currentScoresCount={} | jsonPreview={}",
                    baseUrl,
                    GENERATE_REPORT_PATH,
                    targetMatcher.group(1),
                    requestDto.getCurrentScores().size(),
                    sanitizeJsonForLog(jsonPreview)
            );
        } catch (JacksonException ex) {
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    "Impossible de sérialiser le payload de recommandations IA."
            );
        }

        String url = baseUrl + GENERATE_REPORT_PATH;
        try {
            byte[] body = webClient.post()
                    .uri(GENERATE_REPORT_PATH)
                    .contentType(MediaType.APPLICATION_JSON)
                    .accept(MediaType.APPLICATION_PDF, MediaType.APPLICATION_JSON)
                    .bodyValue(requestDto)
                    .retrieve()
                    .onStatus(HttpStatusCode::isError, response -> response.bodyToMono(String.class)
                            .defaultIfEmpty("")
                            .flatMap(errorBody -> {
                                log.error(
                                        "AI recommendation service error | url={} | status={} | body={}",
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
                                                : "Le service de recommandations IA a renvoyé une erreur ("
                                                + response.statusCode().value() + ")."
                                ));
                            }))
                    .bodyToMono(byte[].class)
                    .block(timeout);

            if (body == null || body.length == 0 || !startsWithPdf(body)) {
                log.warn("AI service returned invalid PDF for POST {} | bytes={}", url, body == null ? 0 : body.length);
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "Le service IA a renvoyé un PDF invalide ou vide."
                );
            }
            log.info("AI recommendation PDF received | bytes={}", body.length);
            return body;
        } catch (ResponseStatusException ex) {
            throw ex;
        } catch (WebClientResponseException ex) {
            String responseBody = ex.getResponseBodyAsString(StandardCharsets.UTF_8);
            log.error(
                    "AI recommendation service error | url={} | status={} | body={}",
                    url,
                    ex.getStatusCode().value(),
                    truncateForLog(responseBody)
            );
            String detail = extractErrorDetail(responseBody);
            HttpStatus status = mapUpstreamStatus(ex.getStatusCode().value());
            throw new ResponseStatusException(
                    status,
                    detail != null && !detail.isBlank()
                            ? detail
                            : "Le service de recommandations IA a renvoyé une erreur (" + ex.getStatusCode().value() + ")."
            );
        } catch (WebClientRequestException ex) {
            log.error("AI recommendation service unreachable | url={} | reason={}", url, ex.getMessage());
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Le service de recommandations IA est indisponible. Réessayez plus tard."
            );
        } catch (RuntimeException ex) {
            Throwable cause = ex.getCause();
            if (cause instanceof ResponseStatusException responseStatusException) {
                throw responseStatusException;
            }
            log.error("AI recommendation unexpected error | url={} | reason={}", url, ex.getMessage());
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY,
                    "Le service de recommandations IA a renvoyé une erreur."
            );
        }
    }

    /**
     * Keeps targetScore / framework / metadata visible; redacts detailed score maps.
     */
    static String sanitizeJsonForLog(String json) {
        if (json == null) {
            return "";
        }
        String sanitized = json
                .replaceAll("\"currentScores\"\\s*:\\s*\\{[^}]*}", "\"currentScores\":{/*redacted*/}")
                .replaceAll("\"domainWeights\"\\s*:\\s*\\{[^}]*}", "\"domainWeights\":{/*redacted*/}")
                .replaceAll("\"domainScores\"\\s*:\\s*\\{[^}]*}", "\"domainScores\":{/*redacted*/}")
                .replaceAll("\"weightedScores\"\\s*:\\s*\\{[^}]*}", "\"weightedScores\":{/*redacted*/}");
        return truncateForLog(sanitized);
    }

    private static HttpStatus mapUpstreamStatus(int upstreamStatus) {
        if (upstreamStatus == 400 || upstreamStatus == 422) {
            return HttpStatus.BAD_REQUEST;
        }
        if (upstreamStatus == 404) {
            return HttpStatus.BAD_GATEWAY;
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
        if (trimmed.contains("\"msg\"")) {
            int msgIdx = trimmed.indexOf("\"msg\"");
            int colon = trimmed.indexOf(':', msgIdx);
            if (colon > 0) {
                String after = trimmed.substring(colon + 1).trim();
                if (after.startsWith("\"")) {
                    int end = after.indexOf('"', 1);
                    if (end > 1) {
                        return after.substring(1, end);
                    }
                }
            }
        }
        if (trimmed.startsWith("{") && trimmed.contains("\"detail\"")) {
            int detailIdx = trimmed.indexOf("\"detail\"");
            int colon = trimmed.indexOf(':', detailIdx);
            if (colon > 0) {
                String after = trimmed.substring(colon + 1).trim();
                if (after.startsWith("\"")) {
                    int end = after.indexOf('"', 1);
                    if (end > 1) {
                        return after.substring(1, end);
                    }
                }
                if (after.startsWith("[")) {
                    return "Requête invalide envoyée au service de recommandations IA.";
                }
            }
        }
        if (trimmed.length() > 400) {
            return trimmed.substring(0, 400);
        }
        return trimmed;
    }
}
