package org.example.pfebackend.assessment;

import org.example.pfebackend.assessment.dto.QuestionnaireResponse;
import org.example.pfebackend.project.ClientProjectEntitlements;
import org.example.pfebackend.project.Framework;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

@Service
public class QuestionnaireService {

    private final QuestionnaireQuestionRepository questionRepository;
    private final LegacyQuestionnaireMetadataService metadataService;

    public QuestionnaireService(
            QuestionnaireQuestionRepository questionRepository,
            LegacyQuestionnaireMetadataService metadataService
    ) {
        this.questionRepository = questionRepository;
        this.metadataService = metadataService;
    }

    public QuestionnaireResponse getQuestionnaire() {
        return getQuestionnaire(new ClientProjectEntitlements(EnumSet.allOf(Framework.class), Set.of()));
    }

    public QuestionnaireResponse getQuestionnaire(Set<Framework> allowedBuiltinFrameworks) {
        return getQuestionnaire(new ClientProjectEntitlements(allowedBuiltinFrameworks, Set.of()));
    }

    public QuestionnaireResponse getQuestionnaire(ClientProjectEntitlements entitlements) {
        ClientProjectEntitlements e = entitlements == null || entitlements.isEmpty()
                ? new ClientProjectEntitlements(EnumSet.allOf(Framework.class), Set.of())
                : entitlements;
        List<QuestionnaireQuestion> questions = questionRepository.findByActiveTrueOrderBySegment_SortOrderAscSegment_CodeAscSortOrderAsc()
                .stream()
                .filter(q -> isQuestionAllowed(q, e))
                .sorted(QuestionnaireOrdering.questionComparator())
                .toList();

        Map<String, QuestionnaireResponse.SegmentDto> segments = new LinkedHashMap<>();
        Map<String, List<QuestionnaireResponse.QuestionDto>> segmentQuestions = new LinkedHashMap<>();

        for (QuestionnaireQuestion q : questions) {
            QuestionnaireSegment s = q.getSegment();
            QuestionnaireDomain d = q.getDomain();
            String parentCode = null;
            if (d != null && d.getParent() != null) {
                parentCode = d.getParent().getCode();
            } else if (s != null && s.getParent() != null) {
                parentCode = s.getParent().getCode();
            }
            String fwCode = frameworkCodeFor(q, e);
            String segmentCode = QuestionnaireOrdering.segmentCodeFor(q);
            segments.putIfAbsent(
                    segmentCode,
                    new QuestionnaireResponse.SegmentDto(
                            segmentCode,
                            metadataService.titleFor(q),
                            sortOrderFor(q),
                            parentCode,
                            fwCode,
                            domainWeightFor(q),
                            List.of()
                    )
            );
            segmentQuestions.computeIfAbsent(segmentCode, k -> new ArrayList<>())
                    .add(new QuestionnaireResponse.QuestionDto(q.getCode(), q.getText(), q.getSortOrder()));
        }

        List<QuestionnaireResponse.SegmentDto> segmentDtos = new ArrayList<>();
        for (var entry : segments.entrySet()) {
            String code = entry.getKey();
            QuestionnaireResponse.SegmentDto base = entry.getValue();
            segmentDtos.add(new QuestionnaireResponse.SegmentDto(
                    base.code(),
                    base.title(),
                    base.sortOrder(),
                    base.parentSegmentCode(),
                    base.maturityFrameworkCode(),
                    base.weight(),
                    segmentQuestions.getOrDefault(code, List.of())
            ));
        }

        return new QuestionnaireResponse(segmentDtos);
    }

    private static boolean isQuestionAllowed(QuestionnaireQuestion q, ClientProjectEntitlements e) {
        String questionCode = q.getCode();
        if (questionCode == null) {
            return false;
        }
        if (questionCode.startsWith("ndi_")) {
            return e.builtinFrameworks().contains(Framework.NDI);
        }
        if (questionCode.startsWith("cmmi_")) {
            return e.builtinFrameworks().contains(Framework.CMMI);
        }
        return !e.builtinFrameworks().isEmpty();
    }

    private static int sortOrderFor(QuestionnaireQuestion q) {
        QuestionnaireDomain domain = q.getDomain();
        if (domain != null && domain.getSortOrder() > 0) {
            return domain.getSortOrder();
        }
        return QuestionnaireOrdering.segmentSortOrder(q);
    }

    private static String frameworkCodeFor(QuestionnaireQuestion q, ClientProjectEntitlements e) {
        String questionCode = q.getCode();
        if (questionCode != null) {
            if (questionCode.startsWith("ndi_")) {
                return Framework.NDI.name();
            }
            if (questionCode.startsWith("cmmi_")) {
                return Framework.CMMI.name();
            }
        }
        if (e.builtinFrameworks().contains(Framework.NDI)) {
            return Framework.NDI.name();
        }
        if (e.builtinFrameworks().contains(Framework.CMMI)) {
            return Framework.CMMI.name();
        }
        return null;
    }

    private static Double domainWeightFor(QuestionnaireQuestion q) {
        QuestionnaireSegment segment = q.getSegment();
        if (segment != null && segment.getWeight() != null) {
            return segment.getWeight();
        }
        QuestionnaireDomain domain = q.getDomain();
        if (domain != null) {
            return domain.getWeight();
        }
        return segment != null && segment.getDomain() != null ? segment.getDomain().getWeight() : null;
    }
}
