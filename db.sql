--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

-- Started on 2026-10-29 11:15:09

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
-- TOC entry 5 (class 2615 OID 16391)
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- TOC entry 4928 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


--
-- TOC entry 866 (class 1247 OID 16393)
-- Name: achievement_condition; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.achievement_condition AS ENUM (
    'manual',
    'points',
    'tasks',
    'attendance'
);


ALTER TYPE public.achievement_condition OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 231 (class 1259 OID 16489)
-- Name: achievements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.achievements (
    id integer NOT NULL,
    code text,
    title text,
    description text,
    icon text,
    condition_type text,
    condition_value integer,
    discipline_id integer,
    xp_bonus integer,
    coin_bonus integer
);


ALTER TABLE public.achievements OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16415)
-- Name: disciplines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.disciplines (
    id integer NOT NULL,
    code text,
    name text,
    description text,
    is_special boolean
);


ALTER TABLE public.disciplines OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16422)
-- Name: levels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.levels (
    level_no integer NOT NULL,
    title text,
    xp_required integer
);


ALTER TABLE public.levels OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 16525)
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id integer NOT NULL,
    user_id integer,
    title text,
    body text,
    is_read boolean,
    created_at timestamp with time zone
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 16486)
-- Name: quest_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quest_tasks (
    quest_id integer,
    task_id integer
);


ALTER TABLE public.quest_tasks OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16479)
-- Name: quests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quests (
    id integer NOT NULL,
    discipline_id integer,
    title text,
    description text,
    starts_at timestamp with time zone,
    ends_at timestamp with time zone,
    xp_reward integer,
    coin_reward integer,
    is_active boolean
);


ALTER TABLE public.quests OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 16506)
-- Name: reward_purchases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reward_purchases (
    id integer NOT NULL,
    student_id integer,
    reward_id integer,
    cost_coins integer,
    status text,
    purchased_at timestamp with time zone,
    issued_at timestamp with time zone
);


ALTER TABLE public.reward_purchases OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16429)
-- Name: rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rewards (
    id integer NOT NULL,
    title text,
    description text,
    cost_coins integer,
    stock integer,
    is_active boolean
);


ALTER TABLE public.rewards OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 16401)
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id integer NOT NULL,
    code text,
    name text
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16408)
-- Name: specialties; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.specialties (
    id integer NOT NULL,
    code text,
    name text,
    qualification text
);


ALTER TABLE public.specialties OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16450)
-- Name: specialty_disciplines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.specialty_disciplines (
    specialty_id integer,
    discipline_id integer
);


ALTER TABLE public.specialty_disciplines OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16436)
-- Name: student_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_groups (
    id integer NOT NULL,
    name text,
    specialty_id integer,
    course integer,
    admission_year integer,
    curator_id integer
);


ALTER TABLE public.student_groups OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16453)
-- Name: student_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_profiles (
    user_id integer NOT NULL,
    total_xp integer,
    coins integer,
    level_no integer,
    current_streak integer,
    best_streak integer,
    last_activity_date date
);


ALTER TABLE public.student_profiles OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 16513)
-- Name: student_quests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_quests (
    student_id integer,
    quest_id integer,
    status text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);


ALTER TABLE public.student_quests OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 16499)
-- Name: submissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.submissions (
    id integer NOT NULL,
    task_id integer,
    student_id integer,
    attempt_no integer,
    answer_text text,
    file_path text,
    status text,
    score numeric,
    teacher_comment text,
    checked_by integer,
    submitted_at timestamp with time zone,
    checked_at timestamp with time zone
);


ALTER TABLE public.submissions OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 16472)
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    id integer NOT NULL,
    discipline_id integer,
    topic_id integer,
    author_id integer,
    title text,
    description text,
    type text,
    difficulty text,
    max_score numeric,
    xp_reward integer,
    coin_reward integer,
    deadline timestamp with time zone,
    is_active boolean,
    created_at timestamp with time zone
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16458)
-- Name: teaching_assignments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teaching_assignments (
    id integer NOT NULL,
    discipline_id integer,
    group_id integer,
    teacher_id integer,
    academic_year text,
    semester integer
);


