-- Демо-данные для запуска приложения (выполнять ПОСЛЕ schema.sql в базе gamification_spo)

INSERT INTO specialties(code, name, qualification) VALUES
    ('09.02.07', 'Информационные системы и программирование', 'Программист');

INSERT INTO student_groups(name, specialty_id, course, admission_year)
SELECT g.name, s.id, g.course, g.year
FROM specialties s,
     (VALUES ('ИС-21', 2, 2024), ('ИС-31', 3, 2023)) AS g(name, course, year)
WHERE s.code = '09.02.07';

INSERT INTO disciplines(code, name, description) VALUES
    ('МДК.01.01', 'Разработка программных модулей',         'Алгоритмизация, ООП, разработка приложений'),
    ('МДК.02.01', 'Технология разработки ПО',               'Жизненный цикл, тестирование, документирование'),
    ('МДК.11.01', 'Технология разработки и защиты баз данных', 'Проектирование БД, SQL, администрирование');

INSERT INTO specialty_disciplines(specialty_id, discipline_id)
SELECT s.id, d.id FROM specialties s, disciplines d WHERE s.code = '09.02.07';

INSERT INTO topics(discipline_id, title, order_no)
SELECT d.id, t.title, t.n
FROM disciplines d
JOIN (VALUES ('МДК.11.01', 'Проектирование схемы БД', 1),
             ('МДК.11.01', 'Язык SQL: выборка данных', 2),
             ('МДК.01.01', 'Объектно-ориентированное программирование', 1)) AS t(code, title, n)
  ON t.code = d.code;
