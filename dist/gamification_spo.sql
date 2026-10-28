--
-- PostgreSQL database dump
--

\restrict kXhapQfKh0peCQMR7ErfFWFYVYuvStYr8HWz567AN2EfHP41OqFs9lC42z9nRCa

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

-- Started on 2026-10-23 23:46:37

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
-- TOC entry 908 (class 1247 OID 24628)
-- Name: achievement_condition; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.achievement_condition AS ENUM (
    'tasks_completed',
    'total_xp',
    'streak_days',
    'perfect_scores',
    'quests_completed',
    'manual'
);


ALTER TYPE public.achievement_condition OWNER TO postgres;

--
-- TOC entry 899 (class 1247 OID 24592)
-- Name: difficulty_level; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.difficulty_level AS ENUM (
    'easy',
    'medium',
    'hard',
    'expert'
);


ALTER TYPE public.difficulty_level OWNER TO postgres;

--
-- TOC entry 914 (class 1247 OID 24650)
-- Name: purchase_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.purchase_status AS ENUM (
    'pending',
    'issued',
    'cancelled'
);


ALTER TYPE public.purchase_status OWNER TO postgres;

--
-- TOC entry 911 (class 1247 OID 24642)
-- Name: quest_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.quest_status AS ENUM (
    'in_progress',
    'completed',
    'failed'
);


ALTER TYPE public.quest_status OWNER TO postgres;

--
-- TOC entry 902 (class 1247 OID 24602)
-- Name: submission_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.submission_status AS ENUM (
    'submitted',
    'on_review',
    'graded',
    'rejected',
    'revision'
);


ALTER TYPE public.submission_status OWNER TO postgres;

--
-- TOC entry 896 (class 1247 OID 24578)
-- Name: task_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.task_type AS ENUM (
    'lab',
    'practice',
    'test',
    'homework',
    'project',
    'quiz'
);


ALTER TYPE public.task_type OWNER TO postgres;

--
-- TOC entry 905 (class 1247 OID 24614)
-- Name: xp_reason; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.xp_reason AS ENUM (
    'task_completed',
    'achievement',
    'quest_completed',
    'streak_bonus',
    'manual',
    'reward_purchase'
);


ALTER TYPE public.xp_reason OWNER TO postgres;