ALTER TABLE public.teaching_assignments OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16465)
-- Name: topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topics (
    id integer NOT NULL,
    discipline_id integer,
    title text,
    order_no integer
);


ALTER TABLE public.topics OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 16496)
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_achievements (
    student_id integer,
    achievement_id integer,
    awarded_at timestamp with time zone
);


ALTER TABLE public.user_achievements OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16443)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    login text,
    password_hash text,
    email text,
    last_name text,
    first_name text,
    middle_name text,
    role_id integer,
    group_id integer,
    is_active boolean,
    created_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 16518)
-- Name: xp_transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.xp_transactions (
    id integer NOT NULL,
    student_id integer,
    xp_amount integer,
    coin_amount integer,
    reason text,
    source_id integer,
    comment text,
    created_at timestamp with time zone
);


ALTER TABLE public.xp_transactions OWNER TO postgres;

--
-- TOC entry 4916 (class 0 OID 16489)
-- Dependencies: 231
-- Data for Name: achievements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.achievements (id, code, title, description, icon, condition_type, condition_value, discipline_id, xp_bonus, coin_bonus) FROM stdin;
1	first_task	Первые шаги	Выполнено первое задание	\N	tasks_completed	1	\N	20	5
2	ten_tasks	Трудяга	Выполнено 10 заданий	\N	tasks_completed	10	\N	100	20
3	perfectionist	Перфекционист	5 работ на максимальный балл	\N	perfect_scores	5	\N	150	30
4	streak_7	Неделя без пропусков	Серия активности 7 дней	\N	streak_days	7	\N	100	25
5	xp_500	Полтысячи	Набрано 500 XP	\N	total_xp	500	\N	50	10
6	quest_master	Искатель приключений	Завершено 3 квеста	\N	quests_completed	3	\N	120	30
\.


--
-- TOC entry 4904 (class 0 OID 16415)
-- Dependencies: 219
-- Data for Name: disciplines; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.disciplines (id, code, name, description, is_special) FROM stdin;
1	МДК.01.01	Разработка программных модулей	Алгоритмизация, ООП, разработка приложений	t
2	МДК.02.01	Технология разработки ПО	Жизненный цикл, тестирование, документирование	t
3	МДК.11.01	Технология разработки и защиты баз данных	Проектирование БД, SQL, администрирование	t
\.


--
-- TOC entry 4905 (class 0 OID 16422)
-- Dependencies: 220
-- Data for Name: levels; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.levels (level_no, title, xp_required) FROM stdin;
1	Новичок	0
2	Ученик	100
3	Практик	300
4	Специалист	700
5	Профессионал	1500
6	Эксперт	3000
7	Мастер	6000
\.


