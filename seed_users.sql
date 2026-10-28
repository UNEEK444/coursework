-- Тестовые пользователи, задания и сдачи для демонстрации приложения.
-- Выполнять ПОСЛЕ schema.sql и seed_demo.sql, в базе gamification_spo.
-- Пароль у ВСЕХ тестовых пользователей: 123456
--   администратор: admin
--   преподаватели: teacher1, teacher2
--   студенты:      student1, student2, student3 (группа ИС-21), student4 (группа ИС-31)
-- Скрипт можно запускать повторно: уже существующие данные не дублируются.

BEGIN;

INSERT INTO users(login, password_hash, email, last_name, first_name, middle_name, role_id, group_id)
SELECT v.login, v.pw, v.email, v.ln, v.fn, v.mn,
       (SELECT id FROM roles WHERE code = v.role),
       (SELECT id FROM student_groups WHERE name = v.grp)
FROM (VALUES
    ('admin', '28c7bbb502ecabf7c13d77dd6cf88e29$0d5c2844af0e868c3b49fa7120b516f16e05e840b714bb38178e4c1dadd8c215', 'admin@example.com', 'Администратор', 'Системы', NULL, 'admin', NULL),
    ('teacher1', '28c7bbb502ecabf7c13d77dd6cf88e29$0d5c2844af0e868c3b49fa7120b516f16e05e840b714bb38178e4c1dadd8c215', 'petrova@example.com', 'Петрова', 'Анна', 'Сергеевна', 'teacher', NULL),
    ('teacher2', 'c2ea825b634cd6b2b6753069cea00cc5$c485b56ebdce74e508c9e943d25d21f189bbce17d204eab2ecbb2c3fc21b91d6', 'ivanov@example.com', 'Иванов', 'Олег', 'Павлович', 'teacher', NULL),
    ('student1', 'ddb4dcd0622cbaf67111d80c1278e600$ee65788edef9fcdac3df3ae46cb33a4d4b8226885b63df6d7daee0d3404179fa', 'smirnov@example.com', 'Смирнов', 'Дмитрий', 'Алексеевич', 'student', 'ИС-21'),
    ('student2', 'ca0fc2d2bd344409eedf902135085f11$4b961fce63d52c4d76a913dbd6ea0b2d29992cdc8c45f122806c3ac9c39f2887', 'kuznetsova@example.com', 'Кузнецова', 'Мария', 'Игоревна', 'student', 'ИС-21'),
    ('student3', 'b1e5a8aa1e7e0ba8330c3c7d653c615c$de3776fa7d46de6bd735c1d6cefca4054018e053da25d93ae2c6549001e65031', 'popov@example.com', 'Попов', 'Артём', 'Николаевич', 'student', 'ИС-21'),
    ('student4', '6bff58789ec285d45858e3679e303a32$f335ff7cb615f5eb01c65b6338854881138e824b885030d25f577f7ee7bf7322', 'volkova@example.com', 'Волкова', 'Елена', 'Андреевна', 'student', 'ИС-31')
) AS v(login, pw, email, ln, fn, mn, role, grp)
ON CONFLICT (login) DO NOTHING;

-- ---------------------------------------------------------------------
-- Задания преподавателя teacher1
-- ---------------------------------------------------------------------
INSERT INTO tasks(discipline_id, topic_id, author_id, title, description, type, difficulty,
                  max_score, xp_reward, coin_reward, deadline)
SELECT d.id,
       (SELECT id FROM topics WHERE discipline_id = d.id ORDER BY order_no LIMIT 1),
       (SELECT id FROM users WHERE login = 'teacher1'),
       v.title, v.descr, v.type::task_type, v.diff::difficulty_level,
       v.max_score, v.xp, v.coins, v.deadline