--
-- TOC entry 274 (class 1255 OID 25153)
-- Name: buy_reward(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.buy_reward(p_student integer, p_reward integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    r           rewards%ROWTYPE;
    v_coins     INT;
    v_purchase  INT;
BEGIN
    SELECT * INTO r FROM rewards WHERE id = p_reward AND is_active FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Награда недоступна'; END IF;
    IF r.stock IS NOT NULL AND r.stock <= 0 THEN RAISE EXCEPTION 'Награда закончилась'; END IF;

    SELECT coins INTO v_coins FROM student_profiles WHERE user_id = p_student FOR UPDATE;
    IF v_coins IS NULL OR v_coins < r.cost_coins THEN RAISE EXCEPTION 'Недостаточно монет'; END IF;

    INSERT INTO reward_purchases(student_id, reward_id, cost_coins)
    VALUES (p_student, p_reward, r.cost_coins) RETURNING id INTO v_purchase;

    INSERT INTO xp_transactions(student_id, coin_amount, reason, source_id, comment)
    VALUES (p_student, -r.cost_coins, 'reward_purchase', v_purchase, 'Покупка: ' || r.title);

    IF r.stock IS NOT NULL THEN
        UPDATE rewards SET stock = stock - 1 WHERE id = p_reward;
    END IF;
    RETURN v_purchase;
END;
$$;


ALTER FUNCTION public.buy_reward(p_student integer, p_reward integer) OWNER TO postgres;

--
-- TOC entry 273 (class 1255 OID 25152)
-- Name: check_achievements(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.check_achievements(p_student integer) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
    a          achievements%ROWTYPE;
    v_value    INT;
    v_awarded  INT := 0;
BEGIN
    FOR a IN
        SELECT * FROM achievements
         WHERE condition_type <> 'manual'
           AND id NOT IN (SELECT achievement_id FROM user_achievements WHERE student_id = p_student)
    LOOP
        v_value := CASE a.condition_type
            WHEN 'tasks_completed' THEN (
                SELECT COUNT(DISTINCT s.task_id) FROM submissions s
                  JOIN tasks t ON t.id = s.task_id
                 WHERE s.student_id = p_student AND s.status = 'graded'
                   AND (a.discipline_id IS NULL OR t.discipline_id = a.discipline_id))
            WHEN 'total_xp' THEN (SELECT total_xp FROM student_profiles WHERE user_id = p_student)
            WHEN 'streak_days' THEN (SELECT best_streak FROM student_profiles WHERE user_id = p_student)
            WHEN 'perfect_scores' THEN (
                SELECT COUNT(*) FROM submissions s JOIN tasks t ON t.id = s.task_id
                 WHERE s.student_id = p_student AND s.status = 'graded' AND s.score >= t.max_score
                   AND (a.discipline_id IS NULL OR t.discipline_id = a.discipline_id))
            WHEN 'quests_completed' THEN (
                SELECT COUNT(*) FROM student_quests
                 WHERE student_id = p_student AND status = 'completed')
        END;

        IF COALESCE(v_value, 0) >= a.condition_value THEN
            INSERT INTO user_achievements(student_id, achievement_id) VALUES (p_student, a.id);
            INSERT INTO xp_transactions(student_id, xp_amount, coin_amount, reason, source_id, comment)
            VALUES (p_student, a.xp_bonus, a.coin_bonus, 'achievement', a.id, 'Достижение: ' || a.title);
            INSERT INTO notifications(user_id, title, body)
            VALUES (p_student, 'Новое достижение!', a.title);
            v_awarded := v_awarded + 1;
        END IF;
    END LOOP;
    RETURN v_awarded;
END;
$$;


ALTER FUNCTION public.check_achievements(p_student integer) OWNER TO postgres;

--
-- TOC entry 260 (class 1255 OID 25148)
-- Name: fn_apply_xp_transaction(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_apply_xp_transaction() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_new_xp  INT;
    v_level   SMALLINT;
BEGIN
    UPDATE student_profiles
       SET total_xp = GREATEST(total_xp + NEW.xp_amount, 0),
           coins    = GREATEST(coins + NEW.coin_amount, 0)
     WHERE user_id = NEW.student_id
    RETURNING total_xp INTO v_new_xp;

    IF v_new_xp IS NULL THEN
        RAISE EXCEPTION 'Профиль студента % не найден', NEW.student_id;
    END IF;

    SELECT level_no INTO v_level
      FROM levels
     WHERE xp_required <= v_new_xp
     ORDER BY xp_required DESC
     LIMIT 1;

    UPDATE student_profiles SET level_no = COALESCE(v_level, 1)
     WHERE user_id = NEW.student_id;

    RETURN NEW;
END;
$$;


ALTER FUNCTION public.fn_apply_xp_transaction() OWNER TO postgres;

--
-- TOC entry 272 (class 1255 OID 25150)
-- Name: fn_award_on_graded(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_award_on_graded() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_task    tasks%ROWTYPE;
    v_xp      INT;
    v_today   DATE := CURRENT_DATE;
    v_last    DATE;
    v_streak  INT;
BEGIN
    IF NEW.status = 'graded' AND NEW.score IS NOT NULL
       AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'graded') THEN

        SELECT * INTO v_task FROM tasks WHERE id = NEW.task_id;
        v_xp := ROUND(v_task.xp_reward * LEAST(NEW.score / v_task.max_score, 1));

        INSERT INTO xp_transactions(student_id, xp_amount, coin_amount, reason, source_id, comment)
        VALUES (NEW.student_id, v_xp, v_task.coin_reward, 'task_completed', NEW.task_id,
                'Задание: ' || v_task.title)
        ON CONFLICT DO NOTHING;   -- повторная пересдача не даёт XP второй раз

        -- серия дней активности
        SELECT last_activity_date, current_streak INTO v_last, v_streak
          FROM student_profiles WHERE user_id = NEW.student_id;

        IF v_last IS DISTINCT FROM v_today THEN
            v_streak := CASE WHEN v_last = v_today - 1 THEN COALESCE(v_streak, 0) + 1 ELSE 1 END;
            UPDATE student_profiles
               SET current_streak = v_streak,
                   best_streak = GREATEST(best_streak, v_streak),
                   last_activity_date = v_today
             WHERE user_id = NEW.student_id;
        END IF;

        INSERT INTO notifications(user_id, title, body)
        VALUES (NEW.student_id, 'Работа проверена',
                format('«%s»: %s из %s баллов, +%s XP', v_task.title, NEW.score, v_task.max_score, v_xp));
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.fn_award_on_graded() OWNER TO postgres;

--
-- TOC entry 259 (class 1255 OID 25146)
-- Name: fn_create_student_profile(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_create_student_profile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (SELECT code FROM roles WHERE id = NEW.role_id) = 'student' THEN
        INSERT INTO student_profiles(user_id) VALUES (NEW.id)
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.fn_create_student_profile() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 243 (class 1259 OID 24973)
-- Name: achievements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.achievements (
    id integer NOT NULL,
    code character varying(40) NOT NULL,
    title character varying(100) NOT NULL,
    description text,
    icon character varying(255),
    condition_type public.achievement_condition DEFAULT 'manual'::public.achievement_condition NOT NULL,
    condition_value integer,
    discipline_id integer,
    xp_bonus integer DEFAULT 0 NOT NULL,
    coin_bonus integer DEFAULT 0 NOT NULL,
    CONSTRAINT achievements_coin_bonus_check CHECK ((coin_bonus >= 0)),
    CONSTRAINT achievements_condition_value_check CHECK ((condition_value > 0)),
    CONSTRAINT achievements_xp_bonus_check CHECK ((xp_bonus >= 0))
);


ALTER TABLE public.achievements OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 24972)
-- Name: achievements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.achievements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.achievements_id_seq OWNER TO postgres;

--
-- TOC entry 5360 (class 0 OID 0)
-- Dependencies: 242
-- Name: achievements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.achievements_id_seq OWNED BY public.achievements.id;


--
-- TOC entry 228 (class 1259 OID 24743)
-- Name: disciplines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.disciplines (
    id integer NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    is_special boolean DEFAULT true NOT NULL
);


ALTER TABLE public.disciplines OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 24742)
-- Name: disciplines_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.disciplines_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.disciplines_id_seq OWNER TO postgres;

--
-- TOC entry 5361 (class 0 OID 0)
-- Dependencies: 227
-- Name: disciplines_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.disciplines_id_seq OWNED BY public.disciplines.id;


--
-- TOC entry 238 (class 1259 OID 24910)
-- Name: levels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.levels (
    level_no smallint NOT NULL,
    title character varying(60) NOT NULL,
    xp_required integer NOT NULL,
    CONSTRAINT levels_xp_required_check CHECK ((xp_required >= 0))
);


ALTER TABLE public.levels OWNER TO postgres;

--
-- TOC entry 254 (class 1259 OID 25125)
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    title character varying(150) NOT NULL,
    body text,
    is_read boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- TOC entry 253 (class 1259 OID 25124)
-- Name: notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notifications_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notifications_id_seq OWNER TO postgres;

--
-- TOC entry 5362 (class 0 OID 0)
-- Dependencies: 253
-- Name: notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.notifications_id_seq OWNED BY public.notifications.id;


--
-- TOC entry 247 (class 1259 OID 25044)
-- Name: quest_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quest_tasks (
    quest_id integer NOT NULL,
    task_id integer NOT NULL
);


ALTER TABLE public.quest_tasks OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 25020)
-- Name: quests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quests (
    id integer NOT NULL,
    discipline_id integer,
    title character varying(150) NOT NULL,
    description text,
    starts_at timestamp with time zone,
    ends_at timestamp with time zone,
    xp_reward integer DEFAULT 0 NOT NULL,
    coin_reward integer DEFAULT 0 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT quests_check CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at > starts_at))),
    CONSTRAINT quests_coin_reward_check CHECK ((coin_reward >= 0)),
    CONSTRAINT quests_xp_reward_check CHECK ((xp_reward >= 0))
);


ALTER TABLE public.quests OWNER TO postgres;

--
-- TOC entry 245 (class 1259 OID 25019)
-- Name: quests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.quests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.quests_id_seq OWNER TO postgres;

--
-- TOC entry 5363 (class 0 OID 0)
-- Dependencies: 245
-- Name: quests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.quests_id_seq OWNED BY public.quests.id;


--
-- TOC entry 252 (class 1259 OID 25099)
-- Name: reward_purchases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reward_purchases (
    id integer NOT NULL,
    student_id integer NOT NULL,
    reward_id integer NOT NULL,
    cost_coins integer NOT NULL,
    status public.purchase_status DEFAULT 'pending'::public.purchase_status NOT NULL,
    purchased_at timestamp with time zone DEFAULT now() NOT NULL,
    issued_at timestamp with time zone,
    CONSTRAINT reward_purchases_cost_coins_check CHECK ((cost_coins > 0))
);