--
-- TOC entry 4922 (class 0 OID 16525)
-- Dependencies: 237
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.notifications (id, user_id, title, body, is_read, created_at) FROM stdin;
1	7	Работа проверена	«SQL: выборка с JOIN»: 70.00 из 100.00 баллов, +35 XP	f	2026-10-20 15:39:04.021895+03
2	6	Работа проверена	«Тест: нормальные формы»: 14.00 из 20.00 баллов, +21 XP	f	2026-10-20 15:39:04.021895+03
3	4	Работа проверена	«Тест: нормальные формы»: 20.00 из 20.00 баллов, +30 XP	f	2026-10-20 15:39:04.021895+03
4	5	Работа проверена	«Проектирование ER-диаграммы»: 80.00 из 100.00 баллов, +48 XP	f	2026-10-20 15:39:04.021895+03
5	4	Работа проверена	«Проектирование ER-диаграммы»: 95.00 из 100.00 баллов, +57 XP	f	2026-10-20 15:39:04.021895+03
6	4	Новое достижение!	Первые шаги	f	2026-10-20 15:39:04.021895+03
7	5	Новое достижение!	Первые шаги	f	2026-10-20 15:39:04.021895+03
8	6	Новое достижение!	Первые шаги	f	2026-10-20 15:39:04.021895+03
9	7	Новое достижение!	Первые шаги	f	2026-10-20 15:39:04.021895+03
13	4	Работа проверена	«Документирование проекта»: 50.00 из 50.00 баллов, +40 XP	f	2026-10-23 22:16:29.234518+03
14	4	Работа проверена	«SQL: выборка с JOIN»: 99.00 из 100.00 баллов, +50 XP	f	2026-10-26 17:54:12.225908+03
15	13	Работа проверена	«Классы и наследование на C#»: 99.00 из 100.00 баллов, +99 XP	f	2026-10-28 23:58:10.030322+03
16	13	Новое достижение!	Первые шаги	f	2026-10-28 23:58:10.030322+03
\.


--
-- TOC entry 4915 (class 0 OID 16486)
-- Dependencies: 230
-- Data for Name: quest_tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quest_tasks (quest_id, task_id) FROM stdin;
1	6
1	5
1	4
1	3
1	2
1	1
2	6
2	5
3	6
3	5
4	6
4	5
4	4
4	3
4	2
5	7
5	6
5	5
5	4
5	3
5	2
1	6
1	5
1	4
1	3
1	2
1	1
2	6
2	5
3	6
3	5
4	6
4	5
4	4
4	3
4	2
5	7
5	6
5	5
5	4
5	3
5	2
\.


--
-- TOC entry 4914 (class 0 OID 16479)
-- Dependencies: 229
-- Data for Name: quests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quests (id, discipline_id, title, description, starts_at, ends_at, xp_reward, coin_reward, is_active) FROM stdin;
2	\N	test	123	2026-10-22 20:53:33.877971+03	\N	80	15	t
3	\N	тестовый квест123	321	2026-10-23 22:35:20.293892+03	2026-11-11 23:59:00+03	80	15	t
1	\N	123	321	2026-10-22 20:47:11.517853+03	\N	80	15	t
4	\N	Квест 132	1	2026-10-26 17:56:12.174303+03	\N	80	15	t
5	\N	сдать все работы	321	2026-10-29 00:06:25.237404+03	\N	80	15	t
\.


--
-- TOC entry 4919 (class 0 OID 16506)
-- Dependencies: 234
-- Data for Name: reward_purchases; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reward_purchases (id, student_id, reward_id, cost_coins, status, purchased_at, issued_at) FROM stdin;
6	4	3	120	issued	2026-10-23 23:25:11.558322+03	2026-10-23 23:25:32.534085+03
7	4	2	50	issued	2026-10-26 17:57:12.89753+03	2026-10-26 17:57:24.508519+03
9	4	2	50	pending	2026-10-26 18:29:42.945962+03	\N
8	4	2	50	issued	2026-10-26 17:57:43.403834+03	2026-10-26 18:30:35.863263+03
10	1	1	200	pending	2026-10-28 23:52:14.210073+03	\N
\.


--
-- TOC entry 4906 (class 0 OID 16429)
-- Dependencies: 221
-- Data for Name: rewards; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rewards (id, title, description, cost_coins, stock, is_active) FROM stdin;
1	Автомат по дисциплине	Освобождение от одного практического задания	200	\N	t
2	+1 день к дедлайну	Продление срока сдачи на сутки	50	\N	t
3	Выбор темы проекта	Право выбрать тему курсового проекта	120	9	t
\.


--
-- TOC entry 4902 (class 0 OID 16401)
-- Dependencies: 217
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, code, name) FROM stdin;
1	student	Студент
2	teacher	Преподаватель
3	admin	Администратор
\.


