package org.example.pfebackend.assessment.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Size;

import java.util.List;

public record SubmitAnswersRequest(
        @NotEmpty List<@Valid AnswerItem> answers,
        @Size(max = 1000) String versionComment,
        Boolean forceNewVersion
) {
    public record AnswerItem(
            @NotBlank String questionCode,
            @Min(0) @Max(5) Integer score,
            Boolean answered,
            @Size(max = 1000) String comment
    ) {
    }
}