ALTER TABLE public.reward_purchases OWNER TO postgres;

--
-- TOC entry 251 (class 1259 OID 25098)
-- Name: reward_purchases_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reward_purchases_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reward_purchases_id_seq OWNER TO postgres;

--
-- TOC entry 5364 (class 0 OID 0)
-- Dependencies: 251
-- Name: reward_purchases_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reward_purchases_id_seq OWNED BY public.reward_purchases.id;


--
-- TOC entry 250 (class 1259 OID 25083)
-- Name: rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rewards (
    id integer NOT NULL,
    title character varying(150) NOT NULL,
    description text,
    cost_coins integer NOT NULL,
    stock integer,
    is_active boolean DEFAULT true NOT NULL,
    CONSTRAINT rewards_cost_coins_check CHECK ((cost_coins > 0)),
    CONSTRAINT rewards_stock_check CHECK ((stock >= 0))
);


ALTER TABLE public.rewards OWNER TO postgres;

--
-- TOC entry 249 (class 1259 OID 25082)
-- Name: rewards_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.rewards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rewards_id_seq OWNER TO postgres;

--
-- TOC entry 5365 (class 0 OID 0)
-- Dependencies: 249
-- Name: rewards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.rewards_id_seq OWNED BY public.rewards.id;


--
-- TOC entry 220 (class 1259 OID 24658)
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id smallint NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24657)
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO postgres;

--
-- TOC entry 5366 (class 0 OID 0)
-- Dependencies: 219
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- TOC entry 222 (class 1259 OID 24670)
-- Name: specialties; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.specialties (
    id integer NOT NULL,
    code character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    qualification character varying(200)
);


ALTER TABLE public.specialties OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 24669)
-- Name: specialties_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.specialties_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.specialties_id_seq OWNER TO postgres;

--
-- TOC entry 5367 (class 0 OID 0)
-- Dependencies: 221
-- Name: specialties_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.specialties_id_seq OWNED BY public.specialties.id;


--
-- TOC entry 229 (class 1259 OID 24758)
-- Name: specialty_disciplines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.specialty_disciplines (
    specialty_id integer NOT NULL,
    discipline_id integer NOT NULL
);


ALTER TABLE public.specialty_disciplines OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 24710)
-- Name: student_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_groups (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    specialty_id integer NOT NULL,
    course smallint NOT NULL,
    admission_year smallint NOT NULL,
    curator_id integer,
    CONSTRAINT student_groups_admission_year_check CHECK (((admission_year >= 2000) AND (admission_year <= 2100))),
    CONSTRAINT student_groups_course_check CHECK (((course >= 1) AND (course <= 5)))
);


ALTER TABLE public.student_groups OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 24709)
-- Name: student_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.student_groups_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.student_groups_id_seq OWNER TO postgres;

--
-- TOC entry 5368 (class 0 OID 0)
-- Dependencies: 225
-- Name: student_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.student_groups_id_seq OWNED BY public.student_groups.id;


--
-- TOC entry 239 (class 1259 OID 24921)
-- Name: student_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_profiles (
    user_id integer NOT NULL,
    total_xp integer DEFAULT 0 NOT NULL,
    coins integer DEFAULT 0 NOT NULL,
    level_no smallint DEFAULT 1 NOT NULL,
    current_streak integer DEFAULT 0 NOT NULL,
    best_streak integer DEFAULT 0 NOT NULL,
    last_activity_date date,
    CONSTRAINT student_profiles_coins_check CHECK ((coins >= 0)),
    CONSTRAINT student_profiles_total_xp_check CHECK ((total_xp >= 0))
);


ALTER TABLE public.student_profiles OWNER TO postgres;

--
-- TOC entry 248 (class 1259 OID 25061)
-- Name: student_quests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_quests (
    student_id integer NOT NULL,
    quest_id integer NOT NULL,
    status public.quest_status DEFAULT 'in_progress'::public.quest_status NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone
);


ALTER TABLE public.student_quests OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 24872)
-- Name: submissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.submissions (
    id integer NOT NULL,
    task_id integer NOT NULL,
    student_id integer NOT NULL,
    attempt_no smallint DEFAULT 1 NOT NULL,
    answer_text text,
    file_path character varying(500),
    status public.submission_status DEFAULT 'submitted'::public.submission_status NOT NULL,
    score numeric(5,2),
    teacher_comment text,
    checked_by integer,
    submitted_at timestamp with time zone DEFAULT now() NOT NULL,
    checked_at timestamp with time zone,
    CONSTRAINT submissions_attempt_no_check CHECK ((attempt_no > 0)),
    CONSTRAINT submissions_score_check CHECK ((score >= (0)::numeric))
);


ALTER TABLE public.submissions OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 24871)
-- Name: submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.submissions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.submissions_id_seq OWNER TO postgres;

--
-- TOC entry 5369 (class 0 OID 0)
-- Dependencies: 236
-- Name: submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.submissions_id_seq OWNED BY public.submissions.id;


--
-- TOC entry 235 (class 1259 OID 24826)
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    id integer NOT NULL,
    discipline_id integer NOT NULL,
    topic_id integer,
    author_id integer NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    type public.task_type DEFAULT 'practice'::public.task_type NOT NULL,
    difficulty public.difficulty_level DEFAULT 'medium'::public.difficulty_level NOT NULL,
    max_score numeric(5,2) DEFAULT 100 NOT NULL,
    xp_reward integer DEFAULT 50 NOT NULL,
    coin_reward integer DEFAULT 0 NOT NULL,
    deadline timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tasks_coin_reward_check CHECK ((coin_reward >= 0)),
    CONSTRAINT tasks_max_score_check CHECK ((max_score > (0)::numeric)),
    CONSTRAINT tasks_xp_reward_check CHECK ((xp_reward >= 0))
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 24825)
-- Name: tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tasks_id_seq OWNER TO postgres;

--
-- TOC entry 5370 (class 0 OID 0)
-- Dependencies: 234
-- Name: tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tasks_id_seq OWNED BY public.tasks.id;


--
-- TOC entry 231 (class 1259 OID 24776)
-- Name: teaching_assignments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teaching_assignments (
    id integer NOT NULL,
    discipline_id integer NOT NULL,
    group_id integer NOT NULL,
    teacher_id integer NOT NULL,
    academic_year character varying(9) NOT NULL,
    semester smallint NOT NULL,
    CONSTRAINT teaching_assignments_semester_check CHECK (((semester >= 1) AND (semester <= 10)))
);