--
-- TOC entry 4903 (class 0 OID 16408)
-- Dependencies: 218
-- Data for Name: specialties; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.specialties (id, code, name, qualification) FROM stdin;
1	09.02.07	Информационные системы и программирование	Программист
\.


--
-- TOC entry 4909 (class 0 OID 16450)
-- Dependencies: 224
-- Data for Name: specialty_disciplines; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.specialty_disciplines (specialty_id, discipline_id) FROM stdin;
1	1
1	2
1	3
1	1
1	2
1	3
\.


--
-- TOC entry 4907 (class 0 OID 16436)
-- Dependencies: 222
-- Data for Name: student_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_groups (id, name, specialty_id, course, admission_year, curator_id) FROM stdin;
1	ИС-21	1	2	2024	\N
2	ИС-31	1	3	2023	\N
4	ИС-123321	1	3	2026	2
\.


--
-- TOC entry 4910 (class 0 OID 16453)
-- Dependencies: 225
-- Data for Name: student_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_profiles (user_id, total_xp, coins, level_no, current_streak, best_streak, last_activity_date) FROM stdin;
11	0	0	1	0	0	\N
12	0	0	1	0	0	\N
4	197	35	2	1	1	2026-10-26
1	0	999799	1	0	0	\N
13	119	20	2	1	1	2026-10-28
14	0	0	1	0	0	\N
5	68	13	1	1	1	2026-10-20
6	41	8	1	1	1	2026-10-20
7	55	10	1	1	1	2026-10-20
\.


--
-- TOC entry 4920 (class 0 OID 16513)
-- Dependencies: 235
-- Data for Name: student_quests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_quests (student_id, quest_id, status, started_at, completed_at) FROM stdin;
\.


--
-- TOC entry 4918 (class 0 OID 16499)
-- Dependencies: 233
-- Data for Name: submissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.submissions (id, task_id, student_id, attempt_no, answer_text, file_path, status, score, teacher_comment, checked_by, submitted_at, checked_at) FROM stdin;
1	1	7	1	Пять запросов с объяснениями.	\N	graded	70.00	Запросы работают, но нет группировки.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
3	4	6	1	Ответы отправлены.	\N	graded	14.00	Повторите 3НФ.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
4	4	4	1	Ответы на 20 вопросов отправлены.	\N	graded	20.00	Без ошибок!	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
5	5	5	1	Репозиторий: github.com/student2/oop-lab	\N	submitted	\N	\N	\N	2026-10-19 15:39:04.021895+03	\N
6	6	6	1	Диаграмма во вложении.	\N	submitted	\N	\N	\N	2026-10-19 15:39:04.021895+03	\N
7	6	5	1	ER-диаграмма: 5 сущностей.	\N	graded	80.00	Не хватает связи между заказом и оплатой.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
8	6	4	1	Диаграмма в файле er_diagram.png: 6 сущностей, связи 1:M и M:M.	\N	graded	95.00	Отлично, аккуратно.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
10	3	4	1	{}	\N	graded	50.00	\N	2	2026-10-23 22:03:05.636276+03	2026-10-23 22:16:29.234518+03
2	1	4	1	Запросы и скриншоты: github.com/student1/sql-practice	\N	graded	99.00	\N	2	2026-10-19 15:39:04.021895+03	2026-10-26 17:54:12.225908+03
12	5	13	1	123321	\N	graded	99.00	\N	2	2026-10-28 23:48:02.020474+03	2026-10-28 23:58:10.030322+03
11	2	4	1	1111	\N	revision	\N	111	2	2026-10-23 23:53:12.069487+03	2026-10-29 00:02:25.786685+03
\.


