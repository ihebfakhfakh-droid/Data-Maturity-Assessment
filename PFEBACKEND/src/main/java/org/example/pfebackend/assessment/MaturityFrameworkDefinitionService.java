package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.CreateFrameworkDomainRequest;
import org.example.pfebackend.assessment.dto.CreateFrameworkQuestionRequest;
import org.example.pfebackend.assessment.dto.CreateMaturityFrameworkRequest;
import org.example.pfebackend.user.AppUser;
import org.example.pfebackend.user.Role;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

@Service
public class MaturityFrameworkDefinitionService {

    private final MaturityFrameworkDefinitionRepository definitionRepository;
    private final QuestionnaireSegmentRepository segmentRepository;
    private final QuestionnaireQuestionRepository questionRepository;

    public MaturityFrameworkDefinitionService(
            MaturityFrameworkDefinitionRepository definitionRepository,
            QuestionnaireSegmentRepository segmentRepository,
            QuestionnaireQuestionRepository questionRepository
    ) {
        this.definitionRepository = definitionRepository;
        this.segmentRepository = segmentRepository;
        this.questionRepository = questionRepository;
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listDefinitions(AppUser actor) {
        requireAdmin(actor);
        return definitionRepository.findAll().stream()
                .sorted(java.util.Comparator.comparing(MaturityFrameworkDefinition::getName, String.CASE_INSENSITIVE_ORDER))
                .map(this::toSummary)
                .toList();
    }

    @Transactional
    public Map<String, Object> createDefinition(AppUser actor, CreateMaturityFrameworkRequest request) {
        requireAdmin(actor);
        String code = normalizeCode(request.code());
        if (code.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "code is required");
        }
        if ("ndi".equals(code) || "cmmi".equals(code)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Reserved framework code");
        }
        if (definitionRepository.existsByCodeIgnoreCase(code)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Framework code already exists");
        }

        MaturityFrameworkDefinition def = new MaturityFrameworkDefinition();
        def.setCode(code);
        def.setName(request.name().trim());
        def.setDomainScoringMethod(request.domainScoringMethod());
        def.setScoreScale(request.scoreScale());
        def = definitionRepository.save(def);

        Set<String> segmentCodes = new HashSet<>();
        Set<String> questionCodes = new HashSet<>();
        for (CreateFrameworkDomainRequest domain : request.domains()) {
            persistDomain(def, domain, null, segmentCodes, questionCodes);
        }

        return toSummary(def);
    }

    private void persistDomain(
            MaturityFrameworkDefinition def,
            CreateFrameworkDomainRequest dto,
            QuestionnaireSegment parent,
            Set<String> segmentCodes,
            Set<String> questionCodes
    ) {
        String segCode = normalizeCode(dto.code());
        if (segCode.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Domain code is required");
        }
        if (segCode.startsWith("ndi_") || segCode.startsWith("cmmi_")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Segment codes must not use reserved ndi_/cmmi_ prefixes");
        }
        if (!segmentCodes.add(segCode)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Duplicate segment code in request: " + segCode);
        }
        if (segmentRepository.existsByCodeIgnoreCase(segCode)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Segment code already exists: " + segCode);
        }

        QuestionnaireSegment segment = new QuestionnaireSegment();
        segment.setCode(segCode);
        segment.setTitle(dto.title().trim());
        segment.setSortOrder(dto.sortOrder());
        segment.setWeight(dto.weight());
        segment.setMaturityFramework(def);
        segment.setParent(parent);
        segment = segmentRepository.save(segment);

        List<CreateFrameworkQuestionRequest> qs = dto.questions() == null ? List.of() : dto.questions();
        for (CreateFrameworkQuestionRequest q : qs) {
            String qCode = normalizeCode(q.code());
            if (qCode.isBlank()) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Question code is required");
            }
            if (!questionCodes.add(qCode)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Duplicate question code in request: " + qCode);
            }
            if (questionRepository.existsByCodeIgnoreCase(qCode)) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Question code already exists: " + qCode);
            }
            QuestionnaireQuestion qq = new QuestionnaireQuestion();
            qq.setSegment(segment);
            qq.setCode(qCode);
            qq.setText(q.text().trim());
            qq.setSortOrder(q.sortOrder());
            qq.setActive(true);
            questionRepository.save(qq);
        }

        List<CreateFrameworkDomainRequest> subs = dto.subDomains() == null ? List.of() : dto.subDomains();
        for (CreateFrameworkDomainRequest sub : subs) {
            persistDomain(def, sub, segment, segmentCodes, questionCodes);
        }
    }

    private static void requireAdmin(AppUser actor) {
        if (actor.getRole() != Role.ADMIN) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only an admin can manage maturity frameworks");
        }
    }

    private static String normalizeCode(String raw) {
        return raw == null ? "" : raw.trim().toLowerCase(Locale.ROOT);
    }

    private Map<String, Object> toSummary(MaturityFrameworkDefinition d) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", d.getId());
        m.put("code", d.getCode());
        m.put("name", d.getName());
        m.put("domainScoringMethod", d.getDomainScoringMethod().name());
        m.put("scoreScale", d.getScoreScale().name());
        m.put("createdAt", d.getCreatedAt());
        return m;
    }
}