ALTER TABLE public.teaching_assignments OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 24775)
-- Name: teaching_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teaching_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teaching_assignments_id_seq OWNER TO postgres;

--
-- TOC entry 5371 (class 0 OID 0)
-- Dependencies: 230
-- Name: teaching_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teaching_assignments_id_seq OWNED BY public.teaching_assignments.id;


--
-- TOC entry 233 (class 1259 OID 24807)
-- Name: topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topics (
    id integer NOT NULL,
    discipline_id integer NOT NULL,
    title character varying(200) NOT NULL,
    order_no smallint DEFAULT 1 NOT NULL
);


ALTER TABLE public.topics OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 24806)
-- Name: topics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topics_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topics_id_seq OWNER TO postgres;

--
-- TOC entry 5372 (class 0 OID 0)
-- Dependencies: 232
-- Name: topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topics_id_seq OWNED BY public.topics.id;


--
-- TOC entry 244 (class 1259 OID 25000)
-- Name: user_achievements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_achievements (
    student_id integer NOT NULL,
    achievement_id integer NOT NULL,
    awarded_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_achievements OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 24682)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    login character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    email character varying(120),
    last_name character varying(60) NOT NULL,
    first_name character varying(60) NOT NULL,
    middle_name character varying(60),
    role_id smallint NOT NULL,
    group_id integer,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 24681)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 5373 (class 0 OID 0)
-- Dependencies: 223
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 241 (class 1259 OID 24950)
-- Name: xp_transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.xp_transactions (
    id bigint NOT NULL,
    student_id integer NOT NULL,
    xp_amount integer DEFAULT 0 NOT NULL,
    coin_amount integer DEFAULT 0 NOT NULL,
    reason public.xp_reason NOT NULL,
    source_id integer,
    comment character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.xp_transactions OWNER TO postgres;

--
-- TOC entry 257 (class 1259 OID 25164)
-- Name: v_rating_discipline; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_rating_discipline AS
 SELECT rank() OVER (PARTITION BY t.discipline_id ORDER BY (sum(x.xp_amount)) DESC) AS place,
    t.discipline_id,
    d.name AS discipline_name,
    u.id AS student_id,
    (((u.last_name)::text || ' '::text) || (u.first_name)::text) AS student_name,
    sum(x.xp_amount) AS discipline_xp,
    count(*) AS tasks_done
   FROM (((public.xp_transactions x
     JOIN public.tasks t ON (((t.id = x.source_id) AND (x.reason = 'task_completed'::public.xp_reason))))
     JOIN public.disciplines d ON ((d.id = t.discipline_id)))
     JOIN public.users u ON ((u.id = x.student_id)))
  GROUP BY t.discipline_id, d.name, u.id, u.last_name, u.first_name;


ALTER VIEW public.v_rating_discipline OWNER TO postgres;

--
-- TOC entry 255 (class 1259 OID 25154)
-- Name: v_rating_global; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_rating_global AS
 SELECT rank() OVER (ORDER BY p.total_xp DESC) AS place,
    u.id AS student_id,
    (((u.last_name)::text || ' '::text) || (u.first_name)::text) AS student_name,
    g.name AS group_name,
    p.total_xp,
    p.level_no,
    l.title AS level_title,
    p.coins
   FROM (((public.student_profiles p
     JOIN public.users u ON ((u.id = p.user_id)))
     LEFT JOIN public.student_groups g ON ((g.id = u.group_id)))
     JOIN public.levels l ON ((l.level_no = p.level_no)))
  WHERE u.is_active;


ALTER VIEW public.v_rating_global OWNER TO postgres;

--
-- TOC entry 256 (class 1259 OID 25159)
-- Name: v_rating_group; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_rating_group AS
 SELECT rank() OVER (PARTITION BY u.group_id ORDER BY p.total_xp DESC) AS place,
    u.group_id,
    g.name AS group_name,
    u.id AS student_id,
    (((u.last_name)::text || ' '::text) || (u.first_name)::text) AS student_name,
    p.total_xp,
    p.level_no
   FROM ((public.student_profiles p
     JOIN public.users u ON ((u.id = p.user_id)))
     JOIN public.student_groups g ON ((g.id = u.group_id)))
  WHERE u.is_active;


ALTER VIEW public.v_rating_group OWNER TO postgres;

--
-- TOC entry 258 (class 1259 OID 25169)
-- Name: v_student_progress; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_student_progress AS
 SELECT s.student_id,
    t.discipline_id,
    d.name AS discipline_name,
    count(DISTINCT t.id) FILTER (WHERE (s.status = 'graded'::public.submission_status)) AS tasks_graded,
    round(avg(((s.score / t.max_score) * (100)::numeric)) FILTER (WHERE (s.status = 'graded'::public.submission_status)), 1) AS avg_percent
   FROM ((public.submissions s
     JOIN public.tasks t ON ((t.id = s.task_id)))
     JOIN public.disciplines d ON ((d.id = t.discipline_id)))
  GROUP BY s.student_id, t.discipline_id, d.name;


ALTER VIEW public.v_student_progress OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 24949)
-- Name: xp_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.xp_transactions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.xp_transactions_id_seq OWNER TO postgres;

--
-- TOC entry 5374 (class 0 OID 0)
-- Dependencies: 240
-- Name: xp_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.xp_transactions_id_seq OWNED BY public.xp_transactions.id;


--
-- TOC entry 5024 (class 2604 OID 24976)
-- Name: achievements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements ALTER COLUMN id SET DEFAULT nextval('public.achievements_id_seq'::regclass);


--
-- TOC entry 4998 (class 2604 OID 24746)
-- Name: disciplines id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplines ALTER COLUMN id SET DEFAULT nextval('public.disciplines_id_seq'::regclass);


--
-- TOC entry 5040 (class 2604 OID 25128)
-- Name: notifications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications ALTER COLUMN id SET DEFAULT nextval('public.notifications_id_seq'::regclass);


--
-- TOC entry 5029 (class 2604 OID 25023)
-- Name: quests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quests ALTER COLUMN id SET DEFAULT nextval('public.quests_id_seq'::regclass);


--
-- TOC entry 5037 (class 2604 OID 25102)
-- Name: reward_purchases id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reward_purchases ALTER COLUMN id SET DEFAULT nextval('public.reward_purchases_id_seq'::regclass);