--
-- TOC entry 4913 (class 0 OID 16472)
-- Dependencies: 228
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tasks (id, discipline_id, topic_id, author_id, title, description, type, difficulty, max_score, xp_reward, coin_reward, deadline, is_active, created_at) FROM stdin;
2	1	1	2	Проект: приложение Windows Forms	Разработайте небольшое приложение с формой входа и работой с данными.	project	expert	100.00	150	25	2026-11-19 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
3	2	\N	2	Документирование проекта	Подготовьте техническое задание и описание архитектуры вашего проекта.	homework	easy	50.00	40	5	2026-10-18 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
4	3	3	2	Тест: нормальные формы	Тест по нормализации: 1НФ, 2НФ, 3НФ.	test	easy	20.00	30	3	2026-10-23 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
5	1	1	2	Классы и наследование на C#	Реализуйте иерархию классов с наследованием и полиморфизмом (минимум 3 класса).	lab	hard	100.00	100	15	2026-11-03 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
6	3	3	2	Проектирование ER-диаграммы	Спроектируйте ER-диаграмму для предметной области из задания. Укажите сущности, атрибуты и связи.	lab	medium	100.00	60	8	2026-10-27 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
1	3	3	2	SQL: выборка с JOIN	Напишите 5 запросов с соединением таблиц и группировкой. Приложите скриншоты результатов.	practice	medium	100.00	50	5	2026-10-30 15:39:04.021895+03	f	2026-10-20 15:39:04.021895+03
7	1	\N	2	11111	33333	practice	medium	100.00	50	5	\N	t	2026-10-28 23:56:21.78238+03
\.


--
-- TOC entry 4911 (class 0 OID 16458)
-- Dependencies: 226
-- Data for Name: teaching_assignments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teaching_assignments (id, discipline_id, group_id, teacher_id, academic_year, semester) FROM stdin;
1	1	2	2	2026/2027	1
2	2	2	2	2026/2027	1
3	3	2	2	2026/2027	1
4	1	1	2	2026/2027	1
5	2	1	2	2026/2027	1
6	3	1	2	2026/2027	1
7	1	4	2	2026/2027	6
\.


--
-- TOC entry 4912 (class 0 OID 16465)
-- Dependencies: 227
-- Data for Name: topics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.topics (id, discipline_id, title, order_no) FROM stdin;
1	1	Объектно-ориентированное программирование	1
2	3	Язык SQL: выборка данных	2
3	3	Проектирование схемы БД	1
\.


--
-- TOC entry 4917 (class 0 OID 16496)
-- Dependencies: 232
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_achievements (student_id, achievement_id, awarded_at) FROM stdin;
4	1	2026-10-20 15:39:04.021895+03
5	1	2026-10-20 15:39:04.021895+03
6	1	2026-10-20 15:39:04.021895+03
7	1	2026-10-20 15:39:04.021895+03
13	1	2026-10-28 23:58:10.030322+03
4	1	2026-10-20 15:39:04.021895+03
5	1	2026-10-20 15:39:04.021895+03
6	1	2026-10-20 15:39:04.021895+03
7	1	2026-10-20 15:39:04.021895+03
13	1	2026-10-28 23:58:10.030322+03
\.


