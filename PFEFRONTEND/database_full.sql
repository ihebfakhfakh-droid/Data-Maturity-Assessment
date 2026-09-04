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
-- Name: assessment_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.assessment_status_enum AS ENUM (
    'DRAFT',
    'SUBMITTED'
);


--
-- Name: framework_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.framework_enum AS ENUM (
    'NDI',
    'CMMI'
);


--
-- Name: role_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.role_enum AS ENUM (
    'CLIENT',
    'ADMIN',
    'MANAGER',
    'CONSULTANT'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_user; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: app_users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.app_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: app_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.app_users_id_seq OWNED BY public.app_user.id;


--
-- Name: assessment; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: assessment_answer; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: assessment_answers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_answers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_answers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_answers_id_seq OWNED BY public.assessment_answer.id;


--
-- Name: assessment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assessment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assessment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assessment_id_seq OWNED BY public.assessment.id;


--
-- Name: domain; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: evidence; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: evidences_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evidences_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evidences_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evidences_id_seq OWNED BY public.evidence.id;


--
-- Name: framework; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.framework (
    id bigint NOT NULL,
    name character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: framework_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.framework_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: framework_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.framework_id_seq OWNED BY public.framework.id;


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    id bigint NOT NULL,
    client_id bigint NOT NULL,
    name character varying(200) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: project_framework; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_framework (
    project_id bigint NOT NULL,
    framework_id bigint NOT NULL,
    assigned_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: project_consultants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_consultants (
    project_id bigint NOT NULL,
    consultant_id bigint NOT NULL,
    assigned_at timestamp with time zone DEFAULT now()
);


--
-- Name: projects_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.projects_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: projects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.projects_id_seq OWNED BY public.project.id;


--
-- Name: question; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: questionnaire_questions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.questionnaire_questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: questionnaire_questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.questionnaire_questions_id_seq OWNED BY public.question.id;


--
-- Name: questionnaire_segments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.questionnaire_segments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: questionnaire_segments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.questionnaire_segments_id_seq OWNED BY public.domain.id;


--
-- Name: sub_domain; Type: TABLE; Schema: public; Owner: -
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


--
-- Name: sub_domain_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sub_domain_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sub_domain_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sub_domain_id_seq OWNED BY public.sub_domain.id;


--
-- Name: app_user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user ALTER COLUMN id SET DEFAULT nextval('public.app_users_id_seq'::regclass);


--
-- Name: assessment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment ALTER COLUMN id SET DEFAULT nextval('public.assessment_id_seq'::regclass);


--
-- Name: assessment_answer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_answer ALTER COLUMN id SET DEFAULT nextval('public.assessment_answers_id_seq'::regclass);


--
-- Name: domain id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain ALTER COLUMN id SET DEFAULT nextval('public.questionnaire_segments_id_seq'::regclass);


--
-- Name: evidence id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence ALTER COLUMN id SET DEFAULT nextval('public.evidences_id_seq'::regclass);


--
-- Name: framework id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.framework ALTER COLUMN id SET DEFAULT nextval('public.framework_id_seq'::regclass);


--
-- Name: project id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project ALTER COLUMN id SET DEFAULT nextval('public.projects_id_seq'::regclass);


--
-- Name: question id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question ALTER COLUMN id SET DEFAULT nextval('public.questionnaire_questions_id_seq'::regclass);


--
-- Name: sub_domain id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sub_domain ALTER COLUMN id SET DEFAULT nextval('public.sub_domain_id_seq'::regclass);


--
-- Data for Name: app_user; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.app_user VALUES (6, 'abdeslem', 'abdeslembenj@manager', '$2a$10$cucCAZebRri4jN69BhbqEu17nicM2V3QDnTbU0QCYElpMj42wvweO', 'MANAGER', NULL, NULL, '2026-05-07 18:51:53.589267+01');
INSERT INTO public.app_user VALUES (8, 'Super Admin', 'admin@pfe.local', '$2a$10$G6m8Cx7FDUbrnet2RWR1nOpfEkvG.R/SBwd.zfyxbnq7.89i9U0dq', 'ADMIN', NULL, NULL, '2026-05-11 10:49:14.05424+01');
INSERT INTO public.app_user VALUES (20, 'sami ben sami', 'samibensami@manager', '$2a$10$VR5WAKMnpfhG4YgqtuDSKe8pOUr3uM68/9oZ77eAItnpxUyCvWoRK', 'MANAGER', NULL, NULL, '2026-05-19 09:31:54.913769+01');
INSERT INTO public.app_user VALUES (24, 'slim karray', 'slimkarray@client', '$2a$10$LkOQFKaYWD7GShpZ465dwu3cLDXTC8CjEB5LuEEVUkqMKET1LjBLC', 'CLIENT', NULL, NULL, '2026-05-21 16:51:27.443376+01');
INSERT INTO public.app_user VALUES (26, 'mahdi amdouni', 'mahdiamdouni@manager', '$2a$10$YrGygen3boDvhnHuD/kvZO4LUoXuAOfm.wPFfmjdDen2oRe71LUHq', 'MANAGER', NULL, NULL, '2026-05-21 19:39:17.184011+01');
INSERT INTO public.app_user VALUES (27, 'mayssa benjmaa', 'mayssabenjmaa@consultant', '$2a$10$K4mOPDJddUw54OPIjongwOU7XZ4nCA8sdPWrxL0jUf97eufAsN6t.', 'CONSULTANT', 26, NULL, '2026-05-21 19:40:02.640488+01');
INSERT INTO public.app_user VALUES (25, 'mohsen benjmaa', 'mohsenbenjmaa@client', '$2a$10$3FWr97hIvqd4VLizHD2KZeM3iHKqFvy4QAHy3EXBTgGC43Q/jI.ji', 'CLIENT', NULL, 27, '2026-05-21 19:38:29.029603+01');
INSERT INTO public.app_user VALUES (29, 'ilyessouilem', 'ilyessouilem@manager', '$2a$10$zJZPnT9iztUZBnqV8qBlZuUQU7Ds3m4JJaneXaXZlftr2hrVDx05i', 'MANAGER', NULL, NULL, '2026-05-22 09:11:17.489476+01');
INSERT INTO public.app_user VALUES (31, 'ayman dahmen', 'aymandahmen@client', '$2a$10$fvF6axFAy/FSKiRenp2k8.bZR00PTSkJ/6hydcYI/aB3U/VMBNpfu', 'CLIENT', NULL, NULL, '2026-05-22 09:19:48.927071+01');
INSERT INTO public.app_user VALUES (28, 'iheb fakhfekh', 'ihebfakhfekh@client', '$2a$10$82xplymqCifgHodoC.I4nOXoRYdd9Iz2ug.0AoBz6VPZa/doy.sOK', 'CLIENT', NULL, NULL, '2026-05-22 09:10:40.29757+01');
INSERT INTO public.app_user VALUES (32, 'karim benjmaa', 'karimbj@client', '$2a$10$NlsIcN7McrTYwC7wVc.P2ufv6x.coktyK1cesDSZGlFjS1Ff2A.Hy', 'CLIENT', NULL, NULL, '2026-05-23 22:44:21.444373+01');
INSERT INTO public.app_user VALUES (34, 'mohamed benjmaa', 'mohamedbenjmaa@manager', '$2a$10$chMe/MiQFBF6I0oD0K/0YORdYr9de5hcmP4g.ACRAPuBeSF6iZUyO', 'MANAGER', NULL, NULL, '2026-05-25 23:34:01.394915+01');
INSERT INTO public.app_user VALUES (36, 'haitham frikha', 'haithamfrikha@client', '$2a$10$z5DRdyN6fBRisVsRkQ2lsOuHngTrluvhTebVeQkRaDPXAsxKEvwXq', 'CLIENT', NULL, NULL, '2026-05-25 23:35:14.64641+01');
INSERT INTO public.app_user VALUES (33, 'oussema lazez', 'oussemalazez@client', '$2a$10$GclbSqeLbzoQLTlssTlPh.e/ccz00aRYuHuUIo4u4nkegkJiOJ3dO', 'CLIENT', NULL, NULL, '2026-05-25 23:33:02.080149+01');
INSERT INTO public.app_user VALUES (38, 'omar trabelsi', 'omartrabelsi@manager', '$2a$10$3enj0smrvp5OnbudbtlnH.TFOqkurs9FTmxKLPLbAlHiEvYM/y.eu', 'MANAGER', NULL, NULL, '2026-05-26 11:08:43.593091+01');
INSERT INTO public.app_user VALUES (39, 'wassim ben yedder', 'wassimbenyedder@consultant', '$2a$10$yaIDnSRw6SHo03l604NAK.nrN4bcU6IWfjtGaWYX/x/zA0Qve4mGa', 'CONSULTANT', 38, NULL, '2026-05-26 11:09:24.344078+01');
INSERT INTO public.app_user VALUES (37, 'youssef benjmaa', 'youssefbenjmaa@client', '$2a$10$G4EAhYIFPFQKwA/k7U9tQOTJfoHRm9R2aIvROmNfrRt9smubqcYkq', 'CLIENT', NULL, 39, '2026-05-26 11:07:52.622515+01');
INSERT INTO public.app_user VALUES (40, 'yessine bouaziz', 'yessinebouaziz@client', '$2a$10$YDoBcuJrY4V6UOkM7AG8v..VppddLRZNHyZ9/5KDB9y1KmvQNmiA2', 'CLIENT', NULL, NULL, '2026-05-26 11:25:10.749595+01');


--
-- Data for Name: assessment; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.assessment VALUES (81, 33, 2026, 1, 'DRAFT', '2026-05-25 23:36:20.482178+01', NULL, 21, false);
INSERT INTO public.assessment VALUES (91, 40, 2026, 1, 'DRAFT', '2026-05-26 11:26:12.024364+01', NULL, 24, false);
INSERT INTO public.assessment VALUES (87, 37, 2026, 1, 'DRAFT', '2026-05-26 11:10:14.195409+01', NULL, 23, false);
INSERT INTO public.assessment VALUES (88, 37, 2026, 2, 'DRAFT', '2026-05-26 11:20:21.68033+01', NULL, 23, false);
INSERT INTO public.assessment VALUES (71, 24, 2026, 1, 'DRAFT', '2026-05-21 16:51:58.017465+01', NULL, 16, false);
INSERT INTO public.assessment VALUES (72, 25, 2026, 1, 'DRAFT', '2026-05-21 19:42:32.870648+01', NULL, 17, false);
INSERT INTO public.assessment VALUES (75, 28, 2026, 1, 'DRAFT', '2026-05-22 09:14:26.664339+01', NULL, 18, false);
INSERT INTO public.assessment VALUES (76, 31, 2026, 1, 'DRAFT', '2026-05-22 09:21:15.521246+01', NULL, 19, false);
INSERT INTO public.assessment VALUES (80, 32, 2026, 2, 'SUBMITTED', '2026-05-23 23:02:47.726783+01', '2026-05-23 23:07:46.102819+01', 20, true);
INSERT INTO public.assessment VALUES (78, 32, 2026, 1, 'DRAFT', '2026-05-23 22:44:52.956417+01', NULL, 20, false);
INSERT INTO public.assessment VALUES (84, 36, 2026, 1, 'DRAFT', '2026-05-25 23:57:04.823869+01', NULL, 22, false);
INSERT INTO public.assessment VALUES (83, 33, 2026, 2, 'SUBMITTED', '2026-05-25 23:55:13.426088+01', '2026-05-26 08:48:00.286262+01', 21, true);
INSERT INTO public.assessment VALUES (89, 37, 2026, 3, 'DRAFT', '2026-05-26 11:22:45.795674+01', NULL, 23, false);


--
-- Data for Name: assessment_answer; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.assessment_answer VALUES (1090, 81, 24, 2, '2026-05-25 23:52:04.232812+01', true);
INSERT INTO public.assessment_answer VALUES (1092, 81, 26, 4, '2026-05-25 23:52:08.71762+01', true);
INSERT INTO public.assessment_answer VALUES (1093, 81, 27, 4, '2026-05-25 23:52:14.487434+01', true);
INSERT INTO public.assessment_answer VALUES (1094, 81, 28, 2, '2026-05-25 23:52:16.443605+01', true);
INSERT INTO public.assessment_answer VALUES (1097, 81, 31, 3, '2026-05-25 23:52:25.485399+01', true);
INSERT INTO public.assessment_answer VALUES (1098, 81, 32, 2, '2026-05-25 23:52:27.846969+01', true);
INSERT INTO public.assessment_answer VALUES (1099, 81, 33, 4, '2026-05-25 23:52:36.083979+01', true);
INSERT INTO public.assessment_answer VALUES (1100, 81, 34, 1, '2026-05-25 23:52:39.291399+01', true);
INSERT INTO public.assessment_answer VALUES (1102, 81, 36, 2, '2026-05-25 23:52:46.486419+01', true);
INSERT INTO public.assessment_answer VALUES (1103, 81, 37, 3, '2026-05-25 23:52:48.789227+01', true);
INSERT INTO public.assessment_answer VALUES (1104, 81, 39, 1, '2026-05-25 23:52:53.837923+01', true);
INSERT INTO public.assessment_answer VALUES (972, 71, 6, 5, '2026-05-21 16:54:43.379467+01', true);
INSERT INTO public.assessment_answer VALUES (973, 71, 7, 5, '2026-05-21 16:54:48.924283+01', true);
INSERT INTO public.assessment_answer VALUES (967, 71, 1, 1, '2026-05-21 16:56:01.598886+01', true);
INSERT INTO public.assessment_answer VALUES (968, 71, 2, 5, '2026-05-21 18:59:08.81593+01', true);
INSERT INTO public.assessment_answer VALUES (1105, 81, 40, 3, '2026-05-25 23:52:57.141911+01', true);
INSERT INTO public.assessment_answer VALUES (1107, 81, 42, 5, '2026-05-25 23:53:08.883921+01', true);
INSERT INTO public.assessment_answer VALUES (817, 38, 14, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (969, 71, 3, 3, '2026-05-21 18:59:27.338202+01', true);
INSERT INTO public.assessment_answer VALUES (1070, 81, 3, 4, '2026-05-25 23:50:42.318341+01', true);
INSERT INTO public.assessment_answer VALUES (45, 21, 1, 3, '2026-05-11 16:43:45.67284+01', true);
INSERT INTO public.assessment_answer VALUES (52, 21, 7, 3, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (1072, 81, 5, 2, '2026-05-25 23:50:56.105761+01', true);
INSERT INTO public.assessment_answer VALUES (53, 21, 8, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (54, 21, 9, 3, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (55, 21, 10, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (56, 21, 11, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (1073, 81, 6, 4, '2026-05-25 23:50:58.177986+01', true);
INSERT INTO public.assessment_answer VALUES (1074, 81, 7, 5, '2026-05-25 23:51:00.350055+01', true);
INSERT INTO public.assessment_answer VALUES (57, 21, 12, 3, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (58, 21, 13, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (1075, 81, 9, 2, '2026-05-25 23:51:08.518803+01', true);
INSERT INTO public.assessment_answer VALUES (1077, 81, 11, 5, '2026-05-25 23:51:13.677799+01', true);
INSERT INTO public.assessment_answer VALUES (1078, 81, 14, 2, '2026-05-25 23:51:18.893191+01', true);
INSERT INTO public.assessment_answer VALUES (1079, 81, 13, 4, '2026-05-25 23:51:22.623642+01', true);
INSERT INTO public.assessment_answer VALUES (1080, 81, 12, 1, '2026-05-25 23:51:26.759429+01', true);
INSERT INTO public.assessment_answer VALUES (1082, 81, 15, 2, '2026-05-25 23:51:33.315009+01', true);
INSERT INTO public.assessment_answer VALUES (1083, 81, 17, 2, '2026-05-25 23:51:36.269501+01', true);
INSERT INTO public.assessment_answer VALUES (1084, 81, 18, 1, '2026-05-25 23:51:41.315613+01', true);
INSERT INTO public.assessment_answer VALUES (1085, 81, 19, 2, '2026-05-25 23:51:43.829336+01', true);
INSERT INTO public.assessment_answer VALUES (1087, 81, 21, 4, '2026-05-25 23:51:49.870008+01', true);
INSERT INTO public.assessment_answer VALUES (1088, 81, 22, 2, '2026-05-25 23:51:51.505513+01', true);
INSERT INTO public.assessment_answer VALUES (1089, 81, 23, 2, '2026-05-25 23:51:56.958972+01', true);
INSERT INTO public.assessment_answer VALUES (1108, 81, 41, 5, '2026-05-25 23:53:13.881496+01', true);
INSERT INTO public.assessment_answer VALUES (1109, 81, 8, 3, '2026-05-25 23:53:27.942669+01', true);
INSERT INTO public.assessment_answer VALUES (60, 21, 15, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (1068, 81, 1, 4, '2026-05-25 23:54:48.030613+01', true);
INSERT INTO public.assessment_answer VALUES (1069, 81, 2, 3, '2026-05-25 23:54:54.066356+01', true);
INSERT INTO public.assessment_answer VALUES (1071, 81, 4, 3, '2026-05-25 23:55:00.275371+01', true);
INSERT INTO public.assessment_answer VALUES (1112, 83, 3, 4, '2026-05-25 23:50:42.318341+01', true);
INSERT INTO public.assessment_answer VALUES (1114, 83, 5, 2, '2026-05-25 23:50:56.105761+01', true);
INSERT INTO public.assessment_answer VALUES (1115, 83, 6, 4, '2026-05-25 23:50:58.177986+01', true);
INSERT INTO public.assessment_answer VALUES (1116, 83, 7, 5, '2026-05-25 23:51:00.350055+01', true);
INSERT INTO public.assessment_answer VALUES (1120, 83, 14, 2, '2026-05-25 23:51:18.893191+01', true);
INSERT INTO public.assessment_answer VALUES (1121, 83, 13, 4, '2026-05-25 23:51:22.623642+01', true);
INSERT INTO public.assessment_answer VALUES (1122, 83, 12, 1, '2026-05-25 23:51:26.759429+01', true);
INSERT INTO public.assessment_answer VALUES (61, 21, 16, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (62, 21, 17, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (63, 21, 18, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (64, 21, 19, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (46, 21, 20, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (65, 21, 21, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (66, 21, 22, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (68, 21, 24, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (69, 21, 25, 2, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (70, 21, 26, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (72, 21, 28, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (73, 21, 29, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (74, 21, 30, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (76, 21, 32, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (77, 21, 33, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (78, 21, 34, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (984, 78, 1, 3, '2026-05-23 22:45:39.876888+01', true);
INSERT INTO public.assessment_answer VALUES (986, 78, 3, 4, '2026-05-23 22:45:49.327598+01', true);
INSERT INTO public.assessment_answer VALUES (989, 78, 6, 3, '2026-05-23 22:46:08.890176+01', true);
INSERT INTO public.assessment_answer VALUES (991, 78, 8, 1, '2026-05-23 22:46:18.849275+01', true);
INSERT INTO public.assessment_answer VALUES (994, 78, 11, 4, '2026-05-23 22:46:29.966977+01', true);
INSERT INTO public.assessment_answer VALUES (687, 35, 2, 4, '2026-05-21 01:13:43.392822+01', true);
INSERT INTO public.assessment_answer VALUES (688, 35, 38, 2, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (689, 35, 11, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (692, 35, 26, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (1119, 83, 11, 1, '2026-05-25 23:55:16.628063+01', true);
INSERT INTO public.assessment_answer VALUES (1117, 83, 9, 1, '2026-05-25 23:55:20.821283+01', true);
INSERT INTO public.assessment_answer VALUES (1110, 83, 1, 4, '2026-05-25 23:54:48.030613+01', true);
INSERT INTO public.assessment_answer VALUES (1111, 83, 2, 3, '2026-05-25 23:54:54.066356+01', true);
INSERT INTO public.assessment_answer VALUES (1113, 83, 4, 3, '2026-05-25 23:55:00.275371+01', true);
INSERT INTO public.assessment_answer VALUES (697, 35, 43, 3, '2026-05-21 00:28:35.989462+01', true);
INSERT INTO public.assessment_answer VALUES (698, 35, 30, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (699, 35, 40, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (970, 71, 4, 1, '2026-05-21 16:52:37.010063+01', true);
INSERT INTO public.assessment_answer VALUES (1086, 81, 20, 1, '2026-05-25 23:51:47.770671+01', true);
INSERT INTO public.assessment_answer VALUES (47, 21, 2, 3, '2026-05-11 16:43:45.67284+01', true);
INSERT INTO public.assessment_answer VALUES (48, 21, 3, 3, '2026-05-11 16:43:45.67284+01', true);
INSERT INTO public.assessment_answer VALUES (832, 38, 38, 2, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (833, 38, 11, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (834, 38, 1, 5, '2026-05-21 01:19:31.49963+01', true);
INSERT INTO public.assessment_answer VALUES (836, 38, 26, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (837, 38, 24, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (838, 38, 16, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (839, 38, 3, 5, '2026-05-21 01:19:41.002771+01', true);
INSERT INTO public.assessment_answer VALUES (840, 38, 39, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (841, 38, 43, 3, '2026-05-21 00:28:35.989462+01', true);
INSERT INTO public.assessment_answer VALUES (842, 38, 30, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (843, 38, 40, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (845, 38, 12, 3, '2026-05-11 19:41:28.094767+01', true);
INSERT INTO public.assessment_answer VALUES (846, 38, 36, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (847, 38, 15, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (848, 38, 9, 4, '2026-05-21 01:15:08.092027+01', true);
INSERT INTO public.assessment_answer VALUES (849, 38, 33, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (850, 38, 20, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (851, 38, 10, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (852, 38, 47, 4, '2026-05-21 00:32:30.929937+01', true);
INSERT INTO public.assessment_answer VALUES (853, 38, 37, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (854, 38, 17, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (855, 38, 21, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (856, 38, 22, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (815, 38, 4, 5, '2026-05-21 01:19:43.845933+01', true);
INSERT INTO public.assessment_answer VALUES (857, 41, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (858, 42, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (859, 42, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (860, 43, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (861, 43, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (871, 45, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (872, 46, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (873, 46, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (874, 46, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (875, 46, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (876, 46, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (877, 46, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (878, 47, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (879, 47, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (880, 47, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (881, 47, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (882, 47, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (883, 47, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (884, 47, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (885, 48, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (886, 48, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (887, 48, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (888, 48, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (889, 48, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (890, 48, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (891, 48, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (892, 48, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (893, 49, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (894, 49, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (895, 49, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (896, 49, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (897, 49, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (898, 49, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (899, 49, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (900, 49, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (901, 49, 9, 4, '2026-05-21 01:22:44.395188+01', true);
INSERT INTO public.assessment_answer VALUES (902, 50, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (903, 50, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (904, 50, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (905, 50, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (988, 78, 5, 1, '2026-05-23 22:46:06.253993+01', true);
INSERT INTO public.assessment_answer VALUES (993, 78, 10, 4, '2026-05-23 22:46:26.102692+01', true);
INSERT INTO public.assessment_answer VALUES (996, 78, 13, 3, '2026-05-23 22:46:41.77665+01', true);
INSERT INTO public.assessment_answer VALUES (999, 78, 16, 3, '2026-05-23 22:46:55.108213+01', true);
INSERT INTO public.assessment_answer VALUES (1001, 78, 18, 3, '2026-05-23 22:47:07.847287+01', true);
INSERT INTO public.assessment_answer VALUES (1004, 78, 21, 3, '2026-05-23 22:47:20.043681+01', true);
INSERT INTO public.assessment_answer VALUES (1006, 78, 23, 5, '2026-05-23 22:47:26.464729+01', true);
INSERT INTO public.assessment_answer VALUES (1009, 78, 26, 5, '2026-05-23 22:47:40.906886+01', true);
INSERT INTO public.assessment_answer VALUES (1011, 78, 28, 5, '2026-05-23 22:47:50.88944+01', true);
INSERT INTO public.assessment_answer VALUES (1016, 78, 33, 1, '2026-05-23 22:48:15.728398+01', true);
INSERT INTO public.assessment_answer VALUES (1019, 78, 36, 2, '2026-05-23 22:48:29.555421+01', true);
INSERT INTO public.assessment_answer VALUES (1021, 78, 38, 1, '2026-05-23 22:48:41.6469+01', true);
INSERT INTO public.assessment_answer VALUES (1024, 78, 41, 2, '2026-05-23 22:48:55.877065+01', true);
INSERT INTO public.assessment_answer VALUES (997, 78, 14, 1, '2026-05-23 22:46:46.417112+01', true);
INSERT INTO public.assessment_answer VALUES (1002, 78, 19, 1, '2026-05-23 22:47:10.876922+01', true);
INSERT INTO public.assessment_answer VALUES (1007, 78, 24, 1, '2026-05-23 22:47:34.242099+01', true);
INSERT INTO public.assessment_answer VALUES (1091, 81, 25, 2, '2026-05-25 23:52:06.455136+01', true);
INSERT INTO public.assessment_answer VALUES (1012, 78, 29, 4, '2026-05-23 22:47:53.427537+01', true);
INSERT INTO public.assessment_answer VALUES (1017, 78, 34, 5, '2026-05-23 22:48:18.463461+01', true);
INSERT INTO public.assessment_answer VALUES (1022, 78, 39, 3, '2026-05-23 22:48:44.2233+01', true);
INSERT INTO public.assessment_answer VALUES (1096, 81, 30, 4, '2026-05-25 23:52:21.253055+01', true);
INSERT INTO public.assessment_answer VALUES (1076, 81, 10, 3, '2026-05-25 23:55:07.400022+01', true);
INSERT INTO public.assessment_answer VALUES (1081, 81, 16, 0, '2026-05-25 23:51:30.39513+01', false);
INSERT INTO public.assessment_answer VALUES (798, 37, 36, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (799, 37, 15, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (800, 37, 9, 4, '2026-05-21 01:15:08.092027+01', true);
INSERT INTO public.assessment_answer VALUES (801, 37, 33, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (819, 38, 13, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (712, 35, 22, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (690, 35, 1, 5, '2026-05-21 01:19:31.49963+01', true);
INSERT INTO public.assessment_answer VALUES (713, 36, 28, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (714, 36, 34, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (715, 36, 25, 2, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (716, 36, 35, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (717, 36, 8, 4, '2026-05-21 01:15:05.56726+01', true);
INSERT INTO public.assessment_answer VALUES (718, 36, 19, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (719, 36, 4, 4, '2026-05-21 01:14:56.513287+01', true);
INSERT INTO public.assessment_answer VALUES (720, 36, 45, 1, '2026-05-21 00:28:55.332819+01', true);
INSERT INTO public.assessment_answer VALUES (723, 36, 13, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (724, 36, 7, 1, '2026-05-21 01:14:38.237064+01', true);
INSERT INTO public.assessment_answer VALUES (725, 36, 29, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (726, 36, 32, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (971, 71, 5, 5, '2026-05-21 16:54:39.453889+01', true);
INSERT INTO public.assessment_answer VALUES (802, 37, 20, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (803, 37, 10, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (804, 37, 47, 4, '2026-05-21 00:32:30.929937+01', true);
INSERT INTO public.assessment_answer VALUES (805, 37, 37, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (806, 37, 17, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (807, 37, 21, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (808, 37, 22, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (791, 37, 3, 5, '2026-05-21 01:19:41.002771+01', true);
INSERT INTO public.assessment_answer VALUES (812, 38, 35, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (813, 38, 8, 4, '2026-05-21 01:15:05.56726+01', true);
INSERT INTO public.assessment_answer VALUES (814, 38, 19, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (816, 38, 45, 1, '2026-05-21 00:28:55.332819+01', true);
INSERT INTO public.assessment_answer VALUES (976, 71, 8, 4, '2026-05-21 19:25:14.333287+01', true);
INSERT INTO public.assessment_answer VALUES (79, 21, 35, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (80, 21, 36, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (81, 21, 37, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (82, 21, 38, 2, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (83, 21, 39, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (84, 21, 40, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (85, 21, 41, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (86, 21, 42, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (977, 71, 9, 1, '2026-05-21 19:25:19.076681+01', true);
INSERT INTO public.assessment_answer VALUES (796, 37, 23, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (770, 37, 31, 0, '2026-05-11 16:43:45.70454+01', false);
INSERT INTO public.assessment_answer VALUES (748, 36, 23, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (1101, 81, 35, 2, '2026-05-25 23:52:41.01884+01', true);
INSERT INTO public.assessment_answer VALUES (1106, 81, 38, 3, '2026-05-25 23:53:03.336822+01', true);
INSERT INTO public.assessment_answer VALUES (1196, 87, 36, 3, '2026-05-26 11:15:04.621235+01', true);
INSERT INTO public.assessment_answer VALUES (1201, 87, 41, 3, '2026-05-26 11:15:20.804763+01', true);
INSERT INTO public.assessment_answer VALUES (695, 35, 3, 4, '2026-05-21 01:14:53.796554+01', true);
INSERT INTO public.assessment_answer VALUES (696, 35, 39, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (49, 21, 4, 2, '2026-05-11 16:43:45.67284+01', true);
INSERT INTO public.assessment_answer VALUES (50, 21, 5, 3, '2026-05-11 16:43:45.67284+01', true);
INSERT INTO public.assessment_answer VALUES (51, 21, 6, 3, '2026-05-11 16:43:45.67284+01', true);
INSERT INTO public.assessment_answer VALUES (701, 35, 12, 3, '2026-05-11 19:41:28.094767+01', true);
INSERT INTO public.assessment_answer VALUES (702, 35, 36, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (703, 35, 15, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (704, 35, 9, 4, '2026-05-21 01:15:08.092027+01', true);
INSERT INTO public.assessment_answer VALUES (705, 35, 33, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (706, 35, 20, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (707, 35, 10, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (708, 35, 47, 4, '2026-05-21 00:32:30.929937+01', true);
INSERT INTO public.assessment_answer VALUES (709, 35, 37, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (710, 35, 17, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (711, 35, 21, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (985, 78, 2, 2, '2026-05-23 22:45:45.994265+01', true);
INSERT INTO public.assessment_answer VALUES (990, 78, 7, 5, '2026-05-23 22:46:11.380572+01', true);
INSERT INTO public.assessment_answer VALUES (995, 78, 12, 2, '2026-05-23 22:46:38.354166+01', true);
INSERT INTO public.assessment_answer VALUES (685, 35, 41, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (686, 35, 44, 3, '2026-05-21 00:28:50.640323+01', true);
INSERT INTO public.assessment_answer VALUES (727, 36, 6, 1, '2026-05-21 01:14:35.379751+01', true);
INSERT INTO public.assessment_answer VALUES (1124, 83, 15, 2, '2026-05-25 23:51:33.315009+01', true);
INSERT INTO public.assessment_answer VALUES (1125, 83, 17, 2, '2026-05-25 23:51:36.269501+01', true);
INSERT INTO public.assessment_answer VALUES (1126, 83, 18, 1, '2026-05-25 23:51:41.315613+01', true);
INSERT INTO public.assessment_answer VALUES (1127, 83, 19, 2, '2026-05-25 23:51:43.829336+01', true);
INSERT INTO public.assessment_answer VALUES (1128, 83, 20, 1, '2026-05-25 23:51:47.770671+01', true);
INSERT INTO public.assessment_answer VALUES (1129, 83, 21, 4, '2026-05-25 23:51:49.870008+01', true);
INSERT INTO public.assessment_answer VALUES (1130, 83, 22, 2, '2026-05-25 23:51:51.505513+01', true);
INSERT INTO public.assessment_answer VALUES (1131, 83, 23, 2, '2026-05-25 23:51:56.958972+01', true);
INSERT INTO public.assessment_answer VALUES (1132, 83, 24, 2, '2026-05-25 23:52:04.232812+01', true);
INSERT INTO public.assessment_answer VALUES (1133, 83, 25, 2, '2026-05-25 23:52:06.455136+01', true);
INSERT INTO public.assessment_answer VALUES (1134, 83, 26, 4, '2026-05-25 23:52:08.71762+01', true);
INSERT INTO public.assessment_answer VALUES (1135, 83, 27, 4, '2026-05-25 23:52:14.487434+01', true);
INSERT INTO public.assessment_answer VALUES (1136, 83, 28, 2, '2026-05-25 23:52:16.443605+01', true);
INSERT INTO public.assessment_answer VALUES (1138, 83, 30, 4, '2026-05-25 23:52:21.253055+01', true);
INSERT INTO public.assessment_answer VALUES (1139, 83, 31, 3, '2026-05-25 23:52:25.485399+01', true);
INSERT INTO public.assessment_answer VALUES (1140, 83, 32, 2, '2026-05-25 23:52:27.846969+01', true);
INSERT INTO public.assessment_answer VALUES (1141, 83, 33, 4, '2026-05-25 23:52:36.083979+01', true);
INSERT INTO public.assessment_answer VALUES (1142, 83, 34, 1, '2026-05-25 23:52:39.291399+01', true);
INSERT INTO public.assessment_answer VALUES (1143, 83, 35, 2, '2026-05-25 23:52:41.01884+01', true);
INSERT INTO public.assessment_answer VALUES (1144, 83, 36, 2, '2026-05-25 23:52:46.486419+01', true);
INSERT INTO public.assessment_answer VALUES (1145, 83, 37, 3, '2026-05-25 23:52:48.789227+01', true);
INSERT INTO public.assessment_answer VALUES (1146, 83, 39, 1, '2026-05-25 23:52:53.837923+01', true);
INSERT INTO public.assessment_answer VALUES (1147, 83, 40, 3, '2026-05-25 23:52:57.141911+01', true);
INSERT INTO public.assessment_answer VALUES (1148, 83, 38, 3, '2026-05-25 23:53:03.336822+01', true);
INSERT INTO public.assessment_answer VALUES (1149, 83, 42, 5, '2026-05-25 23:53:08.883921+01', true);
INSERT INTO public.assessment_answer VALUES (1150, 83, 41, 5, '2026-05-25 23:53:13.881496+01', true);
INSERT INTO public.assessment_answer VALUES (1151, 83, 8, 1, '2026-05-25 23:55:24.284882+01', true);
INSERT INTO public.assessment_answer VALUES (1118, 83, 10, 1, '2026-05-25 23:55:13.485883+01', true);
INSERT INTO public.assessment_answer VALUES (1277, 89, 19, 4, '2026-05-26 11:11:58.011754+01', true);
INSERT INTO public.assessment_answer VALUES (1278, 89, 8, 2, '2026-05-26 11:11:02.194045+01', true);
INSERT INTO public.assessment_answer VALUES (1123, 83, 16, 3, '2026-05-26 08:47:48.832709+01', true);
INSERT INTO public.assessment_answer VALUES (1137, 83, 29, 3, '2026-05-26 08:47:58.062989+01', true);
INSERT INTO public.assessment_answer VALUES (1245, 89, 30, 2, '2026-05-26 11:12:51.503845+01', true);
INSERT INTO public.assessment_answer VALUES (1246, 89, 38, 2, '2026-05-26 11:15:13.571438+01', true);
INSERT INTO public.assessment_answer VALUES (1247, 89, 36, 3, '2026-05-26 11:15:04.621235+01', true);
INSERT INTO public.assessment_answer VALUES (1248, 89, 23, 2, '2026-05-26 11:12:18.249067+01', true);
INSERT INTO public.assessment_answer VALUES (1249, 89, 1, 4, '2026-05-26 11:20:21.751338+01', true);
INSERT INTO public.assessment_answer VALUES (1250, 89, 33, 3, '2026-05-26 11:14:50.514195+01', true);
INSERT INTO public.assessment_answer VALUES (1251, 89, 29, 5, '2026-05-26 11:12:47.674836+01', true);
INSERT INTO public.assessment_answer VALUES (1252, 89, 7, 4, '2026-05-26 11:10:51.387578+01', true);
INSERT INTO public.assessment_answer VALUES (1253, 89, 39, 2, '2026-05-26 11:15:11.195268+01', true);
INSERT INTO public.assessment_answer VALUES (1254, 89, 4, 2, '2026-05-26 11:20:33.637122+01', true);
INSERT INTO public.assessment_answer VALUES (1255, 89, 40, 2, '2026-05-26 11:15:16.687651+01', true);
INSERT INTO public.assessment_answer VALUES (1256, 89, 16, 3, '2026-05-26 11:11:41.95982+01', true);
INSERT INTO public.assessment_answer VALUES (1257, 89, 27, 3, '2026-05-26 11:12:42.064784+01', true);
INSERT INTO public.assessment_answer VALUES (728, 36, 42, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (745, 36, 43, 3, '2026-05-21 00:28:35.989462+01', true);
INSERT INTO public.assessment_answer VALUES (1258, 89, 13, 2, '2026-05-26 11:11:22.6576+01', true);
INSERT INTO public.assessment_answer VALUES (1259, 89, 9, 3, '2026-05-26 11:11:05.441406+01', true);
INSERT INTO public.assessment_answer VALUES (1260, 89, 37, 3, '2026-05-26 11:15:06.763909+01', true);
INSERT INTO public.assessment_answer VALUES (1261, 89, 34, 3, '2026-05-26 11:14:53.767916+01', true);
INSERT INTO public.assessment_answer VALUES (1262, 89, 18, 3, '2026-05-26 11:11:55.497973+01', true);
INSERT INTO public.assessment_answer VALUES (1263, 89, 22, 3, '2026-05-26 11:12:15.726268+01', true);
INSERT INTO public.assessment_answer VALUES (1264, 89, 20, 3, '2026-05-26 11:12:07.495487+01', true);
INSERT INTO public.assessment_answer VALUES (1265, 89, 24, 3, '2026-05-26 11:12:36.347176+01', true);
INSERT INTO public.assessment_answer VALUES (1266, 89, 11, 4, '2026-05-26 11:11:12.270473+01', true);
INSERT INTO public.assessment_answer VALUES (1267, 89, 35, 2, '2026-05-26 11:14:57.466482+01', true);
INSERT INTO public.assessment_answer VALUES (1268, 89, 32, 3, '2026-05-26 11:13:01.710895+01', true);
INSERT INTO public.assessment_answer VALUES (1269, 89, 3, 1, '2026-05-26 11:20:29.502202+01', true);
INSERT INTO public.assessment_answer VALUES (1270, 89, 12, 4, '2026-05-26 11:20:46.656262+01', true);
INSERT INTO public.assessment_answer VALUES (1272, 89, 31, 1, '2026-05-26 11:12:58.870803+01', true);
INSERT INTO public.assessment_answer VALUES (1273, 89, 25, 2, '2026-05-26 11:12:27.6017+01', true);
INSERT INTO public.assessment_answer VALUES (1274, 89, 14, 1, '2026-05-26 11:20:40.345677+01', true);
INSERT INTO public.assessment_answer VALUES (1275, 89, 15, 3, '2026-05-26 11:11:38.959389+01', true);
INSERT INTO public.assessment_answer VALUES (1276, 89, 2, 2, '2026-05-26 11:20:25.68416+01', true);
INSERT INTO public.assessment_answer VALUES (1279, 89, 42, 4, '2026-05-26 11:15:23.270022+01', true);
INSERT INTO public.assessment_answer VALUES (1280, 89, 28, 4, '2026-05-26 11:12:44.70195+01', true);
INSERT INTO public.assessment_answer VALUES (1281, 89, 6, 2, '2026-05-26 11:10:47.482765+01', true);
INSERT INTO public.assessment_answer VALUES (1282, 89, 21, 3, '2026-05-26 11:12:12.589123+01', true);
INSERT INTO public.assessment_answer VALUES (1283, 89, 41, 3, '2026-05-26 11:15:20.804763+01', true);
INSERT INTO public.assessment_answer VALUES (1284, 89, 10, 2, '2026-05-26 11:11:08.327129+01', true);
INSERT INTO public.assessment_answer VALUES (1285, 89, 5, 3, '2026-05-26 11:10:58.072143+01', true);
INSERT INTO public.assessment_answer VALUES (820, 38, 7, 1, '2026-05-21 01:14:38.237064+01', true);
INSERT INTO public.assessment_answer VALUES (821, 38, 29, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (822, 38, 32, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (823, 38, 6, 1, '2026-05-21 01:14:35.379751+01', true);
INSERT INTO public.assessment_answer VALUES (824, 38, 42, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (825, 38, 5, 1, '2026-05-21 01:14:32.287092+01', true);
INSERT INTO public.assessment_answer VALUES (826, 38, 48, 3, '2026-05-21 00:29:05.299612+01', true);
INSERT INTO public.assessment_answer VALUES (827, 38, 46, 1, '2026-05-21 00:29:00.901891+01', true);
INSERT INTO public.assessment_answer VALUES (828, 38, 18, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (829, 38, 41, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (830, 38, 44, 3, '2026-05-21 00:28:50.640323+01', true);
INSERT INTO public.assessment_answer VALUES (831, 38, 2, 5, '2026-05-21 01:19:35.061473+01', true);
INSERT INTO public.assessment_answer VALUES (1152, 84, 43, 1, '2026-05-25 23:57:12.083952+01', true);
INSERT INTO public.assessment_answer VALUES (1153, 84, 44, 5, '2026-05-25 23:57:14.240758+01', true);
INSERT INTO public.assessment_answer VALUES (1156, 84, 1, 2, '2026-05-25 23:59:01.036065+01', true);
INSERT INTO public.assessment_answer VALUES (1160, 84, 48, 0, '2026-05-26 00:01:18.162351+01', true);
INSERT INTO public.assessment_answer VALUES (1286, 89, 26, 3, '2026-05-26 11:12:29.880828+01', true);
INSERT INTO public.assessment_answer VALUES (1287, 89, 43, 3, '2026-05-26 11:22:45.853673+01', true);
INSERT INTO public.assessment_answer VALUES (1289, 89, 45, 3, '2026-05-26 11:22:51.988209+01', true);
INSERT INTO public.assessment_answer VALUES (1291, 89, 47, 3, '2026-05-26 11:22:57.999891+01', true);
INSERT INTO public.assessment_answer VALUES (1292, 89, 48, 4, '2026-05-26 11:23:02.762001+01', true);
INSERT INTO public.assessment_answer VALUES (1154, 84, 45, 3, '2026-05-25 23:57:16.694463+01', true);
INSERT INTO public.assessment_answer VALUES (1157, 84, 2, 2, '2026-05-25 23:59:05.942283+01', true);
INSERT INTO public.assessment_answer VALUES (1159, 84, 4, 2, '2026-05-25 23:59:13.423662+01', true);
INSERT INTO public.assessment_answer VALUES (693, 35, 24, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (694, 35, 16, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (746, 36, 30, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (747, 36, 40, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (749, 36, 12, 3, '2026-05-11 19:41:28.094767+01', true);
INSERT INTO public.assessment_answer VALUES (750, 36, 36, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (1288, 89, 44, 4, '2026-05-26 11:22:48.201095+01', true);
INSERT INTO public.assessment_answer VALUES (751, 36, 15, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (752, 36, 9, 4, '2026-05-21 01:15:08.092027+01', true);
INSERT INTO public.assessment_answer VALUES (753, 36, 33, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (754, 36, 20, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (1293, 91, 1, 3, '2026-05-26 11:26:18.650337+01', true);
INSERT INTO public.assessment_answer VALUES (755, 36, 10, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (756, 36, 47, 4, '2026-05-21 00:32:30.929937+01', true);
INSERT INTO public.assessment_answer VALUES (1294, 91, 2, 4, '2026-05-26 11:26:21.94757+01', true);
INSERT INTO public.assessment_answer VALUES (1295, 91, 43, 4, '2026-05-26 11:27:05.889421+01', true);
INSERT INTO public.assessment_answer VALUES (1296, 91, 44, 4, '2026-05-26 11:27:08.091291+01', true);
INSERT INTO public.assessment_answer VALUES (757, 36, 37, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (758, 36, 17, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (759, 36, 21, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (760, 36, 22, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (735, 36, 2, 5, '2026-05-21 01:19:35.061473+01', true);
INSERT INTO public.assessment_answer VALUES (761, 37, 28, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (762, 37, 34, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (763, 37, 25, 2, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (764, 37, 35, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (765, 37, 8, 4, '2026-05-21 01:15:05.56726+01', true);
INSERT INTO public.assessment_answer VALUES (766, 37, 19, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (767, 37, 4, 4, '2026-05-21 01:14:56.513287+01', true);
INSERT INTO public.assessment_answer VALUES (768, 37, 45, 1, '2026-05-21 00:28:55.332819+01', true);
INSERT INTO public.assessment_answer VALUES (987, 78, 4, 1, '2026-05-23 22:45:53.34447+01', true);
INSERT INTO public.assessment_answer VALUES (992, 78, 9, 5, '2026-05-23 22:46:21.910572+01', true);
INSERT INTO public.assessment_answer VALUES (771, 37, 13, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (772, 37, 7, 1, '2026-05-21 01:14:38.237064+01', true);
INSERT INTO public.assessment_answer VALUES (773, 37, 29, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (774, 37, 32, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (775, 37, 6, 1, '2026-05-21 01:14:35.379751+01', true);
INSERT INTO public.assessment_answer VALUES (776, 37, 42, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (777, 37, 5, 1, '2026-05-21 01:14:32.287092+01', true);
INSERT INTO public.assessment_answer VALUES (778, 37, 48, 3, '2026-05-21 00:29:05.299612+01', true);
INSERT INTO public.assessment_answer VALUES (779, 37, 46, 1, '2026-05-21 00:29:00.901891+01', true);
INSERT INTO public.assessment_answer VALUES (780, 37, 18, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (781, 37, 41, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (782, 37, 44, 3, '2026-05-21 00:28:50.640323+01', true);
INSERT INTO public.assessment_answer VALUES (783, 37, 2, 5, '2026-05-21 01:19:35.061473+01', true);
INSERT INTO public.assessment_answer VALUES (784, 37, 38, 2, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (785, 37, 11, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (786, 37, 1, 5, '2026-05-21 01:19:31.49963+01', true);
INSERT INTO public.assessment_answer VALUES (788, 37, 26, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (789, 37, 24, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (790, 37, 16, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (792, 37, 39, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (793, 37, 43, 3, '2026-05-21 00:28:35.989462+01', true);
INSERT INTO public.assessment_answer VALUES (794, 37, 30, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (795, 37, 40, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (797, 37, 12, 3, '2026-05-11 19:41:28.094767+01', true);
INSERT INTO public.assessment_answer VALUES (1155, 84, 46, 4, '2026-05-25 23:57:18.958607+01', true);
INSERT INTO public.assessment_answer VALUES (1158, 84, 3, 2, '2026-05-25 23:59:08.892621+01', true);
INSERT INTO public.assessment_answer VALUES (1290, 89, 46, 3, '2026-05-26 11:22:54.657483+01', true);
INSERT INTO public.assessment_answer VALUES (862, 43, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (863, 44, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (864, 44, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (865, 44, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (866, 44, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (867, 45, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (978, 71, 10, 5, '2026-05-21 19:25:24.236207+01', true);
INSERT INTO public.assessment_answer VALUES (974, 71, 43, 5, '2026-05-21 17:40:37.131771+01', true);
INSERT INTO public.assessment_answer VALUES (975, 71, 44, 4, '2026-05-21 17:40:40.010656+01', true);
INSERT INTO public.assessment_answer VALUES (979, 71, 11, 3, '2026-05-21 19:25:27.071215+01', true);
INSERT INTO public.assessment_answer VALUES (868, 45, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (869, 45, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (870, 45, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (71, 21, 27, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (665, 35, 28, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (666, 35, 34, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (667, 35, 25, 2, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (998, 78, 15, 1, '2026-05-23 22:46:52.574457+01', true);
INSERT INTO public.assessment_answer VALUES (1003, 78, 20, 1, '2026-05-23 22:47:17.779952+01', true);
INSERT INTO public.assessment_answer VALUES (1008, 78, 25, 3, '2026-05-23 22:47:37.160891+01', true);
INSERT INTO public.assessment_answer VALUES (668, 35, 35, 4, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (1013, 78, 30, 3, '2026-05-23 22:47:56.392282+01', true);
INSERT INTO public.assessment_answer VALUES (669, 35, 8, 4, '2026-05-21 01:15:05.56726+01', true);
INSERT INTO public.assessment_answer VALUES (670, 35, 19, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (671, 35, 4, 4, '2026-05-21 01:14:56.513287+01', true);
INSERT INTO public.assessment_answer VALUES (700, 35, 23, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (674, 35, 31, 0, '2026-05-11 16:43:45.70454+01', false);
INSERT INTO public.assessment_answer VALUES (1014, 78, 31, 0, '2026-05-23 22:48:06.170138+01', false);
INSERT INTO public.assessment_answer VALUES (673, 35, 14, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (672, 35, 45, 1, '2026-05-21 00:28:55.332819+01', true);
INSERT INTO public.assessment_answer VALUES (818, 38, 31, 0, '2026-05-11 16:43:45.70454+01', false);
INSERT INTO public.assessment_answer VALUES (722, 36, 31, 0, '2026-05-11 16:43:45.70454+01', false);
INSERT INTO public.assessment_answer VALUES (691, 35, 27, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (835, 38, 27, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (844, 38, 23, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (675, 35, 13, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (676, 35, 7, 1, '2026-05-21 01:14:38.237064+01', true);
INSERT INTO public.assessment_answer VALUES (677, 35, 29, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (721, 36, 14, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (67, 21, 23, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (980, 75, 1, 1, '2026-05-22 11:29:52.606965+01', true);
INSERT INTO public.assessment_answer VALUES (1018, 78, 35, 4, '2026-05-23 22:48:21.629282+01', true);
INSERT INTO public.assessment_answer VALUES (1023, 78, 40, 4, '2026-05-23 22:48:47.285944+01', true);
INSERT INTO public.assessment_answer VALUES (678, 35, 32, 3, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (679, 35, 6, 1, '2026-05-21 01:14:35.379751+01', true);
INSERT INTO public.assessment_answer VALUES (680, 35, 42, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (681, 35, 5, 1, '2026-05-21 01:14:32.287092+01', true);
INSERT INTO public.assessment_answer VALUES (981, 75, 2, 2, '2026-05-22 09:14:43.347735+01', true);
INSERT INTO public.assessment_answer VALUES (982, 75, 3, 3, '2026-05-22 09:14:46.889444+01', true);
INSERT INTO public.assessment_answer VALUES (59, 21, 14, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (682, 35, 48, 3, '2026-05-21 00:29:05.299612+01', true);
INSERT INTO public.assessment_answer VALUES (683, 35, 46, 1, '2026-05-21 00:29:00.901891+01', true);
INSERT INTO public.assessment_answer VALUES (684, 35, 18, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (1058, 80, 10, 4, '2026-05-23 22:46:26.102692+01', true);
INSERT INTO public.assessment_answer VALUES (1059, 80, 22, 4, '2026-05-23 22:47:23.109493+01', true);
INSERT INTO public.assessment_answer VALUES (1060, 80, 27, 2, '2026-05-23 22:47:48.649364+01', true);
INSERT INTO public.assessment_answer VALUES (1061, 80, 30, 3, '2026-05-23 22:47:56.392282+01', true);
INSERT INTO public.assessment_answer VALUES (1062, 80, 23, 5, '2026-05-23 22:47:26.464729+01', true);
INSERT INTO public.assessment_answer VALUES (1064, 80, 4, 1, '2026-05-23 22:45:53.34447+01', true);
INSERT INTO public.assessment_answer VALUES (1065, 80, 17, 1, '2026-05-23 22:46:59.295674+01', true);
INSERT INTO public.assessment_answer VALUES (769, 37, 14, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (1000, 78, 17, 1, '2026-05-23 22:46:59.295674+01', true);
INSERT INTO public.assessment_answer VALUES (1005, 78, 22, 4, '2026-05-23 22:47:23.109493+01', true);
INSERT INTO public.assessment_answer VALUES (1010, 78, 27, 2, '2026-05-23 22:47:48.649364+01', true);
INSERT INTO public.assessment_answer VALUES (1015, 78, 32, 4, '2026-05-23 22:48:08.991388+01', true);
INSERT INTO public.assessment_answer VALUES (1020, 78, 37, 2, '2026-05-23 22:48:35.129954+01', true);
INSERT INTO public.assessment_answer VALUES (1025, 78, 42, 4, '2026-05-23 22:48:58.428775+01', true);
INSERT INTO public.assessment_answer VALUES (983, 75, 4, 4, '2026-05-22 09:14:50.35568+01', true);
INSERT INTO public.assessment_answer VALUES (1271, 89, 17, 3, '2026-05-28 12:06:02.597003+01', true);
INSERT INTO public.assessment_answer VALUES (787, 37, 27, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (729, 36, 5, 1, '2026-05-21 01:14:32.287092+01', true);
INSERT INTO public.assessment_answer VALUES (730, 36, 48, 3, '2026-05-21 00:29:05.299612+01', true);
INSERT INTO public.assessment_answer VALUES (731, 36, 46, 1, '2026-05-21 00:29:00.901891+01', true);
INSERT INTO public.assessment_answer VALUES (732, 36, 18, 3, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (733, 36, 41, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (734, 36, 44, 3, '2026-05-21 00:28:50.640323+01', true);
INSERT INTO public.assessment_answer VALUES (736, 36, 38, 2, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (737, 36, 11, 2, '2026-05-11 16:43:45.680382+01', true);
INSERT INTO public.assessment_answer VALUES (738, 36, 1, 5, '2026-05-21 01:19:31.49963+01', true);
INSERT INTO public.assessment_answer VALUES (740, 36, 26, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (741, 36, 24, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (742, 36, 16, 1, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (743, 36, 3, 4, '2026-05-21 01:14:53.796554+01', true);
INSERT INTO public.assessment_answer VALUES (744, 36, 39, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (1066, 80, 20, 1, '2026-05-23 22:47:17.779952+01', true);
INSERT INTO public.assessment_answer VALUES (1067, 80, 36, 2, '2026-05-23 22:48:29.555421+01', true);
INSERT INTO public.assessment_answer VALUES (1063, 80, 31, 2, '2026-05-23 23:02:47.817321+01', true);
INSERT INTO public.assessment_answer VALUES (809, 38, 28, 1, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (810, 38, 34, 5, '2026-05-11 16:43:45.70454+01', true);
INSERT INTO public.assessment_answer VALUES (811, 38, 25, 2, '2026-05-11 16:43:45.688907+01', true);
INSERT INTO public.assessment_answer VALUES (1026, 80, 39, 3, '2026-05-23 22:48:44.2233+01', true);
INSERT INTO public.assessment_answer VALUES (1027, 80, 2, 2, '2026-05-23 22:45:45.994265+01', true);
INSERT INTO public.assessment_answer VALUES (1028, 80, 15, 1, '2026-05-23 22:46:52.574457+01', true);
INSERT INTO public.assessment_answer VALUES (1029, 80, 6, 3, '2026-05-23 22:46:08.890176+01', true);
INSERT INTO public.assessment_answer VALUES (1030, 80, 13, 3, '2026-05-23 22:46:41.77665+01', true);
INSERT INTO public.assessment_answer VALUES (1031, 80, 12, 2, '2026-05-23 22:46:38.354166+01', true);
INSERT INTO public.assessment_answer VALUES (1032, 80, 33, 1, '2026-05-23 22:48:15.728398+01', true);
INSERT INTO public.assessment_answer VALUES (1033, 80, 38, 1, '2026-05-23 22:48:41.6469+01', true);
INSERT INTO public.assessment_answer VALUES (1034, 80, 28, 5, '2026-05-23 22:47:50.88944+01', true);
INSERT INTO public.assessment_answer VALUES (1035, 80, 3, 4, '2026-05-23 22:45:49.327598+01', true);
INSERT INTO public.assessment_answer VALUES (1036, 80, 11, 4, '2026-05-23 22:46:29.966977+01', true);
INSERT INTO public.assessment_answer VALUES (1037, 80, 29, 4, '2026-05-23 22:47:53.427537+01', true);
INSERT INTO public.assessment_answer VALUES (1038, 80, 9, 5, '2026-05-23 22:46:21.910572+01', true);
INSERT INTO public.assessment_answer VALUES (1039, 80, 24, 1, '2026-05-23 22:47:34.242099+01', true);
INSERT INTO public.assessment_answer VALUES (1040, 80, 37, 2, '2026-05-23 22:48:35.129954+01', true);
INSERT INTO public.assessment_answer VALUES (1041, 80, 42, 4, '2026-05-23 22:48:58.428775+01', true);
INSERT INTO public.assessment_answer VALUES (1042, 80, 8, 1, '2026-05-23 22:46:18.849275+01', true);
INSERT INTO public.assessment_answer VALUES (1043, 80, 7, 5, '2026-05-23 22:46:11.380572+01', true);
INSERT INTO public.assessment_answer VALUES (1044, 80, 21, 3, '2026-05-23 22:47:20.043681+01', true);
INSERT INTO public.assessment_answer VALUES (1045, 80, 25, 3, '2026-05-23 22:47:37.160891+01', true);
INSERT INTO public.assessment_answer VALUES (1046, 80, 32, 4, '2026-05-23 22:48:08.991388+01', true);
INSERT INTO public.assessment_answer VALUES (1047, 80, 14, 1, '2026-05-23 22:46:46.417112+01', true);
INSERT INTO public.assessment_answer VALUES (1049, 80, 16, 3, '2026-05-23 22:46:55.108213+01', true);
INSERT INTO public.assessment_answer VALUES (1050, 80, 26, 5, '2026-05-23 22:47:40.906886+01', true);
INSERT INTO public.assessment_answer VALUES (1051, 80, 18, 3, '2026-05-23 22:47:07.847287+01', true);
INSERT INTO public.assessment_answer VALUES (1052, 80, 40, 4, '2026-05-23 22:48:47.285944+01', true);
INSERT INTO public.assessment_answer VALUES (1053, 80, 41, 2, '2026-05-23 22:48:55.877065+01', true);
INSERT INTO public.assessment_answer VALUES (1054, 80, 34, 5, '2026-05-23 22:48:18.463461+01', true);
INSERT INTO public.assessment_answer VALUES (1055, 80, 35, 4, '2026-05-23 22:48:21.629282+01', true);
INSERT INTO public.assessment_answer VALUES (1056, 80, 5, 1, '2026-05-23 22:46:06.253993+01', true);
INSERT INTO public.assessment_answer VALUES (1057, 80, 19, 1, '2026-05-23 22:47:10.876922+01', true);
INSERT INTO public.assessment_answer VALUES (1048, 80, 1, 3, '2026-05-25 15:59:00.380867+01', true);
INSERT INTO public.assessment_answer VALUES (1166, 87, 7, 4, '2026-05-26 11:10:51.387578+01', true);
INSERT INTO public.assessment_answer VALUES (1168, 87, 8, 2, '2026-05-26 11:11:02.194045+01', true);
INSERT INTO public.assessment_answer VALUES (1169, 87, 9, 3, '2026-05-26 11:11:05.441406+01', true);
INSERT INTO public.assessment_answer VALUES (1171, 87, 11, 4, '2026-05-26 11:11:12.270473+01', true);
INSERT INTO public.assessment_answer VALUES (1173, 87, 13, 2, '2026-05-26 11:11:22.6576+01', true);
INSERT INTO public.assessment_answer VALUES (1174, 87, 14, 3, '2026-05-26 11:11:25.258163+01', true);
INSERT INTO public.assessment_answer VALUES (1176, 87, 16, 3, '2026-05-26 11:11:41.95982+01', true);
INSERT INTO public.assessment_answer VALUES (1178, 87, 18, 3, '2026-05-26 11:11:55.497973+01', true);
INSERT INTO public.assessment_answer VALUES (1179, 87, 19, 4, '2026-05-26 11:11:58.011754+01', true);
INSERT INTO public.assessment_answer VALUES (1181, 87, 21, 3, '2026-05-26 11:12:12.589123+01', true);
INSERT INTO public.assessment_answer VALUES (1183, 87, 23, 2, '2026-05-26 11:12:18.249067+01', true);
INSERT INTO public.assessment_answer VALUES (1184, 87, 25, 2, '2026-05-26 11:12:27.6017+01', true);
INSERT INTO public.assessment_answer VALUES (1186, 87, 24, 3, '2026-05-26 11:12:36.347176+01', true);
INSERT INTO public.assessment_answer VALUES (1188, 87, 28, 4, '2026-05-26 11:12:44.70195+01', true);
INSERT INTO public.assessment_answer VALUES (1189, 87, 29, 5, '2026-05-26 11:12:47.674836+01', true);
INSERT INTO public.assessment_answer VALUES (1161, 87, 1, 3, '2026-05-26 11:16:50.802288+01', true);
INSERT INTO public.assessment_answer VALUES (1163, 87, 3, 3, '2026-05-26 11:17:09.382058+01', true);
INSERT INTO public.assessment_answer VALUES (1164, 87, 4, 3, '2026-05-26 11:17:18.189483+01', true);
INSERT INTO public.assessment_answer VALUES (1095, 81, 29, 0, '2026-05-25 23:52:18.743656+01', false);
INSERT INTO public.assessment_answer VALUES (44, 3, 44, 0, '2026-05-11 16:22:42.524285+01', false);
INSERT INTO public.assessment_answer VALUES (75, 21, 31, 0, '2026-05-11 16:43:45.70454+01', false);
INSERT INTO public.assessment_answer VALUES (906, 50, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (907, 50, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (908, 50, 9, 4, '2026-05-21 01:22:44.395188+01', true);
INSERT INTO public.assessment_answer VALUES (909, 50, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (910, 50, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (922, 51, 11, 4, '2026-05-21 01:22:51.093258+01', true);
INSERT INTO public.assessment_answer VALUES (934, 54, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (935, 54, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (937, 54, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (938, 54, 11, 4, '2026-05-21 01:22:51.093258+01', true);
INSERT INTO public.assessment_answer VALUES (939, 54, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (940, 54, 10, 4, '2026-05-21 01:22:48.697547+01', true);
INSERT INTO public.assessment_answer VALUES (941, 54, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (942, 54, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (943, 54, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (1167, 87, 5, 3, '2026-05-26 11:10:58.072143+01', true);
INSERT INTO public.assessment_answer VALUES (1172, 87, 12, 3, '2026-05-26 11:11:19.288679+01', true);
INSERT INTO public.assessment_answer VALUES (1182, 87, 22, 3, '2026-05-26 11:12:15.726268+01', true);
INSERT INTO public.assessment_answer VALUES (1187, 87, 27, 3, '2026-05-26 11:12:42.064784+01', true);
INSERT INTO public.assessment_answer VALUES (1191, 87, 31, 1, '2026-05-26 11:12:58.870803+01', true);
INSERT INTO public.assessment_answer VALUES (1192, 87, 32, 3, '2026-05-26 11:13:01.710895+01', true);
INSERT INTO public.assessment_answer VALUES (944, 54, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (936, 54, 9, 1, '2026-05-21 01:25:16.730592+01', true);
INSERT INTO public.assessment_answer VALUES (1162, 87, 2, 3, '2026-05-26 11:17:00.255686+01', true);
INSERT INTO public.assessment_answer VALUES (739, 36, 27, 0, '2026-05-11 16:43:45.688907+01', false);
INSERT INTO public.assessment_answer VALUES (1177, 87, 17, 0, '2026-05-26 11:11:47.785372+01', false);
INSERT INTO public.assessment_answer VALUES (1165, 87, 6, 2, '2026-05-26 11:10:47.482765+01', true);
INSERT INTO public.assessment_answer VALUES (911, 50, 10, 4, '2026-05-21 01:22:48.697547+01', true);
INSERT INTO public.assessment_answer VALUES (945, 55, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (946, 55, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (947, 55, 9, 1, '2026-05-21 01:25:16.730592+01', true);
INSERT INTO public.assessment_answer VALUES (948, 55, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (949, 55, 11, 4, '2026-05-21 01:22:51.093258+01', true);
INSERT INTO public.assessment_answer VALUES (950, 55, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (952, 55, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (953, 55, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (954, 55, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (955, 55, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (951, 55, 10, 1, '2026-05-21 01:25:19.758327+01', true);
INSERT INTO public.assessment_answer VALUES (1170, 87, 10, 2, '2026-05-26 11:11:08.327129+01', true);
INSERT INTO public.assessment_answer VALUES (1175, 87, 15, 3, '2026-05-26 11:11:38.959389+01', true);
INSERT INTO public.assessment_answer VALUES (1180, 87, 20, 3, '2026-05-26 11:12:07.495487+01', true);
INSERT INTO public.assessment_answer VALUES (1185, 87, 26, 3, '2026-05-26 11:12:29.880828+01', true);
INSERT INTO public.assessment_answer VALUES (1190, 87, 30, 2, '2026-05-26 11:12:51.503845+01', true);
INSERT INTO public.assessment_answer VALUES (1193, 87, 33, 3, '2026-05-26 11:14:50.514195+01', true);
INSERT INTO public.assessment_answer VALUES (1194, 87, 34, 3, '2026-05-26 11:14:53.767916+01', true);
INSERT INTO public.assessment_answer VALUES (1195, 87, 35, 2, '2026-05-26 11:14:57.466482+01', true);
INSERT INTO public.assessment_answer VALUES (1197, 87, 37, 3, '2026-05-26 11:15:06.763909+01', true);
INSERT INTO public.assessment_answer VALUES (1198, 87, 39, 2, '2026-05-26 11:15:11.195268+01', true);
INSERT INTO public.assessment_answer VALUES (1199, 87, 38, 2, '2026-05-26 11:15:13.571438+01', true);
INSERT INTO public.assessment_answer VALUES (1200, 87, 40, 2, '2026-05-26 11:15:16.687651+01', true);
INSERT INTO public.assessment_answer VALUES (1202, 87, 42, 4, '2026-05-26 11:15:23.270022+01', true);
INSERT INTO public.assessment_answer VALUES (912, 51, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (913, 51, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (914, 51, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (915, 51, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (916, 51, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (917, 51, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (918, 51, 9, 4, '2026-05-21 01:22:44.395188+01', true);
INSERT INTO public.assessment_answer VALUES (919, 51, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (920, 51, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (921, 51, 10, 4, '2026-05-21 01:22:48.697547+01', true);
INSERT INTO public.assessment_answer VALUES (956, 56, 3, 3, '2026-05-21 01:22:15.646967+01', true);
INSERT INTO public.assessment_answer VALUES (957, 56, 7, 2, '2026-05-21 01:22:33.145325+01', true);
INSERT INTO public.assessment_answer VALUES (958, 56, 9, 1, '2026-05-21 01:25:16.730592+01', true);
INSERT INTO public.assessment_answer VALUES (959, 56, 2, 5, '2026-05-21 01:22:13.124024+01', true);
INSERT INTO public.assessment_answer VALUES (961, 56, 4, 3, '2026-05-21 01:22:18.410674+01', true);
INSERT INTO public.assessment_answer VALUES (962, 56, 10, 1, '2026-05-21 01:25:19.758327+01', true);
INSERT INTO public.assessment_answer VALUES (963, 56, 8, 4, '2026-05-21 01:22:41.70982+01', true);
INSERT INTO public.assessment_answer VALUES (964, 56, 6, 2, '2026-05-21 01:22:30.11964+01', true);
INSERT INTO public.assessment_answer VALUES (965, 56, 5, 2, '2026-05-21 01:22:26.834037+01', true);
INSERT INTO public.assessment_answer VALUES (966, 56, 1, 2, '2026-05-21 01:22:09.749248+01', true);
INSERT INTO public.assessment_answer VALUES (960, 56, 11, 1, '2026-05-21 01:25:23.056727+01', true);
INSERT INTO public.assessment_answer VALUES (1207, 88, 6, 2, '2026-05-26 11:10:47.482765+01', true);
INSERT INTO public.assessment_answer VALUES (1208, 88, 7, 4, '2026-05-26 11:10:51.387578+01', true);
INSERT INTO public.assessment_answer VALUES (1209, 88, 5, 3, '2026-05-26 11:10:58.072143+01', true);
INSERT INTO public.assessment_answer VALUES (1210, 88, 8, 2, '2026-05-26 11:11:02.194045+01', true);
INSERT INTO public.assessment_answer VALUES (1211, 88, 9, 3, '2026-05-26 11:11:05.441406+01', true);
INSERT INTO public.assessment_answer VALUES (1212, 88, 10, 2, '2026-05-26 11:11:08.327129+01', true);
INSERT INTO public.assessment_answer VALUES (1213, 88, 11, 4, '2026-05-26 11:11:12.270473+01', true);
INSERT INTO public.assessment_answer VALUES (1215, 88, 13, 2, '2026-05-26 11:11:22.6576+01', true);
INSERT INTO public.assessment_answer VALUES (1217, 88, 15, 3, '2026-05-26 11:11:38.959389+01', true);
INSERT INTO public.assessment_answer VALUES (1218, 88, 16, 3, '2026-05-26 11:11:41.95982+01', true);
INSERT INTO public.assessment_answer VALUES (1220, 88, 18, 3, '2026-05-26 11:11:55.497973+01', true);
INSERT INTO public.assessment_answer VALUES (1221, 88, 19, 4, '2026-05-26 11:11:58.011754+01', true);
INSERT INTO public.assessment_answer VALUES (1222, 88, 20, 3, '2026-05-26 11:12:07.495487+01', true);
INSERT INTO public.assessment_answer VALUES (1223, 88, 21, 3, '2026-05-26 11:12:12.589123+01', true);
INSERT INTO public.assessment_answer VALUES (1224, 88, 22, 3, '2026-05-26 11:12:15.726268+01', true);
INSERT INTO public.assessment_answer VALUES (1225, 88, 23, 2, '2026-05-26 11:12:18.249067+01', true);
INSERT INTO public.assessment_answer VALUES (1226, 88, 25, 2, '2026-05-26 11:12:27.6017+01', true);
INSERT INTO public.assessment_answer VALUES (1227, 88, 26, 3, '2026-05-26 11:12:29.880828+01', true);
INSERT INTO public.assessment_answer VALUES (1228, 88, 24, 3, '2026-05-26 11:12:36.347176+01', true);
INSERT INTO public.assessment_answer VALUES (1229, 88, 27, 3, '2026-05-26 11:12:42.064784+01', true);
INSERT INTO public.assessment_answer VALUES (1230, 88, 28, 4, '2026-05-26 11:12:44.70195+01', true);
INSERT INTO public.assessment_answer VALUES (1231, 88, 29, 5, '2026-05-26 11:12:47.674836+01', true);
INSERT INTO public.assessment_answer VALUES (1232, 88, 30, 2, '2026-05-26 11:12:51.503845+01', true);
INSERT INTO public.assessment_answer VALUES (1233, 88, 31, 1, '2026-05-26 11:12:58.870803+01', true);
INSERT INTO public.assessment_answer VALUES (1234, 88, 32, 3, '2026-05-26 11:13:01.710895+01', true);
INSERT INTO public.assessment_answer VALUES (1235, 88, 33, 3, '2026-05-26 11:14:50.514195+01', true);
INSERT INTO public.assessment_answer VALUES (1236, 88, 34, 3, '2026-05-26 11:14:53.767916+01', true);
INSERT INTO public.assessment_answer VALUES (1237, 88, 35, 2, '2026-05-26 11:14:57.466482+01', true);
INSERT INTO public.assessment_answer VALUES (1238, 88, 36, 3, '2026-05-26 11:15:04.621235+01', true);
INSERT INTO public.assessment_answer VALUES (1239, 88, 37, 3, '2026-05-26 11:15:06.763909+01', true);
INSERT INTO public.assessment_answer VALUES (1240, 88, 39, 2, '2026-05-26 11:15:11.195268+01', true);
INSERT INTO public.assessment_answer VALUES (1241, 88, 38, 2, '2026-05-26 11:15:13.571438+01', true);
INSERT INTO public.assessment_answer VALUES (1242, 88, 40, 2, '2026-05-26 11:15:16.687651+01', true);
INSERT INTO public.assessment_answer VALUES (1243, 88, 41, 3, '2026-05-26 11:15:20.804763+01', true);
INSERT INTO public.assessment_answer VALUES (1244, 88, 42, 4, '2026-05-26 11:15:23.270022+01', true);
INSERT INTO public.assessment_answer VALUES (1203, 88, 1, 4, '2026-05-26 11:20:21.751338+01', true);
INSERT INTO public.assessment_answer VALUES (1204, 88, 2, 2, '2026-05-26 11:20:25.68416+01', true);
INSERT INTO public.assessment_answer VALUES (1205, 88, 3, 1, '2026-05-26 11:20:29.502202+01', true);
INSERT INTO public.assessment_answer VALUES (1206, 88, 4, 2, '2026-05-26 11:20:33.637122+01', true);
INSERT INTO public.assessment_answer VALUES (1216, 88, 14, 1, '2026-05-26 11:20:40.345677+01', true);
INSERT INTO public.assessment_answer VALUES (1214, 88, 12, 4, '2026-05-26 11:20:46.656262+01', true);
INSERT INTO public.assessment_answer VALUES (1219, 88, 17, 0, '2026-05-26 11:11:47.785372+01', false);


--
-- Data for Name: domain; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.domain VALUES (15, 'cmmi_1_1', 'CMMI DMM · 1.1 Data Management Strategy', 100, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (16, 'cmmi_1_2', 'CMMI DMM · 1.2 Communications', 101, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (17, 'cmmi_1_3', 'CMMI DMM · 1.3 Data Management Function', 102, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (18, 'cmmi_1_4', 'CMMI DMM · 1.4 Business Case', 103, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (19, 'cmmi_1_5', 'CMMI DMM · 1.5 Program Funding', 104, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (20, 'cmmi_2_1', 'CMMI DMM · 2.1 Governance Management', 105, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (21, 'cmmi_2_2', 'CMMI DMM · 2.2 Business Glossary', 106, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (22, 'cmmi_2_3', 'CMMI DMM · 2.3 Metadata Management', 107, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (23, 'cmmi_3_1', 'CMMI DMM · 3.1 Data Quality Strategy', 108, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (24, 'cmmi_3_2', 'CMMI DMM · 3.2 Data Profiling', 109, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (25, 'cmmi_3_3', 'CMMI DMM · 3.3 Data Quality Assessment', 110, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (26, 'cmmi_3_4', 'CMMI DMM · 3.4 Data Cleansing', 111, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (27, 'cmmi_4_1', 'CMMI DMM · 4.1 Data Requirements Definition', 112, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (28, 'cmmi_4_2', 'CMMI DMM · 4.2 Data Lifecycle Management', 113, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (29, 'cmmi_4_3', 'CMMI DMM · 4.3 Provider Management', 114, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (30, 'cmmi_5_1', 'CMMI DMM · 5.1 Architectural Approach', 115, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (31, 'cmmi_5_2', 'CMMI DMM · 5.2 Architectural Standards', 116, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (32, 'cmmi_5_3', 'CMMI DMM · 5.3 Data Management Platform', 117, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (33, 'cmmi_5_4', 'CMMI DMM · 5.4 Data Integration', 118, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (34, 'cmmi_5_5', 'CMMI DMM · 5.5 Historical Data, Archiving & Retention', 119, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (35, 'cmmi_6_1', 'CMMI DMM · 6.1 Measurement and Analysis', 120, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (36, 'cmmi_6_2', 'CMMI DMM · 6.2 Process Management', 121, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (37, 'cmmi_6_3', 'CMMI DMM · 6.3 Process Quality Assurance', 122, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (38, 'cmmi_6_4', 'CMMI DMM · 6.4 Risk Management', 123, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (39, 'cmmi_6_5', 'CMMI DMM · 6.5 Configuration Management', 124, true, NULL, NULL, NULL);
INSERT INTO public.domain VALUES (1, 'ndi_dg', 'Data Governance (DG)', 1, true, NULL, NULL, 11.75);
INSERT INTO public.domain VALUES (2, 'ndi_mcm', 'Data Catalog & Metadata Management (MCM)', 2, true, NULL, NULL, 10.88);
INSERT INTO public.domain VALUES (3, 'ndi_dq', 'Data Quality (DQ)', 3, true, NULL, NULL, 11.93);
INSERT INTO public.domain VALUES (4, 'ndi_do', 'Data Operations (DO)', 4, true, NULL, NULL, 4.39);
INSERT INTO public.domain VALUES (5, 'ndi_dcm', 'Document & Content Management (DCM)', 5, true, NULL, NULL, 3.16);
INSERT INTO public.domain VALUES (6, 'ndi_dam', 'Data Architecture & Modelling (DAM)', 6, true, NULL, NULL, 5.09);
INSERT INTO public.domain VALUES (7, 'ndi_dsi', 'Data Sharing & Interoperability (DSI)', 7, true, NULL, NULL, 8.95);
INSERT INTO public.domain VALUES (8, 'ndi_rmd', 'Reference & Master Data Management (RMD)', 8, true, NULL, NULL, 9.30);
INSERT INTO public.domain VALUES (9, 'ndi_bia', 'Business Intelligence & Analytics (BIA)', 9, true, NULL, NULL, 4.74);
INSERT INTO public.domain VALUES (10, 'ndi_dvr', 'Data Value Realization (DVR)', 10, true, NULL, NULL, 3.68);
INSERT INTO public.domain VALUES (11, 'ndi_od', 'Open Data (OD)', 11, true, NULL, NULL, 6.49);
INSERT INTO public.domain VALUES (12, 'ndi_foi', 'Freedom of Information (FOI)', 12, true, NULL, NULL, 3.51);
INSERT INTO public.domain VALUES (13, 'ndi_dc', 'Data Classification (DC)', 13, true, NULL, NULL, 6.84);
INSERT INTO public.domain VALUES (14, 'ndi_pdp', 'Personal Data Protection (PDP)', 14, true, NULL, NULL, 9.30);


--
-- Data for Name: evidence; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.evidence VALUES (72, 24, 'aab5d4dc-9c4e-492e-8639-73c3681633d3/4135.ignite-ui-angular-chart-types.png-774x735-1.png', '4135.ignite-ui-angular-chart-types.png-774x735-1.png', '2026-05-21 16:56:01.614564+01', 967, NULL, NULL);
INSERT INTO public.evidence VALUES (73, 24, 'b742bc50-b931-4c7d-8004-e879bad6558c/Capture d''écran 2025-01-07 182017.png', 'Capture d''écran 2025-01-07 182017.png', '2026-05-21 16:56:07.510965+01', 969, NULL, NULL);
INSERT INTO public.evidence VALUES (74, 28, '44123315-a3eb-4271-9b23-eca3543d38bb/4135.ignite-ui-angular-chart-types.png-774x735-1.png', '4135.ignite-ui-angular-chart-types.png-774x735-1.png', '2026-05-22 11:29:52.622589+01', 980, 'MEDIUM', 8);
INSERT INTO public.evidence VALUES (84, 8, '0aaf6684-f8be-4030-be9b-f386338419ec/person_5.jpg', 'person_5.jpg', '2026-05-26 00:01:18.164351+01', 1160, 'MEDIUM', 8);
INSERT INTO public.evidence VALUES (75, 32, '9170a95c-4eb9-4714-afa6-242ea8c23950/img_1.jpg', 'img_1.jpg', '2026-05-25 15:59:00.402921+01', 1048, 'MEDIUM', 8);
INSERT INTO public.evidence VALUES (76, 33, '6710ce37-090f-4792-9700-2fe472e7b2b0/bg_2.jpg', 'bg_2.jpg', '2026-05-25 23:54:48.045122+01', 1068, NULL, NULL);
INSERT INTO public.evidence VALUES (77, 33, '92c90c8c-3887-489f-aa30-6b6238ef5103/img_2.jpg', 'img_2.jpg', '2026-05-25 23:54:54.069355+01', 1069, NULL, NULL);
INSERT INTO public.evidence VALUES (78, 33, '497e2a90-7b67-4c42-9d2f-39a7ad7c0532/logo_4.png', 'logo_4.png', '2026-05-25 23:55:00.278375+01', 1071, NULL, NULL);
INSERT INTO public.evidence VALUES (79, 33, '6f661a26-171e-4153-83cb-cde95e25dfce/img_3.jpg', 'img_3.jpg', '2026-05-25 23:55:07.402025+01', 1076, NULL, NULL);
INSERT INTO public.evidence VALUES (80, 33, 'daccd6c0-1ec3-44e7-bfa2-7eec071daa93/bg_2.jpg', 'bg_2.jpg', '2026-05-25 23:55:13.436178+01', 1110, 'MEDIUM', 8);
INSERT INTO public.evidence VALUES (81, 33, 'a6c8b05d-3095-41dd-9628-400becb9c9f8/img_2.jpg', 'img_2.jpg', '2026-05-25 23:55:13.440181+01', 1111, 'LOW', 8);
INSERT INTO public.evidence VALUES (82, 33, 'ea16607b-d663-4689-8756-898774c6a18a/logo_4.png', 'logo_4.png', '2026-05-25 23:55:13.445244+01', 1113, 'HIGH', 8);
INSERT INTO public.evidence VALUES (83, 33, '4ae98dd7-d172-4f5b-9796-c29ba7188341/img_3.jpg', 'img_3.jpg', '2026-05-25 23:55:13.452243+01', 1118, 'MEDIUM', 8);
INSERT INTO public.evidence VALUES (85, 37, 'ea3aea52-4e15-4a37-b09e-bf852d13c855/bg_1.jpg', 'bg_1.jpg', '2026-05-26 11:16:50.815286+01', 1161, 'LOW', 38);
INSERT INTO public.evidence VALUES (86, 37, 'bfd62532-f696-4f2a-9c20-f30233eb4cac/logo_4.png', 'logo_4.png', '2026-05-26 11:17:00.258685+01', 1162, 'MEDIUM', 38);
INSERT INTO public.evidence VALUES (87, 37, '9c3de6f3-7641-4682-92ab-15f1cb27660f/logo_3.png', 'logo_3.png', '2026-05-26 11:17:09.38457+01', 1163, 'HIGH', 38);
INSERT INTO public.evidence VALUES (88, 37, 'a22c7515-b832-47ab-9461-92f374b9543b/person_4.jpg', 'person_4.jpg', '2026-05-26 11:17:18.193482+01', 1164, 'HIGH', 38);
INSERT INTO public.evidence VALUES (89, 37, '416e6d4a-ef25-4a92-80d4-2c21e081fc7b/bg_1.jpg', 'bg_1.jpg', '2026-05-26 11:20:21.695324+01', 1203, 'LOW', 38);
INSERT INTO public.evidence VALUES (90, 37, '6e577ad6-043a-454a-adf3-29f13c0e03e2/logo_4.png', 'logo_4.png', '2026-05-26 11:20:21.701331+01', 1204, 'MEDIUM', 38);
INSERT INTO public.evidence VALUES (91, 37, 'b1a648f7-a96e-4478-9f16-10586951662a/logo_3.png', 'logo_3.png', '2026-05-26 11:20:21.705328+01', 1205, 'HIGH', 38);
INSERT INTO public.evidence VALUES (92, 37, '71dc8723-746f-4878-a717-2f76a256d341/person_4.jpg', 'person_4.jpg', '2026-05-26 11:20:21.709331+01', 1206, 'HIGH', 38);
INSERT INTO public.evidence VALUES (93, 37, '483da857-e551-4b58-9306-2136e9c01a50/bg_1.jpg', 'bg_1.jpg', '2026-05-26 11:22:45.810676+01', 1249, 'LOW', 38);
INSERT INTO public.evidence VALUES (94, 37, 'b98a0185-a6a5-4c7f-9453-538cc8e1d629/person_4.jpg', 'person_4.jpg', '2026-05-26 11:22:45.817673+01', 1254, 'HIGH', 38);
INSERT INTO public.evidence VALUES (95, 37, '9e288ee4-3112-4214-a46f-318cb81d9b6c/logo_3.png', 'logo_3.png', '2026-05-26 11:22:45.833673+01', 1269, 'HIGH', 38);
INSERT INTO public.evidence VALUES (96, 37, '9adbeb9e-f59e-41a0-9d61-7c1a0301004a/logo_4.png', 'logo_4.png', '2026-05-26 11:22:45.841673+01', 1276, 'MEDIUM', 38);


--
-- Data for Name: framework; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.framework VALUES (1, 'NDI', '2026-05-21 00:36:47.196229+01');
INSERT INTO public.framework VALUES (2, 'CMMI', '2026-05-21 00:36:47.196229+01');


--
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.project VALUES (16, 24, 'Project - slim karray', '2026-05-21 16:51:35.931991+01');
INSERT INTO public.project VALUES (17, 25, 'Project - mohsen benjmaa', '2026-05-21 19:38:35.547513+01');
INSERT INTO public.project VALUES (18, 28, 'Project - iheb fakhfekh', '2026-05-22 09:10:49.701817+01');
INSERT INTO public.project VALUES (19, 31, 'Project - ayman dahmen', '2026-05-22 09:20:50.077598+01');
INSERT INTO public.project VALUES (20, 32, 'Project - karim benjmaa', '2026-05-23 22:44:27.53272+01');
INSERT INTO public.project VALUES (21, 33, 'Project - oussema lazez', '2026-05-25 23:33:18.500074+01');
INSERT INTO public.project VALUES (22, 36, 'Project - haitham frikha', '2026-05-25 23:35:23.862645+01');
INSERT INTO public.project VALUES (23, 37, 'Project - youssef benjmaa', '2026-05-26 11:08:05.447819+01');
INSERT INTO public.project VALUES (24, 40, 'Project - yessine bouaziz', '2026-05-26 11:25:19.212295+01');


--
-- Data for Name: project_framework; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.project_framework VALUES (16, 1, '2026-05-21 16:51:35.933319+01');
INSERT INTO public.project_framework VALUES (16, 2, '2026-05-21 17:39:47.354358+01');
INSERT INTO public.project_framework VALUES (17, 1, '2026-05-21 19:38:35.547661+01');
INSERT INTO public.project_framework VALUES (17, 2, '2026-05-21 19:43:48.006621+01');
INSERT INTO public.project_framework VALUES (18, 1, '2026-05-22 09:10:49.701523+01');
INSERT INTO public.project_framework VALUES (18, 2, '2026-05-22 09:17:06.792747+01');
INSERT INTO public.project_framework VALUES (19, 1, '2026-05-22 09:20:50.077602+01');
INSERT INTO public.project_framework VALUES (19, 2, '2026-05-23 22:04:03.864694+01');
INSERT INTO public.project_framework VALUES (20, 1, '2026-05-23 22:44:27.532476+01');
INSERT INTO public.project_framework VALUES (21, 1, '2026-05-25 23:33:18.502751+01');
INSERT INTO public.project_framework VALUES (22, 2, '2026-05-25 23:35:23.86265+01');
INSERT INTO public.project_framework VALUES (22, 1, '2026-05-25 23:35:23.86265+01');
INSERT INTO public.project_framework VALUES (23, 1, '2026-05-26 11:08:05.445246+01');
INSERT INTO public.project_framework VALUES (23, 2, '2026-05-26 11:22:03.171992+01');
INSERT INTO public.project_framework VALUES (24, 1, '2026-05-26 11:25:19.21298+01');
INSERT INTO public.project_framework VALUES (24, 2, '2026-05-26 11:26:52.885944+01');


--
-- Data for Name: project_consultants; Type: TABLE DATA; Schema: public; Owner: -
--


--
-- Data for Name: question; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.question VALUES (1, 1, 'ndi_dg_01', 'Has the entity established & implemented a Data Management & Personal Data Protection (DM & PDP) Strategy and a DM & PDP Plan with Key Performance Indicators (KPIs) that can be continuously measured to ensure optimization?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (2, 1, 'ndi_dg_02', 'Has the entity established and implemented Data Management (DM) Policies, Standards and Guidelines across all Data Management (DM) Domains?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (3, 1, 'ndi_dg_03', 'Has the entity established and operationalized all roles required for the Data Management Organization as per the NDMO Controls & Specifications?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (4, 1, 'ndi_dg_04', 'Has the entity established and implemented practices for Change Management including awareness, communication, change control, and capability development?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (5, 2, 'ndi_mcm_01', 'Has the entity developed and implemented a plan to integrate and manage Metadata across the entity?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (6, 2, 'ndi_mcm_02', 'Has the entity implemented a Metadata Management and Data Catalog tool / solution?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (7, 2, 'ndi_mcm_03', 'Has the entity defined and implemented formal processes for effective Metadata Management, such as: prioritization, population, access management, and quality issue management, etc., supported & fostered by collaboration across the entity?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (8, 3, 'ndi_dq_01', 'Has the entity developed and implemented a Data Quality (DQ) plan focused on improving the quality of the entity''s Data?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (9, 3, 'ndi_dq_02', 'Has the entity established / developed and implemented practices to manage and improve the quality of the entity''s Data?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (10, 3, 'ndi_dq_03', 'Has the entity established and implemented practices to monitor and report the entity''s Data Quality (DQ) status?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (11, 3, 'ndi_dq_04', 'Has the entity developed Data Quality (DQ) standards, provided definitions for its datasets, and published / uploaded the definitions on the National Data Catalog (NDC)?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (12, 4, 'ndi_do_01', 'Has the entity developed and implemented a plan to manage and satisfy the needs of Data Operations, Data storage and Data retention?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (13, 4, 'ndi_do_02', 'Does the entity have in place a defined methodology, processes and Standard Operating Procedures (SOPs) for database operations?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (14, 4, 'ndi_do_03', 'Does the entity have in place, practices and processes for Business Continuity such as backup and disaster recovery (DR) and a defined Business Continuity Plan (BCP) for the data?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (15, 5, 'ndi_dcm_01', 'Has the entity developed a Document and Content Management (DCM) plan and a Digitization plan to manage the implementation of paperless management activities?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (16, 5, 'ndi_dcm_02', 'Has the entity implemented policies and processes for Document and Content Management (DCM)?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (17, 5, 'ndi_dcm_03', 'Has the entity implemented a tool to support Document and Content Management (DCM)?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (18, 6, 'ndi_dam_01', 'Has the entity developed and implemented a plan to improve its Data Architecture Capabilities?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (19, 6, 'ndi_dam_02', 'Has the entity developed and implemented practices for Data Architecture & Modelling (DAM)?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (20, 7, 'ndi_dsi_01', 'Has the entity developed and implemented a Data Sharing and Integration (DSI) Plan?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (21, 7, 'ndi_dsi_02', 'Has the entity defined and implemented Processes for Sharing Data?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (22, 7, 'ndi_dsi_03', 'Has the entity defined and implemented a data integration architecture?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (23, 7, 'ndi_dsi_04', 'Has the entity developed and implemented Data Sharing Controls?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (24, 8, 'ndi_rmd_01', 'Has the entity developed and implemented a plan for RMD?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (25, 8, 'ndi_rmd_02', 'Has the entity defined and implemented processes to manage RMD?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (26, 8, 'ndi_rmd_03', 'Has the entity implemented a Data Hub for RMD?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (27, 9, 'ndi_bia_01', 'Has the entity developed and implemented a plan for BIA?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (28, 9, 'ndi_bia_02', 'Has the entity identified BIA use cases?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (29, 9, 'ndi_bia_03', 'Has the entity defined and implemented BIA processes?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (30, 9, 'ndi_bia_04', 'Has the entity implemented tools for BIA?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (31, 10, 'ndi_dvr_01', 'Has the entity developed a plan for data value realization?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (32, 10, 'ndi_dvr_02', 'Has the entity implemented data revenue practices?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (33, 11, 'ndi_od_01', 'Has the entity defined a plan for Open Data?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (34, 11, 'ndi_od_02', 'Has the entity defined processes for Open Data?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (35, 11, 'ndi_od_03', 'Has the entity implemented publishing processes?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (36, 12, 'ndi_foi_01', 'Has the entity defined a plan for FOI compliance?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (37, 12, 'ndi_foi_02', 'Has the entity implemented FOI processes?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (38, 13, 'ndi_dc_01', 'Has the entity established a Data Classification plan?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (39, 13, 'ndi_dc_02', 'Has the entity implemented classification processes?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (40, 13, 'ndi_dc_03', 'Has the entity reviewed classified datasets?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (42, 14, 'ndi_pdp_02', 'Has the entity implemented privacy policies and processes?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (43, 15, 'cmmi_1_1_01', 'Do executive stakeholders visibly and actively support the data management strategy?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (44, 15, 'cmmi_1_1_02', 'Is the sequence plan aligned with business priorities and milestones?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (45, 15, 'cmmi_1_1_03', 'Is there sufficient understanding and agreement among executives and operational, IT and business stakeholders, to support a long-term sustainable data management program?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (46, 15, 'cmmi_1_1_04', 'How are projects aligned with the sequence plan that guides implementation of the data management program?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (47, 15, 'cmmi_1_1_05', 'Are staff capabilities and resources in place to architect, design, and lead the data management program?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (48, 15, 'cmmi_1_1_06', 'Is there a commitment to provide training to enable maturity of the data management program?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (49, 16, 'cmmi_1_2_01', 'How are policies, standards, and processes for data management promulgated?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (50, 16, 'cmmi_1_2_02', 'How does the organization keep stakeholders informed about data management plans and projects?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (51, 16, 'cmmi_1_2_03', 'How is bidirectional communication accomplished among business, IT, data management, and executive management about data management priorities, approaches, and deliverables?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (52, 17, 'cmmi_1_3_01', 'Is the data management function defined such that it is clear to all relevant stakeholders?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (53, 17, 'cmmi_1_3_02', 'Is the data management function aligned to the data management strategy, as demonstrated by measures and metrics?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (54, 17, 'cmmi_1_3_03', 'What role do executives play in the design and oversight of the data management function?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (55, 18, 'cmmi_1_4_01', 'How does the organization determine the level of investment required for the data management program?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (56, 18, 'cmmi_1_4_02', 'How does the organization decide whether to develop one umbrella business case or multiple, linked business cases?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (57, 18, 'cmmi_1_4_03', 'What are the success criteria for the business case?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (58, 18, 'cmmi_1_4_04', 'Who needs to be involved? Who needs to approve?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (59, 18, 'cmmi_1_4_05', 'Does the business case reflect the objectives and priorities of the data management strategy?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (60, 18, 'cmmi_1_4_06', 'Does the business case reflect the data management sequence plan?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (61, 18, 'cmmi_1_4_07', 'Has the Data Management Strategy sequence plan, supporting the business case(s), been reviewed and approved by data management sponsors?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (62, 18, 'cmmi_1_4_08', 'Does the business case methodology satisfy Program Funding criteria?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (63, 19, 'cmmi_1_5_01', 'Is there an approved set of investment criteria and priorities for data management?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (64, 19, 'cmmi_1_5_02', 'How does data governance provide oversight for data management funding?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (65, 19, 'cmmi_1_5_03', 'Was the program funding approach developed, evaluated, and approved by relevant stakeholders?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (66, 19, 'cmmi_1_5_04', 'Does the funding model reflect the organization’s business models, priorities, and financial decision processes?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (67, 19, 'cmmi_1_5_05', 'Are there defined and approved cost-benefit allocation methods, defined expense management practices, and business cases across the organization?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (68, 19, 'cmmi_1_5_06', 'Does the funding model consider all expenses of data management (e.g., projects, unique applications, urgent requirements)?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (69, 20, 'cmmi_2_1_01', 'Does data governance provide mechanisms to facilitate collaboration and decision making across lines of business and IT functions?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (70, 20, 'cmmi_2_1_02', 'Does the data governance structure clearly delineate defined responsibilities and accountability for data domains?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (71, 20, 'cmmi_2_1_03', 'How does the organization define roles and responsibilities and ensure that all relevant stakeholders are involved?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (72, 20, 'cmmi_2_1_04', 'Does data governance provide a mechanism for definition of priorities and resolution of competing priorities?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (73, 20, 'cmmi_2_1_05', 'Does data governance effectively provide a process for defining, escalating, and resolving issues?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (74, 20, 'cmmi_2_1_06', 'How does the executive sponsor(s) of data governance actively support the effort?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (75, 20, 'cmmi_2_1_07', 'How are executive sponsor(s) informed of data governance efforts?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (76, 20, 'cmmi_2_1_08', 'Has the organization instituted an effective compliance program across the data lifecycle?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (77, 20, 'cmmi_2_1_09', 'Does the organization have a process in place to review the governance structure and activities?', 9, true, NULL, NULL);
INSERT INTO public.question VALUES (78, 20, 'cmmi_2_1_10', 'Is there appropriate training in place for staff involved in data governance?', 10, true, NULL, NULL);
INSERT INTO public.question VALUES (79, 20, 'cmmi_2_1_11', 'What is the compliance process to carry out the decisions of the data governance body?', 11, true, NULL, NULL);
INSERT INTO public.question VALUES (80, 21, 'cmmi_2_2_01', 'Is there a policy mandating use of and reference to the business glossary?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (81, 21, 'cmmi_2_2_02', 'How are organization-wide business terms, definitions, and corresponding metadata created, approved, verified, and managed?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (82, 21, 'cmmi_2_2_03', 'Is the business glossary promulgated and made accessible to all stakeholders?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (83, 21, 'cmmi_2_2_04', 'Are business terms referenced as the first step in the design of application data stores and repositories?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (84, 21, 'cmmi_2_2_05', 'Does the organization perform cross-referencing and mapping of business-specific terms (synonyms, business unit glossaries, logical attributes, physical data elements, etc.) to standardized business terms?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (85, 21, 'cmmi_2_2_06', 'How is the organization’s business glossary enhanced and maintained to reflect changes and additions?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (86, 21, 'cmmi_2_2_07', 'What role does data governance perform in creating, approving, managing, and updating business terms?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (87, 21, 'cmmi_2_2_08', 'Is a compliance process implemented to ensure that business units and projects are correctly applying business terms?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (88, 21, 'cmmi_2_2_09', 'Does the organization employ a defined process for stakeholders to provide feedback about business terms?', 9, true, NULL, NULL);
INSERT INTO public.question VALUES (89, 22, 'cmmi_2_3_01', 'Is the metadata strategy defined and aligned with internal and selected external standards?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (90, 22, 'cmmi_2_3_02', 'How is the scope of metadata to be addressed for inclusion within the metadata repository defined?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (91, 22, 'cmmi_2_3_03', 'Are all relevant stakeholders involved in defining metadata categories and properties?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (92, 22, 'cmmi_2_3_04', 'What is the method for developing and evaluating standards and processes for metadata management?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (93, 22, 'cmmi_2_3_05', 'What is the method for maintaining or updating the metadata repository?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (95, 22, 'cmmi_2_3_07', 'Are roles and responsibilities clearly defined for the capture, updating, and use of metadata?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (96, 23, 'cmmi_3_1_01', 'Is data quality emphasized in all initiatives involving the data stores?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (97, 23, 'cmmi_3_1_02', 'How does the organization measure data quality program progress?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (98, 23, 'cmmi_3_1_03', 'What organizational unit is responsible for maintaining the data quality strategy?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (99, 23, 'cmmi_3_1_04', 'What organizational units are tasked with data quality initiatives? How are decisions made about standards, methods, and techniques?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (100, 23, 'cmmi_3_1_05', 'Are roles, responsibilities, and accountability clearly defined to foster improved quality of data assets?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (101, 23, 'cmmi_3_1_06', 'Is the data quality strategy widely distributed, communicated, and promulgated?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (102, 23, 'cmmi_3_1_07', 'Does the data quality strategy clearly describe objectives, policies, and processes?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (103, 23, 'cmmi_3_1_08', 'Is data quality integrated with the systems development lifecycle?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (104, 23, 'cmmi_3_1_09', 'How is data quality improvement integrated with business process improvement efforts?', 9, true, NULL, NULL);
INSERT INTO public.question VALUES (105, 24, 'cmmi_3_2_01', 'Does the organization have a standard method for profiling data?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (106, 24, 'cmmi_3_2_02', 'Has the organization trained or acquired staff resources with expertise in data profiling tools and techniques?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (107, 24, 'cmmi_3_2_03', 'Does the organization apply statistical models to analyze data profiling reports?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (108, 24, 'cmmi_3_2_04', 'Do policies and processes specify the criteria for a data store to undergo profiling?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (109, 24, 'cmmi_3_2_05', 'Is data profiling scheduled based on defined events, considerations, or triggers?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (110, 25, 'cmmi_3_3_01', 'Are standard data quality assessment techniques and methods documented and followed?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (111, 25, 'cmmi_3_3_02', 'How are data quality assessments conducted, and are they scheduled or event-driven?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (112, 25, 'cmmi_3_3_03', 'Are standard data quality rules developed for core data attributes?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (113, 25, 'cmmi_3_3_04', 'Are data quality rules engines or assessment tools employed?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (114, 25, 'cmmi_3_3_05', 'Are the business, technical, and cost impacts of data quality issues analyzed and used as input to data quality improvement priorities?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (115, 26, 'cmmi_3_4_01', 'Does the organization have a reusable set of data cleansing processes (automated and manual) to resolve data quality issues?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (116, 26, 'cmmi_3_4_02', 'Is there a defined process for verifying corrections and assessing effectiveness?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (117, 26, 'cmmi_3_4_03', 'How does the organization cleanse duplicate records?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (118, 26, 'cmmi_3_4_04', 'Are corrections implemented at the source of capture?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (119, 26, 'cmmi_3_4_05', 'Are data cleansing processes followed through to analysis of root causes?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (120, 26, 'cmmi_3_4_06', 'Have lines of business established quality thresholds and tolerance limits?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (121, 26, 'cmmi_3_4_07', 'Has the organization deployed a consistent toolset(s) to support data cleansing?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (122, 26, 'cmmi_3_4_08', 'Does ROI incorporate data cleansing costs?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (123, 26, 'cmmi_3_4_09', 'Does the organization apply considerations of operational and reputational risk to determine what data cleansing activities to fund?', 9, true, NULL, NULL);
INSERT INTO public.question VALUES (124, 26, 'cmmi_3_4_10', 'How does the organization define, institutionalize, and monitor the data cleansing process?', 10, true, NULL, NULL);
INSERT INTO public.question VALUES (125, 27, 'cmmi_4_1_01', 'How are business and technical data requirements solicited, captured, evaluated, adjudicated, and verified with stakeholders?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (126, 27, 'cmmi_4_1_02', 'How are the data requirements mapped to the business objectives?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (127, 27, 'cmmi_4_1_03', 'How are approved data requirements validated against standard data definitions as well as logical and physical representations?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (128, 28, 'cmmi_4_2_01', 'What activities, milestones, and products are defined for mapping business processes to the data created and maintained in support of these processes?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (129, 28, 'cmmi_4_2_02', 'Has the organization established clear roles and responsibilities for creating and maintaining a mapping of business processes to data?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (130, 28, 'cmmi_4_2_03', 'Are standard process modeling methods and tools employed to model and define business processes?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (131, 28, 'cmmi_4_2_04', 'Does governance have a role in the management and orchestration of business process data needs, mapping, and prioritization?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (132, 29, 'cmmi_4_3_01', 'How are data sourcing requirements captured, validated, and prioritized?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (133, 29, 'cmmi_4_3_02', 'Are requirements for data sourcing specific, unambiguous, driven by business requirements, and feasibly procurable?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (134, 29, 'cmmi_4_3_03', 'Is there a mechanism that ensures business approval of sourcing requirements?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (135, 29, 'cmmi_4_3_04', 'How are data attributes mapped to data sources and downstream applications?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (136, 29, 'cmmi_4_3_05', 'How is the data source selection process managed?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (137, 29, 'cmmi_4_3_06', 'How are service and content quality from data providers monitored?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (138, 29, 'cmmi_4_3_07', 'Do providers comply with applicable standards?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (139, 29, 'cmmi_4_3_08', 'Is there a repeatable process for managing issues that includes responsible points of contact?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (140, 30, 'cmmi_5_1_01', 'How does the organization approach architecting information assets?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (141, 30, 'cmmi_5_1_02', 'Is the architectural approach consistently followed, and are project-level decisions aligned with the approach?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (142, 30, 'cmmi_5_1_03', 'What is the rationalization method employed for synchronizing, consolidating, or eliminating duplicate data?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (143, 30, 'cmmi_5_1_04', 'How does the organization ensure the sustained progress of the transition plan to the target-state in response to deadlines, tight schedules, and other pressures?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (144, 30, 'cmmi_5_1_05', 'Does the organization have an approved data technology stack, and corresponding governance applied to modifications, additions, and sunsetting?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (145, 30, 'cmmi_5_1_06', 'Has the organization documented and approved the technical capabilities and requirements to satisfy operational business continuity?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (146, 31, 'cmmi_5_2_01', 'What are the categories of standards required for the organization’s target data architecture, and how are they scoped and defined?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (147, 31, 'cmmi_5_2_02', 'How does the organization determine business need and technology strategy for developing approved, standard data access and provisioning?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (148, 31, 'cmmi_5_2_03', 'How are data models approved, maintained, and governed?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (149, 31, 'cmmi_5_2_04', 'Has the organization defined architecturally aligned, standard data access methods and criteria for determining which methods to apply?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (150, 31, 'cmmi_5_2_05', 'How does the organization promulgate, audit, and enforce standards?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (151, 32, 'cmmi_5_3_01', 'How are authoritative data sources defined, selected, and integrated into particular portions of the platform?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (152, 32, 'cmmi_5_3_02', 'How does the organization address overlapping platforms and data duplication?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (153, 32, 'cmmi_5_3_03', 'Does the organization have a process for making “build versus buy” decisions?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (154, 32, 'cmmi_5_3_04', 'How does the organization address platform scalability, security, and resiliency in accordance with anticipated growth of data, users, and overall complexity?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (155, 32, 'cmmi_5_3_05', 'What forms of data, data exchange, and interfaces are supported by the platform?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (158, 33, 'cmmi_5_4_03', 'How does the organization consolidate data effectively where redundancy exists?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (159, 33, 'cmmi_5_4_04', 'Do data integration standards exist, and are they reviewed, monitored, approved, and enforced?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (160, 33, 'cmmi_5_4_05', 'Describe the compliance processes employed to enforce integration standards.', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (161, 33, 'cmmi_5_4_06', 'How are data quality thresholds and targets applied to sources of data at ingestion and integration?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (162, 33, 'cmmi_5_4_07', 'Are the processes to identify missing data automated, and does tracking against defects or gaps support remediation?', 7, true, NULL, NULL);
INSERT INTO public.question VALUES (163, 33, 'cmmi_5_4_08', 'How is adequate staffing ensured for monitoring, managing, and sustaining data quality for ingestion and integration?', 8, true, NULL, NULL);
INSERT INTO public.question VALUES (164, 34, 'cmmi_5_5_01', 'What are the architectural standards and conventions applied to the structure and management of historical data, and how are the corresponding business rules defined and governed?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (165, 34, 'cmmi_5_5_02', 'How is data retention for the required length of time assured?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (166, 34, 'cmmi_5_5_03', 'How is the integrity of archived data maintained?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (167, 34, 'cmmi_5_5_04', 'Is there a consistent approach for the retrieval and integration of archived historical data with current data?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (168, 34, 'cmmi_5_5_05', 'How is an audit trail for data changes monitored and managed?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (169, 34, 'cmmi_5_5_06', 'What considerations are applied to determine when archived data can be deleted?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (170, 35, 'cmmi_6_1_01', 'What measures and analyses exist to determine if data management goals and objectives are being met?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (171, 35, 'cmmi_6_1_02', 'How does the organization define, measure, analyze, and report on data management?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (172, 35, 'cmmi_6_1_03', 'How are measurements and analyses integrated into data management processes?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (173, 36, 'cmmi_6_2_01', 'How are processes, methods, procedures, policies, and standards maintained?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (174, 36, 'cmmi_6_2_02', 'How is process performance measured?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (175, 36, 'cmmi_6_2_03', 'How does the organization measure process compliance?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (176, 36, 'cmmi_6_2_04', 'How does the organization ensure that improvements are identified, pursued, and implemented?', 4, true, NULL, NULL);
INSERT INTO public.question VALUES (177, 36, 'cmmi_6_2_05', 'How does the organization validate that proposed improvements enhance performance before they are deployed?', 5, true, NULL, NULL);
INSERT INTO public.question VALUES (178, 37, 'cmmi_6_3_01', 'Are process noncompliance issues raised to an appropriate level?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (179, 37, 'cmmi_6_3_02', 'Are quality issues analyzed for positive trending?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (180, 37, 'cmmi_6_3_03', 'Do all relevant stakeholders have visibility into the quality of the process and products?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (181, 38, 'cmmi_6_4_01', 'Does the organization know the amount of risk it is operating under?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (182, 38, 'cmmi_6_4_02', 'Has the organization identified and implemented risk mitigation and contingency plans?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (183, 38, 'cmmi_6_4_03', 'Does the organization periodically monitor risks and take appropriate update actions?', 3, true, NULL, NULL);
INSERT INTO public.question VALUES (184, 39, 'cmmi_6_5_01', 'How is configuration management implemented and measured?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (185, 39, 'cmmi_6_5_02', 'How are data changes planned and controlled across the data lifecycle?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (94, 22, 'cmmi_2_3_06', 'Are metadata management processes defined and followed?', 6, true, NULL, NULL);
INSERT INTO public.question VALUES (156, 33, 'cmmi_5_4_01', 'How are data consolidation needs assessed?', 1, true, NULL, NULL);
INSERT INTO public.question VALUES (157, 33, 'cmmi_5_4_02', 'How is future redundancy minimized?', 2, true, NULL, NULL);
INSERT INTO public.question VALUES (41, 14, 'ndi_pdp_01', 'Has the entity performed a PDP assessment and plan?', 1, true, NULL, NULL);


--
-- Data for Name: sub_domain; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Name: app_users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.app_users_id_seq', 40, true);


--
-- Name: assessment_answers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.assessment_answers_id_seq', 1296, true);


--
-- Name: assessment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.assessment_id_seq', 91, true);


--
-- Name: evidences_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.evidences_id_seq', 96, true);


--
-- Name: framework_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.framework_id_seq', 2, true);


--
-- Name: projects_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.projects_id_seq', 24, true);


--
-- Name: questionnaire_questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.questionnaire_questions_id_seq', 185, true);


--
-- Name: questionnaire_segments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.questionnaire_segments_id_seq', 39, true);


--
-- Name: sub_domain_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sub_domain_id_seq', 1, false);


--
-- Name: app_user app_users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT app_users_pkey PRIMARY KEY (id);


--
-- Name: assessment_answer assessment_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT assessment_answers_pkey PRIMARY KEY (id);


--
-- Name: assessment assessment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment
    ADD CONSTRAINT assessment_pkey PRIMARY KEY (id);


--
-- Name: assessment ck_assessment_is_submitted_matches_status; Type: CHECK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE public.assessment
    ADD CONSTRAINT ck_assessment_is_submitted_matches_status CHECK ((is_submitted = ((status)::text = 'SUBMITTED'::text))) NOT VALID;


--
-- Name: evidence evidences_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT evidences_pkey PRIMARY KEY (id);


--
-- Name: framework framework_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.framework
    ADD CONSTRAINT framework_pkey PRIMARY KEY (id);


--
-- Name: project_framework project_framework_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_framework
    ADD CONSTRAINT project_framework_pkey PRIMARY KEY (project_id, framework_id);


--
-- Name: project_consultants pk_project_consultants; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_consultants
    ADD CONSTRAINT pk_project_consultants PRIMARY KEY (project_id, consultant_id);


--
-- Name: project projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: question questionnaire_questions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT questionnaire_questions_pkey PRIMARY KEY (id);


--
-- Name: domain questionnaire_segments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain
    ADD CONSTRAINT questionnaire_segments_pkey PRIMARY KEY (id);


--
-- Name: sub_domain sub_domain_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sub_domain
    ADD CONSTRAINT sub_domain_pkey PRIMARY KEY (id);


--
-- Name: assessment_answer uq_answers_assessment_question; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT uq_answers_assessment_question UNIQUE (assessment_id, question_id);


--
-- Name: app_user uq_app_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT uq_app_users_email UNIQUE (email);


--
-- Name: assessment uq_assessment_client_year_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment
    ADD CONSTRAINT uq_assessment_client_year_version UNIQUE (client_id, year, version);


--
-- Name: evidence uq_evidence_answer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT uq_evidence_answer UNIQUE (answer_id);


--
-- Name: question uq_questions_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT uq_questions_code UNIQUE (code);


--
-- Name: domain uq_segments_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain
    ADD CONSTRAINT uq_segments_code UNIQUE (code);


--
-- Name: idx_answers_assessment; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_answers_assessment ON public.assessment_answer USING btree (assessment_id);


--
-- Name: idx_answers_question; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_answers_question ON public.assessment_answer USING btree (question_id);


--
-- Name: idx_app_users_assigned_consultant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_users_assigned_consultant ON public.app_user USING btree (assigned_consultant_id);


--
-- Name: idx_app_users_managed_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_users_managed_by ON public.app_user USING btree (managed_by_id);


--
-- Name: idx_app_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_users_role ON public.app_user USING btree (role);


--
-- Name: idx_projects_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_client_id ON public.project USING btree (client_id);


--
-- Name: idx_project_consultants_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_consultants_project_id ON public.project_consultants USING btree (project_id);


--
-- Name: idx_project_consultants_consultant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_consultants_consultant_id ON public.project_consultants USING btree (consultant_id);


--
-- Name: idx_questions_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_questions_active ON public.question USING btree (active);


--
-- Name: idx_questions_segment_sort; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_questions_segment_sort ON public.question USING btree (domain_id, sort_order);


--
-- Name: idx_segments_sort; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_segments_sort ON public.domain USING btree (sort_order);


--
-- Name: assessment_answer fk_answers_question; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT fk_answers_question FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE RESTRICT;


--
-- Name: assessment_answer fk_assessment_answer_question; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment_answer
    ADD CONSTRAINT fk_assessment_answer_question FOREIGN KEY (question_id) REFERENCES public.question(id) ON DELETE CASCADE;


--
-- Name: assessment fk_assessment_project; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assessment
    ADD CONSTRAINT fk_assessment_project FOREIGN KEY (project_id) REFERENCES public.project(id) ON DELETE SET NULL NOT VALID;


--
-- Name: domain fk_domain_framework; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.domain
    ADD CONSTRAINT fk_domain_framework FOREIGN KEY (framework_id) REFERENCES public.framework(id) ON DELETE CASCADE;


--
-- Name: evidence fk_evidence_uploader; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidence_uploader FOREIGN KEY (uploaded_by_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: evidence fk_evidences_answer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidences_answer FOREIGN KEY (answer_id) REFERENCES public.assessment_answer(id) ON DELETE CASCADE;


--
-- Name: evidence fk_evidences_rated_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidences_rated_by FOREIGN KEY (rated_by_id) REFERENCES public.app_user(id) ON DELETE SET NULL;


--
-- Name: evidence fk_evidences_uploaded_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evidence
    ADD CONSTRAINT fk_evidences_uploaded_by FOREIGN KEY (uploaded_by_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: project_framework fk_project_framework_framework; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_framework
    ADD CONSTRAINT fk_project_framework_framework FOREIGN KEY (framework_id) REFERENCES public.framework(id) ON DELETE CASCADE;


--
-- Name: project_framework fk_project_framework_project; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_framework
    ADD CONSTRAINT fk_project_framework_project FOREIGN KEY (project_id) REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: project_consultants fk_project_consultants_project; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_consultants
    ADD CONSTRAINT fk_project_consultants_project FOREIGN KEY (project_id) REFERENCES public.project(id) ON DELETE CASCADE;


--
-- Name: project_consultants fk_project_consultants_consultant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_consultants
    ADD CONSTRAINT fk_project_consultants_consultant FOREIGN KEY (consultant_id) REFERENCES public.app_user(id) ON DELETE CASCADE;


--
-- Name: project fk_projects_client; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_projects_client FOREIGN KEY (client_id) REFERENCES public.app_user(id) ON DELETE RESTRICT;


--
-- Name: question fk_question_domain; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT fk_question_domain FOREIGN KEY (domain_id) REFERENCES public.domain(id) ON DELETE CASCADE;


--
-- Name: question fk_question_sub_domain; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT fk_question_sub_domain FOREIGN KEY (sub_domain_id) REFERENCES public.sub_domain(id) ON DELETE SET NULL;


--
-- Name: question fk_questions_segment; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.question
    ADD CONSTRAINT fk_questions_segment FOREIGN KEY (domain_id) REFERENCES public.domain(id) ON DELETE RESTRICT;


--
-- Name: sub_domain fk_sub_domain_domain; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sub_domain
    ADD CONSTRAINT fk_sub_domain_domain FOREIGN KEY (domain_id) REFERENCES public.domain(id) ON DELETE CASCADE;


--
-- Name: app_user fk_users_assigned_consultant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT fk_users_assigned_consultant FOREIGN KEY (assigned_consultant_id) REFERENCES public.app_user(id) ON DELETE SET NULL;


--
-- Name: app_user fk_users_managed_by; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT fk_users_managed_by FOREIGN KEY (managed_by_id) REFERENCES public.app_user(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