--
-- TOC entry 5035 (class 2604 OID 25086)
-- Name: rewards id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rewards ALTER COLUMN id SET DEFAULT nextval('public.rewards_id_seq'::regclass);


--
-- TOC entry 4992 (class 2604 OID 24661)
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- TOC entry 4993 (class 2604 OID 24673)
-- Name: specialties id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialties ALTER COLUMN id SET DEFAULT nextval('public.specialties_id_seq'::regclass);


--
-- TOC entry 4997 (class 2604 OID 24713)
-- Name: student_groups id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_groups ALTER COLUMN id SET DEFAULT nextval('public.student_groups_id_seq'::regclass);


--
-- TOC entry 5011 (class 2604 OID 24875)
-- Name: submissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions ALTER COLUMN id SET DEFAULT nextval('public.submissions_id_seq'::regclass);


--
-- TOC entry 5003 (class 2604 OID 24829)
-- Name: tasks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks ALTER COLUMN id SET DEFAULT nextval('public.tasks_id_seq'::regclass);


--
-- TOC entry 5000 (class 2604 OID 24779)
-- Name: teaching_assignments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments ALTER COLUMN id SET DEFAULT nextval('public.teaching_assignments_id_seq'::regclass);


--
-- TOC entry 5001 (class 2604 OID 24810)
-- Name: topics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics ALTER COLUMN id SET DEFAULT nextval('public.topics_id_seq'::regclass);


--
-- TOC entry 4994 (class 2604 OID 24685)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 5020 (class 2604 OID 24953)
-- Name: xp_transactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.xp_transactions ALTER COLUMN id SET DEFAULT nextval('public.xp_transactions_id_seq'::regclass);


--
-- TOC entry 5343 (class 0 OID 24973)
-- Dependencies: 243
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
-- TOC entry 5328 (class 0 OID 24743)
-- Dependencies: 228
-- Data for Name: disciplines; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.disciplines (id, code, name, description, is_special) FROM stdin;
1	МДК.01.01	Разработка программных модулей	Алгоритмизация, ООП, разработка приложений	t
2	МДК.02.01	Технология разработки ПО	Жизненный цикл, тестирование, документирование	t
3	МДК.11.01	Технология разработки и защиты баз данных	Проектирование БД, SQL, администрирование	t
\.


--
-- TOC entry 5338 (class 0 OID 24910)
-- Dependencies: 238
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
-- TOC entry 5354 (class 0 OID 25125)
-- Dependencies: 254
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
\.


--
-- TOC entry 5347 (class 0 OID 25044)
-- Dependencies: 247
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
\.


--
-- TOC entry 5346 (class 0 OID 25020)
-- Dependencies: 246
-- Data for Name: quests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.quests (id, discipline_id, title, description, starts_at, ends_at, xp_reward, coin_reward, is_active) FROM stdin;
2	\N	test	123	2026-10-22 20:53:33.877971+03	\N	80	15	t
3	\N	тестовый квест123	321	2026-10-23 22:35:20.293892+03	2026-11-11 23:59:00+03	80	15	t
1	\N	123	321	2026-10-22 20:47:11.517853+03	\N	80	15	t
\.


--
-- TOC entry 5352 (class 0 OID 25099)
-- Dependencies: 252
-- Data for Name: reward_purchases; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reward_purchases (id, student_id, reward_id, cost_coins, status, purchased_at, issued_at) FROM stdin;
6	4	3	120	issued	2026-10-23 23:25:11.558322+03	2026-10-23 23:25:32.534085+03
\.


--
-- TOC entry 5350 (class 0 OID 25083)
-- Dependencies: 250
-- Data for Name: rewards; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.rewards (id, title, description, cost_coins, stock, is_active) FROM stdin;
1	Автомат по дисциплине	Освобождение от одного практического задания	200	\N	t
2	+1 день к дедлайну	Продление срока сдачи на сутки	50	\N	t
3	Выбор темы проекта	Право выбрать тему курсового проекта	120	9	t
\.


--
-- TOC entry 5320 (class 0 OID 24658)
-- Dependencies: 220
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, code, name) FROM stdin;
1	student	Студент
2	teacher	Преподаватель
3	admin	Администратор
\.


--
-- TOC entry 5322 (class 0 OID 24670)
-- Dependencies: 222
-- Data for Name: specialties; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.specialties (id, code, name, qualification) FROM stdin;
1	09.02.07	Информационные системы и программирование	Программист
\.


--
-- TOC entry 5329 (class 0 OID 24758)
-- Dependencies: 229
-- Data for Name: specialty_disciplines; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.specialty_disciplines (specialty_id, discipline_id) FROM stdin;
1	1
1	2
1	3
\.


--
-- TOC entry 5326 (class 0 OID 24710)
-- Dependencies: 226
-- Data for Name: student_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_groups (id, name, specialty_id, course, admission_year, curator_id) FROM stdin;
1	ИС-21	1	2	2024	\N
2	ИС-31	1	3	2023	\N
\.


--
-- TOC entry 5339 (class 0 OID 24921)
-- Dependencies: 239
-- Data for Name: student_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_profiles (user_id, total_xp, coins, level_no, current_streak, best_streak, last_activity_date) FROM stdin;
5	68	13	1	1	1	2026-10-20
6	41	8	1	1	1	2026-10-20
7	55	10	1	1	1	2026-10-20
1	0	0	1	0	0	\N
4	147	180	2	1	1	2026-10-23
\.


--
-- TOC entry 5348 (class 0 OID 25061)
-- Dependencies: 248
-- Data for Name: student_quests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_quests (student_id, quest_id, status, started_at, completed_at) FROM stdin;
\.


--
-- TOC entry 5337 (class 0 OID 24872)
-- Dependencies: 237
-- Data for Name: submissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.submissions (id, task_id, student_id, attempt_no, answer_text, file_path, status, score, teacher_comment, checked_by, submitted_at, checked_at) FROM stdin;
1	1	7	1	Пять запросов с объяснениями.	\N	graded	70.00	Запросы работают, но нет группировки.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
2	1	4	1	Запросы и скриншоты: github.com/student1/sql-practice	\N	submitted	\N	\N	\N	2026-10-19 15:39:04.021895+03	\N
3	4	6	1	Ответы отправлены.	\N	graded	14.00	Повторите 3НФ.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
4	4	4	1	Ответы на 20 вопросов отправлены.	\N	graded	20.00	Без ошибок!	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
5	5	5	1	Репозиторий: github.com/student2/oop-lab	\N	submitted	\N	\N	\N	2026-10-19 15:39:04.021895+03	\N
6	6	6	1	Диаграмма во вложении.	\N	submitted	\N	\N	\N	2026-10-19 15:39:04.021895+03	\N
7	6	5	1	ER-диаграмма: 5 сущностей.	\N	graded	80.00	Не хватает связи между заказом и оплатой.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
8	6	4	1	Диаграмма в файле er_diagram.png: 6 сущностей, связи 1:M и M:M.	\N	graded	95.00	Отлично, аккуратно.	2	2026-10-19 15:39:04.021895+03	2026-10-20 15:39:04.021895+03
10	3	4	1	{}	\N	graded	50.00	\N	2	2026-10-23 22:03:05.636276+03	2026-10-23 22:16:29.234518+03
\.