--
-- TOC entry 4908 (class 0 OID 16443)
-- Dependencies: 223
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, login, password_hash, email, last_name, first_name, middle_name, role_id, group_id, is_active, created_at) FROM stdin;
1	neket_tiron	5af7799ae5cfe1d1e9e0ba1d83a9a0c1$feeab5429af6a149c89c96b7421fedcceac9431225a30d11ffbf121d953b4d8d	\N	тирон	никита	\N	1	1	t	2026-10-18 19:42:53.349497+03
2	teacher1	28c7bbb502ecabf7c13d77dd6cf88e29$0d5c2844af0e868c3b49fa7120b516f16e05e840b714bb38178e4c1dadd8c215	petrova@example.com	Петрова	Анна	Сергеевна	2	\N	t	2026-10-20 15:39:04.021895+03
3	teacher2	c2ea825b634cd6b2b6753069cea00cc5$c485b56ebdce74e508c9e943d25d21f189bbce17d204eab2ecbb2c3fc21b91d6	ivanov@example.com	Иванов	Олег	Павлович	2	\N	t	2026-10-20 15:39:04.021895+03
4	student1	ddb4dcd0622cbaf67111d80c1278e600$ee65788edef9fcdac3df3ae46cb33a4d4b8226885b63df6d7daee0d3404179fa	smirnov@example.com	Смирнов	Дмитрий	Алексеевич	1	1	t	2026-10-20 15:39:04.021895+03
5	student2	ca0fc2d2bd344409eedf902135085f11$4b961fce63d52c4d76a913dbd6ea0b2d29992cdc8c45f122806c3ac9c39f2887	kuznetsova@example.com	Кузнецова	Мария	Игоревна	1	1	t	2026-10-20 15:39:04.021895+03
6	student3	b1e5a8aa1e7e0ba8330c3c7d653c615c$de3776fa7d46de6bd735c1d6cefca4054018e053da25d93ae2c6549001e65031	popov@example.com	Попов	Артём	Николаевич	1	1	t	2026-10-20 15:39:04.021895+03
7	student4	6bff58789ec285d45858e3679e303a32$f335ff7cb615f5eb01c65b6338854881138e824b885030d25f577f7ee7bf7322	volkova@example.com	Волкова	Елена	Андреевна	1	2	t	2026-10-20 15:39:04.021895+03
8	admin	bce4c7e633c8698758b81d76e07e7f4b$57866d9a3d90f837a8d31834ccd6246819c78551ec38ff842fbb45f403ddf33d	admin@example.com	Администратор	Системы	\N	3	\N	t	2026-10-24 20:01:39.974414+03
11	pozdman	8e22a79b18df8717b677784b9a820dad$0cac3b080426dd7b7d8e0610c9f7442afe18e3b73e21e5e2b253bff8d52c3207	\N	поздняков	владислав	\N	1	4	t	2026-10-26 18:00:27.349671+03
12	ivan	7e771739b1af425d8dedd4feb0cf9ed5$2fc62b3382bd3cabc0cff3e19c488295eaf924578c71ece408bd0e6faaf4eabe	\N	иванов	иван	иванович	1	2	t	2026-10-26 18:18:44.877196+03
13	danila	d1fd2c21ff123f8b22c91be504f6afc5$22f911e073d04a4d39be4fb070a8abda2e8acde1c7ffd21c7d454a33eadb35f2	\N	Корниев	Данила	\N	1	4	t	2026-10-28 23:39:11.305076+03
14	login	cb0c54308d4d1af02884cfa16e6a75be$0b438d3d46afd4b5bd8211ba640cceda301042e7f7c42185a0c12854058b9aa6	\N	111	3333	999	1	4	t	2026-10-29 00:10:32.751959+03
\.