FROM (VALUES
    ('МДК.11.01', 'Проектирование ER-диаграммы',
     'Спроектируйте ER-диаграмму для предметной области из задания. Укажите сущности, атрибуты и связи.',
     'lab', 'medium', 100, 60, 8, now() + interval '7 days'),
    ('МДК.11.01', 'SQL: выборка с JOIN',
     'Напишите 5 запросов с соединением таблиц и группировкой. Приложите скриншоты результатов.',
     'practice', 'medium', 100, 50, 5, now() + interval '10 days'),
    ('МДК.11.01', 'Тест: нормальные формы',
     'Тест по нормализации: 1НФ, 2НФ, 3НФ.',
     'test', 'easy', 20, 30, 3, now() + interval '3 days'),
    ('МДК.01.01', 'Классы и наследование на C#',
     'Реализуйте иерархию классов с наследованием и полиморфизмом (минимум 3 класса).',
     'lab', 'hard', 100, 100, 15, now() + interval '14 days'),
    ('МДК.01.01', 'Проект: приложение Windows Forms',
     'Разработайте небольшое приложение с формой входа и работой с данными.',
     'project', 'expert', 100, 150, 25, now() + interval '30 days'),
    ('МДК.02.01', 'Документирование проекта',
     'Подготовьте техническое задание и описание архитектуры вашего проекта.',
     'homework', 'easy', 50, 40, 5, now() - interval '2 days')
) AS v(code, title, descr, type, diff, max_score, xp, coins, deadline)
JOIN disciplines d ON d.code = v.code
WHERE NOT EXISTS (SELECT 1 FROM tasks t WHERE t.title = v.title);

-- ---------------------------------------------------------------------
-- Сдачи. Оценённые работы сами начисляют XP, монеты, серию и уведомления
-- через триггеры БД; работы со статусом submitted ждут проверки.
-- ---------------------------------------------------------------------
INSERT INTO submissions(task_id, student_id, attempt_no, answer_text, status, score,
                        teacher_comment, checked_by, submitted_at, checked_at)
SELECT t.id, u.id, 1, v.answer, v.status::submission_status, v.score, v.comment,
       CASE WHEN v.status = 'submitted' THEN NULL ELSE (SELECT id FROM users WHERE login = 'teacher1') END,
       now() - interval '1 day',
       CASE WHEN v.status = 'submitted' THEN NULL ELSE now() END
FROM (VALUES
    ('student1', 'Проектирование ER-диаграммы', 'Диаграмма в файле er_diagram.png: 6 сущностей, связи 1:M и M:M.', 'graded', 95, 'Отлично, аккуратно.'),
    ('student1', 'Тест: нормальные формы',      'Ответы на 20 вопросов отправлены.',                          'graded', 20, 'Без ошибок!'),
    ('student1', 'SQL: выборка с JOIN',          'Запросы и скриншоты: github.com/student1/sql-practice',      'submitted', NULL, NULL),
    ('student2', 'Проектирование ER-диаграммы', 'ER-диаграмма: 5 сущностей.',                                  'graded', 80, 'Не хватает связи между заказом и оплатой.'),
    ('student2', 'Классы и наследование на C#',  'Репозиторий: github.com/student2/oop-lab',                   'submitted', NULL, NULL),
    ('student3', 'Тест: нормальные формы',      'Ответы отправлены.',                                          'graded', 14, 'Повторите 3НФ.'),
    ('student3', 'Проектирование ER-диаграммы', 'Диаграмма во вложении.',                                      'submitted', NULL, NULL),
    ('student4', 'SQL: выборка с JOIN',          'Пять запросов с объяснениями.',                              'graded', 70, 'Запросы работают, но нет группировки.')
) AS v(login, title, answer, status, score, comment)
JOIN users u ON u.login = v.login
JOIN tasks t ON t.title = v.title
ON CONFLICT (task_id, student_id, attempt_no) DO NOTHING;

-- Выдать достижения, если условия уже выполнены
SELECT check_achievements(id) FROM users WHERE login LIKE 'student%';

COMMIT;