--
-- TOC entry 5335 (class 0 OID 24826)
-- Dependencies: 235
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tasks (id, discipline_id, topic_id, author_id, title, description, type, difficulty, max_score, xp_reward, coin_reward, deadline, is_active, created_at) FROM stdin;
2	1	1	2	Проект: приложение Windows Forms	Разработайте небольшое приложение с формой входа и работой с данными.	project	expert	100.00	150	25	2026-11-19 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
3	2	\N	2	Документирование проекта	Подготовьте техническое задание и описание архитектуры вашего проекта.	homework	easy	50.00	40	5	2026-10-18 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
4	3	3	2	Тест: нормальные формы	Тест по нормализации: 1НФ, 2НФ, 3НФ.	test	easy	20.00	30	3	2026-10-23 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
5	1	1	2	Классы и наследование на C#	Реализуйте иерархию классов с наследованием и полиморфизмом (минимум 3 класса).	lab	hard	100.00	100	15	2026-11-03 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
6	3	3	2	Проектирование ER-диаграммы	Спроектируйте ER-диаграмму для предметной области из задания. Укажите сущности, атрибуты и связи.	lab	medium	100.00	60	8	2026-10-27 15:39:04.021895+03	t	2026-10-20 15:39:04.021895+03
1	3	3	2	SQL: выборка с JOIN	Напишите 5 запросов с соединением таблиц и группировкой. Приложите скриншоты результатов.	practice	medium	100.00	50	5	2026-10-30 15:39:04.021895+03	f	2026-10-20 15:39:04.021895+03
\.


--
-- TOC entry 5331 (class 0 OID 24776)
-- Dependencies: 231
-- Data for Name: teaching_assignments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teaching_assignments (id, discipline_id, group_id, teacher_id, academic_year, semester) FROM stdin;
1	1	2	2	2026/2027	1
2	2	2	2	2026/2027	1
3	3	2	2	2026/2027	1
4	1	1	2	2026/2027	1
5	2	1	2	2026/2027	1
6	3	1	2	2026/2027	1
\.


--
-- TOC entry 5333 (class 0 OID 24807)
-- Dependencies: 233
-- Data for Name: topics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.topics (id, discipline_id, title, order_no) FROM stdin;
1	1	Объектно-ориентированное программирование	1
2	3	Язык SQL: выборка данных	2
3	3	Проектирование схемы БД	1
\.


--
-- TOC entry 5344 (class 0 OID 25000)
-- Dependencies: 244
-- Data for Name: user_achievements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_achievements (student_id, achievement_id, awarded_at) FROM stdin;
4	1	2026-10-20 15:39:04.021895+03
5	1	2026-10-20 15:39:04.021895+03
6	1	2026-10-20 15:39:04.021895+03
7	1	2026-10-20 15:39:04.021895+03
\.


--
-- TOC entry 5324 (class 0 OID 24682)
-- Dependencies: 224
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
\.


--
-- TOC entry 5341 (class 0 OID 24950)
-- Dependencies: 241
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
\.


--
-- TOC entry 5375 (class 0 OID 0)
-- Dependencies: 242
-- Name: achievements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.achievements_id_seq', 6, true);


--
-- TOC entry 5376 (class 0 OID 0)
-- Dependencies: 227
-- Name: disciplines_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.disciplines_id_seq', 3, true);


--
-- TOC entry 5377 (class 0 OID 0)
-- Dependencies: 253
-- Name: notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.notifications_id_seq', 13, true);


--
-- TOC entry 5378 (class 0 OID 0)
-- Dependencies: 245
-- Name: quests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.quests_id_seq', 3, true);


--
-- TOC entry 5379 (class 0 OID 0)
-- Dependencies: 251
-- Name: reward_purchases_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reward_purchases_id_seq', 6, true);


--
-- TOC entry 5380 (class 0 OID 0)
-- Dependencies: 249
-- Name: rewards_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.rewards_id_seq', 3, true);


--
-- TOC entry 5381 (class 0 OID 0)
-- Dependencies: 219
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 3, true);


--
-- TOC entry 5382 (class 0 OID 0)
-- Dependencies: 221
-- Name: specialties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.specialties_id_seq', 2, true);


--
-- TOC entry 5383 (class 0 OID 0)
-- Dependencies: 225
-- Name: student_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.student_groups_id_seq', 2, true);


--
-- TOC entry 5384 (class 0 OID 0)
-- Dependencies: 236
-- Name: submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.submissions_id_seq', 10, true);


--
-- TOC entry 5385 (class 0 OID 0)
-- Dependencies: 234
-- Name: tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tasks_id_seq', 6, true);


--
-- TOC entry 5386 (class 0 OID 0)
-- Dependencies: 230
-- Name: teaching_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teaching_assignments_id_seq', 6, true);


--
-- TOC entry 5387 (class 0 OID 0)
-- Dependencies: 232
-- Name: topics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.topics_id_seq', 3, true);


--
-- TOC entry 5388 (class 0 OID 0)
-- Dependencies: 223
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 7, true);


--
-- TOC entry 5389 (class 0 OID 0)
-- Dependencies: 240
-- Name: xp_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.xp_transactions_id_seq', 16, true);


--
-- TOC entry 5117 (class 2606 OID 24994)
-- Name: achievements achievements_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements
    ADD CONSTRAINT achievements_code_key UNIQUE (code);


--
-- TOC entry 5119 (class 2606 OID 24992)
-- Name: achievements achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements
    ADD CONSTRAINT achievements_pkey PRIMARY KEY (id);


--
-- TOC entry 5084 (class 2606 OID 24757)
-- Name: disciplines disciplines_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplines
    ADD CONSTRAINT disciplines_code_key UNIQUE (code);


