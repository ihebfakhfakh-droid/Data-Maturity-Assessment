package org.example.pfebackend.config;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Ensures API errors are always returned as JSON, including when the client
 * requested {@code Accept: application/pdf} (recommendation report endpoint).
 */
@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ResponseStatusException.class)
    public ResponseEntity<Map<String, Object>> handleResponseStatusException(ResponseStatusException ex) {
        HttpStatus status = HttpStatus.resolve(ex.getStatusCode().value());
        if (status == null) {
            status = HttpStatus.INTERNAL_SERVER_ERROR;
        }
        String message = ex.getReason() != null && !ex.getReason().isBlank()
                ? ex.getReason()
                : status.getReasonPhrase();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("message", message);
        body.put("status", status.value());
        body.put("error", status.getReasonPhrase());

        return ResponseEntity.status(status)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body);
    }
}
