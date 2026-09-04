package org.example.pfebackend.assessment;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;

@Component
@ConditionalOnProperty(name = "app.questionnaire.seed.enabled", havingValue = "true")
public class QuestionnaireSeeder implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(QuestionnaireSeeder.class);

    private final QuestionnaireSegmentRepository segmentRepository;
    private final QuestionnaireQuestionRepository questionRepository;

    public QuestionnaireSeeder(
            QuestionnaireSegmentRepository segmentRepository,
            QuestionnaireQuestionRepository questionRepository
    ) {
        this.segmentRepository = segmentRepository;
        this.questionRepository = questionRepository;
    }

    @Override
    @Transactional
    public void run(String... args) {
        var existing = questionRepository.findAll();
        existing.forEach(q -> q.setActive(false));
        questionRepository.saveAll(existing);

        seedNdiFramework();
        seedCmmiFramework();
        long active = questionRepository.findAll().stream().filter(QuestionnaireQuestion::isActive).count();
        log.info("Questionnaire seed complete: {} active questions in database", active);
    }

    /** NDI framework — question codes: {@code ndi_dg_01}, {@code ndi_mcm_02}, … (segment + two-digit index). */
    private void seedNdiFramework() {
        seedNdiSub(1, "ndi_dg", "Data Governance (DG)",
                "Has the entity established & implemented a Data Management & Personal Data Protection (DM & PDP) Strategy and a DM & PDP Plan with Key Performance Indicators (KPIs) that can be continuously measured to ensure optimization?",
                "Has the entity established and implemented Data Management (DM) Policies, Standards and Guidelines across all Data Management (DM) Domains?",
                "Has the entity established and operationalized all roles required for the Data Management Organization as per the NDMO Controls & Specifications?",
                "Has the entity established and implemented practices for Change Management including awareness, communication, change control, and capability development?");

        seedNdiSub(2, "ndi_mcm", "Data Catalog & Metadata Management (MCM)",
                "Has the entity developed and implemented a plan to integrate and manage Metadata across the entity?",
                "Has the entity implemented a Metadata Management and Data Catalog tool / solution?",
                "Has the entity defined and implemented formal processes for effective Metadata Management, such as: prioritization, population, access management, and quality issue management, etc., supported & fostered by collaboration across the entity?");

        seedNdiSub(3, "ndi_dq", "Data Quality (DQ)",
                "Has the entity developed and implemented a Data Quality (DQ) plan focused on improving the quality of the entity's Data?",
                "Has the entity established / developed and implemented practices to manage and improve the quality of the entity's Data?",
                "Has the entity established and implemented practices to monitor and report the entity's Data Quality (DQ) status?",
                "Has the entity developed Data Quality (DQ) standards, provided definitions for its datasets, and published / uploaded the definitions on the National Data Catalog (NDC)?");

        seedNdiSub(4, "ndi_do", "Data Operations (DO)",
                "Has the entity developed and implemented a plan to manage and satisfy the needs of Data Operations, Data storage and Data retention?",
                "Does the entity have in place a defined methodology, processes and Standard Operating Procedures (SOPs) for database operations?",
                "Does the entity have in place, practices and processes for Business Continuity such as backup and disaster recovery (DR) and a defined Business Continuity Plan (BCP) for the data?");

        seedNdiSub(5, "ndi_dcm", "Document & Content Management (DCM)",
                "Has the entity developed a Document and Content Management (DCM) plan and a Digitization plan to manage the implementation of paperless management activities?",
                "Has the entity implemented policies and processes for Document and Content Management (DCM)?",
                "Has the entity implemented a tool to support Document and Content Management (DCM)?");

        seedNdiSub(6, "ndi_dam", "Data Architecture & Modelling (DAM)",
                "Has the entity developed and implemented a plan to improve its Data Architecture Capabilities?",
                "Has the entity developed and implemented practices for Data Architecture & Modelling (DAM)?");

        seedNdiSub(7, "ndi_dsi", "Data Sharing & Interoperability (DSI)",
                "Has the entity developed and implemented a Data Sharing and Integration (DSI) Plan?",
                "Has the entity defined and implemented Processes for Sharing Data?",
                "Has the entity defined and implemented a data integration architecture?",
                "Has the entity developed and implemented Data Sharing Controls?");

        seedNdiSub(8, "ndi_rmd", "Reference & Master Data Management (RMD)",
                "Has the entity developed and implemented a plan for RMD?",
                "Has the entity defined and implemented processes to manage RMD?",
                "Has the entity implemented a Data Hub for RMD?");

        seedNdiSub(9, "ndi_bia", "Business Intelligence & Analytics (BIA)",
                "Has the entity developed and implemented a plan for BIA?",
                "Has the entity identified BIA use cases?",
                "Has the entity defined and implemented BIA processes?",
                "Has the entity implemented tools for BIA?");

        seedNdiSub(10, "ndi_dvr", "Data Value Realization (DVR)",
                "Has the entity developed a plan for data value realization?",
                "Has the entity implemented data revenue practices?");

        seedNdiSub(11, "ndi_od", "Open Data (OD)",
                "Has the entity defined a plan for Open Data?",
                "Has the entity defined processes for Open Data?",
                "Has the entity implemented publishing processes?");

        seedNdiSub(12, "ndi_foi", "Freedom of Information (FOI)",
                "Has the entity defined a plan for FOI compliance?",
                "Has the entity implemented FOI processes?");

        seedNdiSub(13, "ndi_dc", "Data Classification (DC)",
                "Has the entity established a Data Classification plan?",
                "Has the entity implemented classification processes?",
                "Has the entity reviewed classified datasets?");

        seedNdiSub(14, "ndi_pdp", "Personal Data Protection (PDP)",
                "Has the entity performed a PDP assessment and plan?",
                "Has the entity implemented privacy policies and processes?");
    }

    private void seedNdiSub(int sortOrder, String segmentCode, String title, String... questionTexts) {
        List<CodedQuestion> list = new ArrayList<>(questionTexts.length);
        for (int i = 0; i < questionTexts.length; i++) {
            String code = segmentCode + "_" + String.format("%02d", i + 1);
            list.add(q(code, questionTexts[i]));
        }
        seedSegment(sortOrder, segmentCode, title, list);
    }

    /**
     * CMMI DMM — one segment per sub-domain; sort orders 100+ keep all CMMI blocks after NDI (1–14).
     * Question codes: {@code cmmi_domain_sub_nn} (e.g. {@code cmmi_1_1_01}).
     */
    private void seedCmmiFramework() {
        int o = 100;
        o = seedCmmiSub(o, "cmmi_1_1", "1.1 Data Management Strategy",
                "Do executive stakeholders visibly and actively support the data management strategy?",
                "Is the sequence plan aligned with business priorities and milestones?",
                "Is there sufficient understanding and agreement among executives and operational, IT and business stakeholders, to support a long-term sustainable data management program?",
                "How are projects aligned with the sequence plan that guides implementation of the data management program?",
                "Are staff capabilities and resources in place to architect, design, and lead the data management program?",
                "Is there a commitment to provide training to enable maturity of the data management program?");
        o = seedCmmiSub(o, "cmmi_1_2", "1.2 Communications",
                "How are policies, standards, and processes for data management promulgated?",
                "How does the organization keep stakeholders informed about data management plans and projects?",
                "How is bidirectional communication accomplished among business, IT, data management, and executive management about data management priorities, approaches, and deliverables?");
        o = seedCmmiSub(o, "cmmi_1_3", "1.3 Data Management Function",
                "Is the data management function defined such that it is clear to all relevant stakeholders?",
                "Is the data management function aligned to the data management strategy, as demonstrated by measures and metrics?",
                "What role do executives play in the design and oversight of the data management function?");
        o = seedCmmiSub(o, "cmmi_1_4", "1.4 Business Case",
                "How does the organization determine the level of investment required for the data management program?",
                "How does the organization decide whether to develop one umbrella business case or multiple, linked business cases?",
                "What are the success criteria for the business case?",
                "Who needs to be involved? Who needs to approve?",
                "Does the business case reflect the objectives and priorities of the data management strategy?",
                "Does the business case reflect the data management sequence plan?",
                "Has the Data Management Strategy sequence plan, supporting the business case(s), been reviewed and approved by data management sponsors?",
                "Does the business case methodology satisfy Program Funding criteria?");
        o = seedCmmiSub(o, "cmmi_1_5", "1.5 Program Funding",
                "Is there an approved set of investment criteria and priorities for data management?",
                "How does data governance provide oversight for data management funding?",
                "Was the program funding approach developed, evaluated, and approved by relevant stakeholders?",
                "Does the funding model reflect the organization’s business models, priorities, and financial decision processes?",
                "Are there defined and approved cost-benefit allocation methods, defined expense management practices, and business cases across the organization?",
                "Does the funding model consider all expenses of data management (e.g., projects, unique applications, urgent requirements)?");

        o = seedCmmiSub(o, "cmmi_2_1", "2.1 Governance Management",
                "Does data governance provide mechanisms to facilitate collaboration and decision making across lines of business and IT functions?",
                "Does the data governance structure clearly delineate defined responsibilities and accountability for data domains?",
                "How does the organization define roles and responsibilities and ensure that all relevant stakeholders are involved?",
                "Does data governance provide a mechanism for definition of priorities and resolution of competing priorities?",
                "Does data governance effectively provide a process for defining, escalating, and resolving issues?",
                "How does the executive sponsor(s) of data governance actively support the effort?",
                "How are executive sponsor(s) informed of data governance efforts?",
                "Has the organization instituted an effective compliance program across the data lifecycle?",
                "Does the organization have a process in place to review the governance structure and activities?",
                "Is there appropriate training in place for staff involved in data governance?",
                "What is the compliance process to carry out the decisions of the data governance body?");
        o = seedCmmiSub(o, "cmmi_2_2", "2.2 Business Glossary",
                "Is there a policy mandating use of and reference to the business glossary?",
                "How are organization-wide business terms, definitions, and corresponding metadata created, approved, verified, and managed?",
                "Is the business glossary promulgated and made accessible to all stakeholders?",
                "Are business terms referenced as the first step in the design of application data stores and repositories?",
                "Does the organization perform cross-referencing and mapping of business-specific terms (synonyms, business unit glossaries, logical attributes, physical data elements, etc.) to standardized business terms?",
                "How is the organization’s business glossary enhanced and maintained to reflect changes and additions?",
                "What role does data governance perform in creating, approving, managing, and updating business terms?",
                "Is a compliance process implemented to ensure that business units and projects are correctly applying business terms?",
                "Does the organization employ a defined process for stakeholders to provide feedback about business terms?");
        o = seedCmmiSub(o, "cmmi_2_3", "2.3 Metadata Management",
                "Is the metadata strategy defined and aligned with internal and selected external standards?",
                "How is the scope of metadata to be addressed for inclusion within the metadata repository defined?",
                "Are all relevant stakeholders involved in defining metadata categories and properties?",
                "What is the method for developing and evaluating standards and processes for metadata management?",
                "What is the method for maintaining or updating the metadata repository?",
                "Are metadata management processes defined and followed?",
                "Are roles and responsibilities clearly defined for the capture, updating, and use of metadata?");

        o = seedCmmiSub(o, "cmmi_3_1", "3.1 Data Quality Strategy",
                "Is data quality emphasized in all initiatives involving the data stores?",
                "How does the organization measure data quality program progress?",
                "What organizational unit is responsible for maintaining the data quality strategy?",
                "What organizational units are tasked with data quality initiatives? How are decisions made about standards, methods, and techniques?",
                "Are roles, responsibilities, and accountability clearly defined to foster improved quality of data assets?",
                "Is the data quality strategy widely distributed, communicated, and promulgated?",
                "Does the data quality strategy clearly describe objectives, policies, and processes?",
                "Is data quality integrated with the systems development lifecycle?",
                "How is data quality improvement integrated with business process improvement efforts?");
        o = seedCmmiSub(o, "cmmi_3_2", "3.2 Data Profiling",
                "Does the organization have a standard method for profiling data?",
                "Has the organization trained or acquired staff resources with expertise in data profiling tools and techniques?",
                "Does the organization apply statistical models to analyze data profiling reports?",
                "Do policies and processes specify the criteria for a data store to undergo profiling?",
                "Is data profiling scheduled based on defined events, considerations, or triggers?");
        o = seedCmmiSub(o, "cmmi_3_3", "3.3 Data Quality Assessment",
                "Are standard data quality assessment techniques and methods documented and followed?",
                "How are data quality assessments conducted, and are they scheduled or event-driven?",
                "Are standard data quality rules developed for core data attributes?",
                "Are data quality rules engines or assessment tools employed?",
                "Are the business, technical, and cost impacts of data quality issues analyzed and used as input to data quality improvement priorities?");
        o = seedCmmiSub(o, "cmmi_3_4", "3.4 Data Cleansing",
                "Does the organization have a reusable set of data cleansing processes (automated and manual) to resolve data quality issues?",
                "Is there a defined process for verifying corrections and assessing effectiveness?",
                "How does the organization cleanse duplicate records?",
                "Are corrections implemented at the source of capture?",
                "Are data cleansing processes followed through to analysis of root causes?",
                "Have lines of business established quality thresholds and tolerance limits?",
                "Has the organization deployed a consistent toolset(s) to support data cleansing?",
                "Does ROI incorporate data cleansing costs?",
                "Does the organization apply considerations of operational and reputational risk to determine what data cleansing activities to fund?",
                "How does the organization define, institutionalize, and monitor the data cleansing process?");

        o = seedCmmiSub(o, "cmmi_4_1", "4.1 Data Requirements Definition",
                "How are business and technical data requirements solicited, captured, evaluated, adjudicated, and verified with stakeholders?",
                "How are the data requirements mapped to the business objectives?",
                "How are approved data requirements validated against standard data definitions as well as logical and physical representations?");
        o = seedCmmiSub(o, "cmmi_4_2", "4.2 Data Lifecycle Management",
                "What activities, milestones, and products are defined for mapping business processes to the data created and maintained in support of these processes?",
                "Has the organization established clear roles and responsibilities for creating and maintaining a mapping of business processes to data?",
                "Are standard process modeling methods and tools employed to model and define business processes?",
                "Does governance have a role in the management and orchestration of business process data needs, mapping, and prioritization?");
        o = seedCmmiSub(o, "cmmi_4_3", "4.3 Provider Management",
                "How are data sourcing requirements captured, validated, and prioritized?",
                "Are requirements for data sourcing specific, unambiguous, driven by business requirements, and feasibly procurable?",
                "Is there a mechanism that ensures business approval of sourcing requirements?",
                "How are data attributes mapped to data sources and downstream applications?",
                "How is the data source selection process managed?",
                "How are service and content quality from data providers monitored?",
                "Do providers comply with applicable standards?",
                "Is there a repeatable process for managing issues that includes responsible points of contact?");

        o = seedCmmiSub(o, "cmmi_5_1", "5.1 Architectural Approach",
                "How does the organization approach architecting information assets?",
                "Is the architectural approach consistently followed, and are project-level decisions aligned with the approach?",
                "What is the rationalization method employed for synchronizing, consolidating, or eliminating duplicate data?",
                "How does the organization ensure the sustained progress of the transition plan to the target-state in response to deadlines, tight schedules, and other pressures?",
                "Does the organization have an approved data technology stack, and corresponding governance applied to modifications, additions, and sunsetting?",
                "Has the organization documented and approved the technical capabilities and requirements to satisfy operational business continuity?");
        o = seedCmmiSub(o, "cmmi_5_2", "5.2 Architectural Standards",
                "What are the categories of standards required for the organization’s target data architecture, and how are they scoped and defined?",
                "How does the organization determine business need and technology strategy for developing approved, standard data access and provisioning?",
                "How are data models approved, maintained, and governed?",
                "Has the organization defined architecturally aligned, standard data access methods and criteria for determining which methods to apply?",
                "How does the organization promulgate, audit, and enforce standards?");
        o = seedCmmiSub(o, "cmmi_5_3", "5.3 Data Management Platform",
                "How are authoritative data sources defined, selected, and integrated into particular portions of the platform?",
                "How does the organization address overlapping platforms and data duplication?",
                "Does the organization have a process for making “build versus buy” decisions?",
                "How does the organization address platform scalability, security, and resiliency in accordance with anticipated growth of data, users, and overall complexity?",
                "What forms of data, data exchange, and interfaces are supported by the platform?");
        o = seedCmmiSub(o, "cmmi_5_4", "5.4 Data Integration",
                "How are data consolidation needs assessed?",
                "How is future redundancy minimized?",
                "How does the organization consolidate data effectively where redundancy exists?",
                "Do data integration standards exist, and are they reviewed, monitored, approved, and enforced?",
                "Describe the compliance processes employed to enforce integration standards.",
                "How are data quality thresholds and targets applied to sources of data at ingestion and integration?",
                "Are the processes to identify missing data automated, and does tracking against defects or gaps support remediation?",
                "How is adequate staffing ensured for monitoring, managing, and sustaining data quality for ingestion and integration?");
        o = seedCmmiSub(o, "cmmi_5_5", "5.5 Historical Data, Archiving & Retention",
                "What are the architectural standards and conventions applied to the structure and management of historical data, and how are the corresponding business rules defined and governed?",
                "How is data retention for the required length of time assured?",
                "How is the integrity of archived data maintained?",
                "Is there a consistent approach for the retrieval and integration of archived historical data with current data?",
                "How is an audit trail for data changes monitored and managed?",
                "What considerations are applied to determine when archived data can be deleted?");

        o = seedCmmiSub(o, "cmmi_6_1", "6.1 Measurement and Analysis",
                "What measures and analyses exist to determine if data management goals and objectives are being met?",
                "How does the organization define, measure, analyze, and report on data management?",
                "How are measurements and analyses integrated into data management processes?");
        o = seedCmmiSub(o, "cmmi_6_2", "6.2 Process Management",
                "How are processes, methods, procedures, policies, and standards maintained?",
                "How is process performance measured?",
                "How does the organization measure process compliance?",
                "How does the organization ensure that improvements are identified, pursued, and implemented?",
                "How does the organization validate that proposed improvements enhance performance before they are deployed?");
        o = seedCmmiSub(o, "cmmi_6_3", "6.3 Process Quality Assurance",
                "Are process noncompliance issues raised to an appropriate level?",
                "Are quality issues analyzed for positive trending?",
                "Do all relevant stakeholders have visibility into the quality of the process and products?");
        o = seedCmmiSub(o, "cmmi_6_4", "6.4 Risk Management",
                "Does the organization know the amount of risk it is operating under?",
                "Has the organization identified and implemented risk mitigation and contingency plans?",
                "Does the organization periodically monitor risks and take appropriate update actions?");
        seedCmmiSub(o, "cmmi_6_5", "6.5 Configuration Management",
                "How is configuration management implemented and measured?",
                "How are data changes planned and controlled across the data lifecycle?");
    }

    private int seedCmmiSub(int sortOrder, String segmentCode, String title, String... questionTexts) {
        List<CodedQuestion> list = new ArrayList<>(questionTexts.length);
        for (int i = 0; i < questionTexts.length; i++) {
            String code = segmentCode + "_" + String.format("%02d", i + 1);
            list.add(q(code, questionTexts[i]));
        }
        seedSegment(sortOrder, segmentCode, "CMMI DMM · " + title, list);
        return sortOrder + 1;
    }

    private static CodedQuestion q(String code, String text) {
        return new CodedQuestion(code, text);
    }

    private record CodedQuestion(String code, String text) {}

    private void seedSegment(int order, String segmentCode, String title, List<CodedQuestion> questions) {
        QuestionnaireSegment segment = segmentRepository.findByCode(segmentCode)
                .orElseGet(() -> {
                    QuestionnaireSegment s = new QuestionnaireSegment();
                    s.setCode(segmentCode);
                    return s;
                });
        segment.setTitle(title);
        segment.setSortOrder(order);
        QuestionnaireSegment savedSegment = segmentRepository.save(segment);

        int i = 1;
        for (CodedQuestion cq : questions) {
            QuestionnaireQuestion q = questionRepository.findByCode(cq.code())
                    .orElseGet(() -> {
                        QuestionnaireQuestion qq = new QuestionnaireQuestion();
                        qq.setCode(cq.code());
                        return qq;
                    });
            q.setSegment(savedSegment);
            q.setText(cq.text());
            q.setSortOrder(i);
            q.setActive(true);
            questionRepository.save(q);
            i++;
        }
    }
}
