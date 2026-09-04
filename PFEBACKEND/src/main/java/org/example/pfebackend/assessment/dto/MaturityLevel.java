package org.example.pfebackend.assessment.dto;

public enum MaturityLevel {
    NOT_IMPLEMENTED(1, "Not implemented"),
    INITIAL(2, "Initial"),
    DEFINED(3, "Defined"),
    MANAGED(4, "Managed"),
    OPTIMIZED(5, "Optimized");

    private final int score;
    private final String labelFr;

    MaturityLevel(int score, String labelFr) {
        this.score = score;
        this.labelFr = labelFr;
    }

    public int score() {
        return score;
    }

    public String labelFr() {
        return labelFr;
    }

    public static MaturityLevel fromScore(int score) {
        return switch (score) {
            case 1 -> NOT_IMPLEMENTED;
            case 2 -> INITIAL;
            case 3 -> DEFINED;
            case 4 -> MANAGED;
            case 5 -> OPTIMIZED;
            default -> throw new IllegalArgumentException("Score must be between 1 and 5");
        };
    }
}

