--
-- PostgreSQL database dump
--

-- Dumped from database version 17.3
-- Dumped by pg_dump version 17.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: assessment_status_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.assessment_status_enum AS ENUM (
    'DRAFT',
    'SUBMITTED'
);


ALTER TYPE public.assessment_status_enum OWNER TO postgres;

--
-- Name: framework_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.framework_enum AS ENUM (
    'NDI',
    'CMMI'
);


ALTER TYPE public.framework_enum OWNER TO postgres;

--
-- Name: role_enum; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.role_enum AS ENUM (
    'CLIENT',
    'ADMIN',
    'MANAGER',
    'CONSULTANT'
);


ALTER TYPE public.role_enum OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.app_user (
    id bigint NOT NULL,
    full_name character varying(120) NOT NULL,
    email character varying(160) NOT NULL,
    password text NOT NULL,
    role character varying NOT NULL,
    managed_by_id bigint,
    assigned_consultant_id bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.app_user OWNER TO postgres;

--
-- Name: app_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.app_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.app_users_id_seq OWNER TO postgres;

--
-- Name: app_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.app_users_id_seq OWNED BY public.app_user.id;


--
-- Name: assessment; Type: TABLE; Schema: public; Owner: pfe_user
--

CREATE TABLE public.assessment (
    id bigint NOT NULL,
    client_id bigint NOT NULL,
    year integer NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    status character varying(20) DEFAULT 'DRAFT'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    submitted_at timestamp with time zone,
    project_id bigint,
    is_submitted boolean DEFAULT false NOT NULL
);


ALTER TABLE public.assessment OWNER TO pfe_user;

--
-- Name: assessment_answer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.assessment_answer (
    id bigint NOT NULL,
    assessment_id bigint NOT NULL,
    question_id bigint NOT NULL,
    score integer NOT NULL,
    answered_at timestamp with time zone DEFAULT now() NOT NULL,
    answered boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_score_range CHECK (((score >= 0) AND (score <= 5)))
);


ALTER TABLE public.assessment_answer OWNER TO postgres;

--
-- Name: assessment_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.assessment_answers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.assessment_answers_id_seq OWNER TO postgres;

--
-- Name: assessment_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.assessment_answers_id_seq OWNED BY public.assessment_answer.id;


--
-- Name: assessment_id_seq; Type: SEQUENCE; Schema: public; Owner: pfe_user
--

CREATE SEQUENCE public.assessment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.assessment_id_seq OWNER TO pfe_user;

--
-- Name: assessment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pfe_user
--

ALTER SEQUENCE public.assessment_id_seq OWNED BY public.assessment.id;


--
-- Name: domain; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.domain (
    id bigint NOT NULL,
    code character varying(80) NOT NULL,
    title character varying(240) NOT NULL,
    sort_order integer NOT NULL,
    active boolean DEFAULT true NOT NULL,
    framework_id bigint,
    parent_segment_id bigint,
    weight numeric(10,2)
);


ALTER TABLE public.domain OWNER TO postgres;

--
-- Name: evidence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.evidence (
    id bigint NOT NULL,
    uploaded_by_id bigint NOT NULL,
    storage_path text NOT NULL,
    original_file_name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    answer_id bigint,
    staff_rating character varying(20),
    rated_by_id bigint
);


ALTER TABLE public.evidence OWNER TO postgres;

--
-- Name: evidences_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.evidences_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.evidences_id_seq OWNER TO postgres;

--
-- Name: evidences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.evidences_id_seq OWNED BY public.evidence.id;


--
-- Name: framework; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.framework (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.framework OWNER TO postgres;

--
-- Name: framework_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.framework_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.framework_id_seq OWNER TO postgres;

--
-- Name: framework_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.framework_id_seq OWNED BY public.framework.id;


--
-- Name: project; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project (
    id bigint NOT NULL,
    client_id bigint NOT NULL,
    name character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.project OWNER TO postgres;

--
-- Name: project_framework; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_framework (
    project_id bigint NOT NULL,
    framework_id bigint NOT NULL,
    assigned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.project_framework OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.projects_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.projects_id_seq OWNER TO postgres;

--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.project.id;


--
-- Name: question; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.question (
    id bigint NOT NULL,
    domain_id bigint NOT NULL,
    code character varying(120) NOT NULL,
    text text NOT NULL,
    sort_order integer NOT NULL,
    active boolean DEFAULT true NOT NULL,
    sub_domain_id bigint,
    weight integer
);


ALTER TABLE public.question OWNER TO postgres;

--
-- Name: questionnaire_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questionnaire_questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionnaire_questions_id_seq OWNER TO postgres;

--
-- Name: questionnaire_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questionnaire_questions_id_seq OWNED BY public.question.id;


--
-- Name: questionnaire_segments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questionnaire_segments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questionnaire_segments_id_seq OWNER TO postgres;

--
-- Name: questionnaire_segments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questionnaire_segments_id_seq OWNED BY public.domain.id;


--
-- Name: sub_domain; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sub_domain (
    id bigint NOT NULL,
    domain_id bigint NOT NULL,
    name character varying(200) NOT NULL,
    sort_order integer,
    code character varying(80),
    maturity_framework_id bigint,
    parent_segment_id bigint
);


ALTER TABLE public.sub_domain OWNER TO postgres;

--
-- Name: sub_domain_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sub_domain_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sub_domain_id_seq OWNER TO postgres;

--
-- Name: sub_domain_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.sub_domain_id_seq OWNED BY public.sub_domain.id;


--
-- Name: app_user id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_user ALTER COLUMN id SET DEFAULT nextval('public.app_users_id_seq'::regclass);


--
-- Name: assessment id; Type: DEFAULT; Schema: public; Owner: pfe_user
--

ALTER TABLE ONLY public.assessment ALTER COLUMN id SET DEFAULT nextval('public.assessment_id_seq'::regclass);


--
-- Name: assessment_answer id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessment_answer ALTER COLUMN id SET DEFAULT nextval('public.assessment_answers_id_seq'::regclass);


--
-- Name: domain id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domain ALTER COLUMN id SET DEFAULT nextval('public.questionnaire_segments_id_seq'::regclass);


--
-- Name: evidence id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence ALTER COLUMN id SET DEFAULT nextval('public.evidences_id_seq'::regclass);


--
-- Name: framework id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.framework ALTER COLUMN id SET DEFAULT nextval('public.framework_id_seq'::regclass);


--
-- Name: project id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: question id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question ALTER COLUMN id SET DEFAULT nextval('public.questionnaire_questions_id_seq'::regclass);


--
-- Name: sub_domain id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sub_domain ALTER COLUMN id SET DEFAULT nextval('public.sub_domain_id_seq'::regclass);


--
-- Name: app_user app_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (id);


--
-- Name: assessment_answer assessment_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT assessment_answers_pkey PRIMARY KEY (id);


--
-- Name: assessment assessment_pkey; Type: CONSTRAINT; Schema: public; Owner: pfe_user
--

ALTER TABLE ONLY public.assessment
    ADD CONSTRAINT assessment_pkey PRIMARY KEY (id);


--
-- Name: assessment ck_assessment_is_submitted_matches_status; Type: CHECK CONSTRAINT; Schema: public; Owner: pfe_user
--

ALTER TABLE public.assessment
    ADD CONSTRAINT ck_assessment_is_submitted_matches_status CHECK ((is_submitted = ((status)::text = 'SUBMITTED'::text))) NOT VALID;


--
-- Name: evidence evidences_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidences_pkey PRIMARY KEY (id);


--
-- Name: framework framework_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.framework
    ADD CONSTRAINT framework_pkey PRIMARY KEY (id);


--
-- Name: project_framework project_framework_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_framework
    ADD CONSTRAINT project_framework_pkey PRIMARY KEY (project_id, framework_id);


--
-- Name: project projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: question questionnaire_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT questionnaire_questions_pkey PRIMARY KEY (id);


--
-- Name: domain questionnaire_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domain
    ADD CONSTRAINT questionnaire_segments_pkey PRIMARY KEY (id);


--
-- Name: sub_domain sub_domain_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sub_domain
    ADD CONSTRAINT sub_domain_pkey PRIMARY KEY (id);


--
-- Name: assessment_answer uq_answers_assessment_question; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT uq_answers_assessment_question UNIQUE (assessment_id, question_id);


--
-- Name: app_user uq_app_users_email; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT uq_app_users_email UNIQUE (email);


--
-- Name: assessment uq_assessment_client_year_version; Type: CONSTRAINT; Schema: public; Owner: pfe_user
--

ALTER TABLE ONLY public.assessment
    ADD CONSTRAINT uq_assessment_client_year_version UNIQUE (client_id, year, version);


--
-- Name: evidence uq_evidence_answer; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT uq_evidence_answer UNIQUE (answer_id);


--
-- Name: question uq_questions_code; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT uq_questions_code UNIQUE (code);


--
-- Name: domain uq_segments_code; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domain
    ADD CONSTRAINT uq_segments_code UNIQUE (code);


--
-- Name: idx_answers_assessment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_answers_assessment ON public.assessment_answer USING btree (assessment_id);


--
-- Name: idx_answers_question; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_answers_question ON public.assessment_answer USING btree (question_id);


--
-- Name: idx_app_users_assigned_consultant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_app_users_assigned_consultant ON public.app_user USING btree (assigned_consultant_id);


--
-- Name: idx_app_users_managed_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_app_users_managed_by ON public.app_user USING btree (managed_by_id);


--
-- Name: idx_app_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_app_users_role ON public.app_user USING btree (role);


--
-- Name: idx_projects_client_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_client_id ON public.project USING btree (client_id);


--
-- Name: idx_questions_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_questions_active ON public.question USING btree (active);


--
-- Name: idx_questions_segment_sort; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_questions_segment_sort ON public.question USING btree (domain_id, sort_order);


--
-- Name: idx_segments_sort; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_segments_sort ON public.domain USING btree (sort_order);


--
-- Name: assessment_answer fk_answers_question; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT fk_answers_question FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE RESTRICT;


--
-- Name: assessment_answer fk_assessment_answer_question; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT fk_assessment_answer_question FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE CASCADE;


--
-- Name: assessment fk_assessment_project; Type: FK CONSTRAINT; Schema: public; Owner: pfe_user
--

ALTER TABLE ONLY public.assessment
    ADD CONSTRAINT fk_assessment_project FOREIGN KEY (project_id) REFERENCES public.project(id) ON DELETE SET NULL NOT VALID;


--
-- Name: domain fk_domain_framework; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.domain
    ADD CONSTRAINT fk_domain_framework FOREIGN KEY (framework_id) REFERENCES public.framework(id) ON DELETE CASCADE;


--
-- Name: evidence fk_evidence_uploader; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidence_uploader FOREIGN KEY (uploaded_by_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: evidence fk_evidences_answer; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidences_answer FOREIGN KEY (answer_id) REFERENCES public.assessment_answer(id) ON DELETE CASCADE;


--
-- Name: evidence fk_evidences_rated_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidences_rated_by FOREIGN KEY (rated_by_id) REFERENCES public.app_user(id) ON DELETE SET NULL;


--
-- Name: evidence fk_evidences_uploaded_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidences_uploaded_by FOREIGN KEY (uploaded_by_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: project_framework fk_project_framework_framework; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_framework
    ADD CONSTRAINT fk_project_framework_framework FOREIGN KEY (framework_id) REFERENCES public.framework(id) ON DELETE CASCADE;


--
-- Name: project_framework fk_project_framework_project; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_framework
    ADD CONSTRAINT fk_project_framework_project FOREIGN KEY (project_id) REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: project fk_projects_client; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_projects_client FOREIGN KEY (client_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: question fk_question_domain; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT fk_question_domain FOREIGN KEY (domain_id) REFERENCES public.domain(id) ON DELETE CASCADE;


--
-- Name: question fk_question_sub_domain; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT fk_question_sub_domain FOREIGN KEY (sub_domain_id) REFERENCES public.sub_domain(id) ON DELETE SET NULL;


--
-- Name: question fk_questions_segment; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT fk_questions_segment FOREIGN KEY (domain_id) REFERENCES public.domain(id) ON DELETE RESTRICT;


--
-- Name: sub_domain fk_sub_domain_domain; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sub_domain
    ADD CONSTRAINT fk_sub_domain_domain FOREIGN KEY (domain_id) REFERENCES public.domain(id) ON DELETE CASCADE;


--
-- Name: app_user fk_users_assigned_consultant; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT fk_users_assigned_consultant FOREIGN KEY (assigned_consultant_id) REFERENCES public.app_user(id) ON DELETE SET NULL;


--
-- Name: app_user fk_users_managed_by; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT fk_users_managed_by FOREIGN KEY (managed_by_id) REFERENCES public.app_user(id) ON DELETE SET NULL;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO pfe_user;


--
-- Name: TABLE app_user; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.app_user TO pfe_user;


--
-- Name: SEQUENCE app_users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.app_users_id_seq TO pfe_user;


--
-- Name: TABLE assessment_answer; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.assessment_answer TO pfe_user;


--
-- Name: SEQUENCE assessment_answers_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.assessment_answers_id_seq TO pfe_user;


--
-- Name: TABLE domain; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.domain TO pfe_user;


--
-- Name: TABLE evidence; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.evidence TO pfe_user;


--
-- Name: SEQUENCE evidences_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.evidences_id_seq TO pfe_user;


--
-- Name: TABLE framework; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.framework TO pfe_user;


--
-- Name: SEQUENCE framework_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.framework_id_seq TO pfe_user;


--
-- Name: TABLE project; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.project TO pfe_user;


--
-- Name: TABLE project_framework; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.project_framework TO pfe_user;


--
-- Name: SEQUENCE projects_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.projects_id_seq TO pfe_user;


--
-- Name: TABLE question; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.question TO pfe_user;


--
-- Name: SEQUENCE questionnaire_questions_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.questionnaire_questions_id_seq TO pfe_user;


--
-- Name: SEQUENCE questionnaire_segments_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.questionnaire_segments_id_seq TO pfe_user;


--
-- Name: TABLE sub_domain; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.sub_domain TO pfe_user;


--
-- Name: SEQUENCE sub_domain_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.sub_domain_id_seq TO pfe_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO pfe_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO pfe_user;


--
-- PostgreSQL database dump complete
--