--
-- TOC entry 5086 (class 2606 OID 24755)
-- Name: disciplines disciplines_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.disciplines
    ADD CONSTRAINT disciplines_pkey PRIMARY KEY (id);


--
-- TOC entry 5107 (class 2606 OID 24918)
-- Name: levels levels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.levels
    ADD CONSTRAINT levels_pkey PRIMARY KEY (level_no);


--
-- TOC entry 5109 (class 2606 OID 24920)
-- Name: levels levels_xp_required_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.levels
    ADD CONSTRAINT levels_xp_required_key UNIQUE (xp_required);


--
-- TOC entry 5134 (class 2606 OID 25139)
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- TOC entry 5125 (class 2606 OID 25050)
-- Name: quest_tasks quest_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quest_tasks
    ADD CONSTRAINT quest_tasks_pkey PRIMARY KEY (quest_id, task_id);


--
-- TOC entry 5123 (class 2606 OID 25038)
-- Name: quests quests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quests
    ADD CONSTRAINT quests_pkey PRIMARY KEY (id);


--
-- TOC entry 5131 (class 2606 OID 25113)
-- Name: reward_purchases reward_purchases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reward_purchases
    ADD CONSTRAINT reward_purchases_pkey PRIMARY KEY (id);


--
-- TOC entry 5129 (class 2606 OID 25097)
-- Name: rewards rewards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rewards
    ADD CONSTRAINT rewards_pkey PRIMARY KEY (id);


--
-- TOC entry 5064 (class 2606 OID 24668)
-- Name: roles roles_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_code_key UNIQUE (code);


--
-- TOC entry 5066 (class 2606 OID 24666)
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- TOC entry 5068 (class 2606 OID 24680)
-- Name: specialties specialties_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialties
    ADD CONSTRAINT specialties_code_key UNIQUE (code);


--
-- TOC entry 5070 (class 2606 OID 24678)
-- Name: specialties specialties_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialties
    ADD CONSTRAINT specialties_pkey PRIMARY KEY (id);


--
-- TOC entry 5088 (class 2606 OID 24764)
-- Name: specialty_disciplines specialty_disciplines_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialty_disciplines
    ADD CONSTRAINT specialty_disciplines_pkey PRIMARY KEY (specialty_id, discipline_id);


--
-- TOC entry 5080 (class 2606 OID 24724)
-- Name: student_groups student_groups_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_groups
    ADD CONSTRAINT student_groups_name_key UNIQUE (name);


--
-- TOC entry 5082 (class 2606 OID 24722)
-- Name: student_groups student_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_groups
    ADD CONSTRAINT student_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 5111 (class 2606 OID 24938)
-- Name: student_profiles student_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_pkey PRIMARY KEY (user_id);


--
-- TOC entry 5127 (class 2606 OID 25071)
-- Name: student_quests student_quests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_quests
    ADD CONSTRAINT student_quests_pkey PRIMARY KEY (student_id, quest_id);


--
-- TOC entry 5103 (class 2606 OID 24890)
-- Name: submissions submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_pkey PRIMARY KEY (id);


--
-- TOC entry 5105 (class 2606 OID 24892)
-- Name: submissions submissions_task_id_student_id_attempt_no_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_task_id_student_id_attempt_no_key UNIQUE (task_id, student_id, attempt_no);


--
-- TOC entry 5099 (class 2606 OID 24854)
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- TOC entry 5090 (class 2606 OID 24790)
-- Name: teaching_assignments teaching_assignments_discipline_id_group_id_academic_year_s_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments
    ADD CONSTRAINT teaching_assignments_discipline_id_group_id_academic_year_s_key UNIQUE (discipline_id, group_id, academic_year, semester);


--
-- TOC entry 5092 (class 2606 OID 24788)
-- Name: teaching_assignments teaching_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments
    ADD CONSTRAINT teaching_assignments_pkey PRIMARY KEY (id);


--
-- TOC entry 5094 (class 2606 OID 24819)
-- Name: topics topics_discipline_id_order_no_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_discipline_id_order_no_key UNIQUE (discipline_id, order_no);


--
-- TOC entry 5096 (class 2606 OID 24817)
-- Name: topics topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_pkey PRIMARY KEY (id);


--
-- TOC entry 5121 (class 2606 OID 25008)
-- Name: user_achievements user_achievements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_pkey PRIMARY KEY (student_id, achievement_id);


--
-- TOC entry 5074 (class 2606 OID 24703)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 5076 (class 2606 OID 24701)
-- Name: users users_login_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_login_key UNIQUE (login);


--
-- TOC entry 5078 (class 2606 OID 24699)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 5115 (class 2606 OID 24964)
-- Name: xp_transactions xp_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.xp_transactions
    ADD CONSTRAINT xp_transactions_pkey PRIMARY KEY (id);


--
-- TOC entry 5132 (class 1259 OID 25145)
-- Name: idx_notifications_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_notifications_user ON public.notifications USING btree (user_id, is_read);


--
-- TOC entry 5100 (class 1259 OID 24909)
-- Name: idx_submissions_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_submissions_status ON public.submissions USING btree (status);


--
-- TOC entry 5101 (class 1259 OID 24908)
-- Name: idx_submissions_student; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_submissions_student ON public.submissions USING btree (student_id);


--
-- TOC entry 5097 (class 1259 OID 24870)
-- Name: idx_tasks_discipline; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tasks_discipline ON public.tasks USING btree (discipline_id);


--
-- TOC entry 5071 (class 1259 OID 24740)
-- Name: idx_users_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_group ON public.users USING btree (group_id);


--
-- TOC entry 5072 (class 1259 OID 24741)
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_role ON public.users USING btree (role_id);


--
-- TOC entry 5112 (class 1259 OID 24970)
-- Name: idx_xp_tx_student; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_xp_tx_student ON public.xp_transactions USING btree (student_id, created_at DESC);


--
-- TOC entry 5113 (class 1259 OID 24971)
-- Name: uq_xp_tx_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_xp_tx_source ON public.xp_transactions USING btree (student_id, reason, source_id) WHERE ((reason = ANY (ARRAY['task_completed'::public.xp_reason, 'achievement'::public.xp_reason, 'quest_completed'::public.xp_reason])) AND (source_id IS NOT NULL));


--
-- TOC entry 5166 (class 2620 OID 25151)
-- Name: submissions trg_submissions_award; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_submissions_award AFTER INSERT OR UPDATE OF status, score ON public.submissions FOR EACH ROW EXECUTE FUNCTION public.fn_award_on_graded();