--
-- TOC entry 4921 (class 0 OID 16518)
-- Dependencies: 236
-- Data for Name: xp_transactions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.xp_transactions (id, student_id, xp_amount, coin_amount, reason, source_id, comment, created_at) FROM stdin;
1	7	35	5	task_completed	1	Задание: SQL: выборка с JOIN	2026-10-20 15:39:04.021895+03
2	6	21	3	task_completed	4	Задание: Тест: нормальные формы	2026-10-20 15:39:04.021895+03
3	4	30	3	task_completed	4	Задание: Тест: нормальные формы	2026-10-20 15:39:04.021895+03
4	5	48	8	task_completed	6	Задание: Проектирование ER-диаграммы	2026-10-20 15:39:04.021895+03
5	4	57	8	task_completed	6	Задание: Проектирование ER-диаграммы	2026-10-20 15:39:04.021895+03
6	4	20	5	achievement	1	Достижение: Первые шаги	2026-10-20 15:39:04.021895+03
7	5	20	5	achievement	1	Достижение: Первые шаги	2026-10-20 15:39:04.021895+03
8	6	20	5	achievement	1	Достижение: Первые шаги	2026-10-20 15:39:04.021895+03
9	7	20	5	achievement	1	Достижение: Первые шаги	2026-10-20 15:39:04.021895+03
13	4	40	5	task_completed	3	Задание: Документирование проекта	2026-10-23 22:16:29.234518+03
14	4	0	10	manual	2	Возврат монет за награду: Автомат по дисциплине	2026-10-23 22:52:48.869222+03
16	4	0	-120	reward_purchase	6	Покупка: Выбор темы проекта	2026-10-23 23:25:11.558322+03
18	1	0	999999	manual	\N	Корректировка администратором	2026-10-24 20:25:32.795174+03
19	4	50	5	task_completed	1	Задание: SQL: выборка с JOIN	2026-10-26 17:54:12.225908+03
20	4	0	-50	reward_purchase	7	Покупка: +1 день к дедлайну	2026-10-26 17:57:12.89753+03
21	4	0	-50	reward_purchase	8	Покупка: +1 день к дедлайну	2026-10-26 17:57:43.403834+03
22	4	0	-50	reward_purchase	9	Покупка: +1 день к дедлайну	2026-10-26 18:29:42.945962+03
23	1	0	-200	reward_purchase	10	Покупка: Автомат по дисциплине	2026-10-28 23:52:14.210073+03
24	13	99	15	task_completed	5	Задание: Классы и наследование на C#	2026-10-28 23:58:10.030322+03
25	13	20	5	achievement	1	Достижение: Первые шаги	2026-10-28 23:58:10.030322+03
\.


--
-- TOC entry 4748 (class 2606 OID 16495)
-- Name: achievements achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements
    ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);


--
-- TOC entry 4728 (class 2606 OID 16421)
-- Name: disciplines disciplines_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplines
    ADD CONSTRAINT disciplines_pkey PRIMARY KEY (id);


--
-- TOC entry 4730 (class 2606 OID 16428)
-- Name: levels levels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.levels
    ADD CONSTRAINT levels_pkey PRIMARY KEY (level_no);


--
-- TOC entry 4756 (class 2606 OID 16531)
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- TOC entry 4746 (class 2606 OID 16485)
-- Name: quests quests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quests
    ADD CONSTRAINT quests_pkey PRIMARY KEY (id);


--
-- TOC entry 4752 (class 2606 OID 16512)
-- Name: reward_purchases reward_purchases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reward_purchases
    ADD CONSTRAINT reward_purchases_pkey PRIMARY KEY (id);


--
-- TOC entry 4732 (class 2606 OID 16435)
-- Name: rewards rewards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rewards
    ADD CONSTRAINT rewards_pkey PRIMARY KEY (id);


--
-- TOC entry 4724 (class 2606 OID 16407)
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- TOC entry 4726 (class 2606 OID 16414)
-- Name: specialties specialties_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialties
    ADD CONSTRAINT specialties_pkey PRIMARY KEY (id);


--
-- TOC entry 4734 (class 2606 OID 16442)
-- Name: student_groups student_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_groups
    ADD CONSTRAINT student_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 4738 (class 2606 OID 16457)
-- Name: student_profiles student_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4750 (class 2606 OID 16505)
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4744 (class 2606 OID 16478)
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- TOC entry 4740 (class 2606 OID 16464)
-- Name: teaching_assignments teaching_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments
    ADD CONSTRAINT teaching_assignments_pkey PRIMARY KEY (id);


--
-- TOC entry 4742 (class 2606 OID 16471)
-- Name: topics topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_pkey PRIMARY KEY (id);


--
-- TOC entry 4736 (class 2606 OID 16449)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 4754 (class 2606 OID 16524)
-- Name: xp_transactions xp_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.xp_transactions
    ADD CONSTRAINT xp_transactions_pkey PRIMARY KEY (id);


--
-- TOC entry 4929 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


-- Completed on 2026-10-29 11:15:09

--
-- PostgreSQL database dump complete
--

