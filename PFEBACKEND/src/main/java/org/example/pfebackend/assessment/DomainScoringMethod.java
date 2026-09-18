package org.example.pfebackend.assessment;

/**
 * How the score of a domain (segment block) is derived from its question scores.
 */
public enum DomainScoringMethod {
    /** Minimum score among all questions in the domain (NDI / CMMI DMM style). */
    DOMAIN_MINIMUM,
    /** Arithmetic mean of question scores in the domain, rounded to nearest integer. */
    DOMAIN_AVERAGE
}