--
-- TOC entry 5165 (class 2620 OID 25147)
-- Name: users trg_users_create_profile; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_users_create_profile AFTER INSERT ON public.users FOR EACH ROW EXECUTE FUNCTION public.fn_create_student_profile();


--
-- TOC entry 5167 (class 2620 OID 25149)
-- Name: xp_transactions trg_xp_tx_apply; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_xp_tx_apply AFTER INSERT ON public.xp_transactions FOR EACH ROW EXECUTE FUNCTION public.fn_apply_xp_transaction();


--
-- TOC entry 5154 (class 2606 OID 24995)
-- Name: achievements achievements_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.achievements
    ADD CONSTRAINT achievements_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.disciplines(id) ON DELETE CASCADE;


--
-- TOC entry 5135 (class 2606 OID 24735)
-- Name: users fk_users_group; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_group FOREIGN KEY (group_id) REFERENCES public.student_groups(id) ON DELETE SET NULL;


--
-- TOC entry 5164 (class 2606 OID 25140)
-- Name: notifications notifications_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5158 (class 2606 OID 25051)
-- Name: quest_tasks quest_tasks_quest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quest_tasks
    ADD CONSTRAINT quest_tasks_quest_id_fkey FOREIGN KEY (quest_id) REFERENCES public.quests(id) ON DELETE CASCADE;


--
-- TOC entry 5159 (class 2606 OID 25056)
-- Name: quest_tasks quest_tasks_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quest_tasks
    ADD CONSTRAINT quest_tasks_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- TOC entry 5157 (class 2606 OID 25039)
-- Name: quests quests_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quests
    ADD CONSTRAINT quests_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.disciplines(id) ON DELETE CASCADE;


--
-- TOC entry 5162 (class 2606 OID 25119)
-- Name: reward_purchases reward_purchases_reward_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reward_purchases
    ADD CONSTRAINT reward_purchases_reward_id_fkey FOREIGN KEY (reward_id) REFERENCES public.rewards(id);


--
-- TOC entry 5163 (class 2606 OID 25114)
-- Name: reward_purchases reward_purchases_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reward_purchases
    ADD CONSTRAINT reward_purchases_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5139 (class 2606 OID 24770)
-- Name: specialty_disciplines specialty_disciplines_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialty_disciplines
    ADD CONSTRAINT specialty_disciplines_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.disciplines(id) ON DELETE CASCADE;


--
-- TOC entry 5140 (class 2606 OID 24765)
-- Name: specialty_disciplines specialty_disciplines_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.specialty_disciplines
    ADD CONSTRAINT specialty_disciplines_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.specialties(id) ON DELETE CASCADE;


--
-- TOC entry 5137 (class 2606 OID 24730)
-- Name: student_groups student_groups_curator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_groups
    ADD CONSTRAINT student_groups_curator_id_fkey FOREIGN KEY (curator_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5138 (class 2606 OID 24725)
-- Name: student_groups student_groups_specialty_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_groups
    ADD CONSTRAINT student_groups_specialty_id_fkey FOREIGN KEY (specialty_id) REFERENCES public.specialties(id);


--
-- TOC entry 5151 (class 2606 OID 24944)
-- Name: student_profiles student_profiles_level_no_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_level_no_fkey FOREIGN KEY (level_no) REFERENCES public.levels(level_no);


--
-- TOC entry 5152 (class 2606 OID 24939)
-- Name: student_profiles student_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_profiles
    ADD CONSTRAINT student_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5160 (class 2606 OID 25077)
-- Name: student_quests student_quests_quest_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_quests
    ADD CONSTRAINT student_quests_quest_id_fkey FOREIGN KEY (quest_id) REFERENCES public.quests(id) ON DELETE CASCADE;


--
-- TOC entry 5161 (class 2606 OID 25072)
-- Name: student_quests student_quests_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_quests
    ADD CONSTRAINT student_quests_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5148 (class 2606 OID 24903)
-- Name: submissions submissions_checked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_checked_by_fkey FOREIGN KEY (checked_by) REFERENCES public.users(id);


--
-- TOC entry 5149 (class 2606 OID 24898)
-- Name: submissions submissions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5150 (class 2606 OID 24893)
-- Name: submissions submissions_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.submissions
    ADD CONSTRAINT submissions_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE;


--
-- TOC entry 5145 (class 2606 OID 24865)
-- Name: tasks tasks_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id);


--
-- TOC entry 5146 (class 2606 OID 24855)
-- Name: tasks tasks_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.disciplines(id) ON DELETE CASCADE;


--
-- TOC entry 5147 (class 2606 OID 24860)
-- Name: tasks tasks_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topics(id) ON DELETE SET NULL;


--
-- TOC entry 5141 (class 2606 OID 24791)
-- Name: teaching_assignments teaching_assignments_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments
    ADD CONSTRAINT teaching_assignments_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.disciplines(id) ON DELETE CASCADE;


--
-- TOC entry 5142 (class 2606 OID 24796)
-- Name: teaching_assignments teaching_assignments_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments
    ADD CONSTRAINT teaching_assignments_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.student_groups(id) ON DELETE CASCADE;


--
-- TOC entry 5143 (class 2606 OID 24801)
-- Name: teaching_assignments teaching_assignments_teacher_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teaching_assignments
    ADD CONSTRAINT teaching_assignments_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.users(id);


--
-- TOC entry 5144 (class 2606 OID 24820)
-- Name: topics topics_discipline_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_discipline_id_fkey FOREIGN KEY (discipline_id) REFERENCES public.disciplines(id) ON DELETE CASCADE;


--
-- TOC entry 5155 (class 2606 OID 25014)
-- Name: user_achievements user_achievements_achievement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_achievement_id_fkey FOREIGN KEY (achievement_id) REFERENCES public.achievements(id) ON DELETE CASCADE;


--
-- TOC entry 5156 (class 2606 OID 25009)
-- Name: user_achievements user_achievements_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_achievements
    ADD CONSTRAINT user_achievements_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5136 (class 2606 OID 24704)
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- TOC entry 5153 (class 2606 OID 24965)
-- Name: xp_transactions xp_transactions_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.xp_transactions
    ADD CONSTRAINT xp_transactions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Completed on 2026-10-23 23:46:37

--
-- PostgreSQL database dump complete
--

\unrestrict kXhapQfKh0peCQMR7ErfFWFYVYuvStYr8HWz567AN2EfHP41OqFs9lC42z9nRCa

