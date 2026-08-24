-- Quizzle SQLite integrity and acceptance-test suite
-- Every query returning zero rows represents a passing exception check unless noted.

PRAGMA integrity_check;
PRAGMA foreign_key_check;
PRAGMA quick_check;

-- Schema and row-count inventory
SELECT type, name FROM sqlite_master WHERE type IN ('table','view','index') ORDER BY type,name;
SELECT 'users' entity,COUNT(*) rows FROM users UNION ALL SELECT 'universities',COUNT(*) FROM universities UNION ALL SELECT 'faculties',COUNT(*) FROM faculties UNION ALL SELECT 'departments',COUNT(*) FROM departments UNION ALL SELECT 'course_catalog',COUNT(*) FROM course_catalog UNION ALL SELECT 'classes',COUNT(*) FROM classes UNION ALL SELECT 'students',COUNT(*) FROM students UNION ALL SELECT 'quizzes',COUNT(*) FROM quizzes UNION ALL SELECT 'questions',COUNT(*) FROM questions UNION ALL SELECT 'attempts',COUNT(*) FROM attempts UNION ALL SELECT 'activity_events',COUNT(*) FROM activity_events UNION ALL SELECT 'resources',COUNT(*) FROM resources;

-- University and curriculum reference data
SELECT ownership_type,COUNT(*) universities FROM universities GROUP BY ownership_type ORDER BY ownership_type;
SELECT f.name faculty,COUNT(DISTINCT d.id) departments,COUNT(cc.id) courses FROM faculties f LEFT JOIN departments d ON d.faculty_id=f.id LEFT JOIN course_catalog cc ON cc.department_id=d.id GROUP BY f.id ORDER BY f.name;
SELECT level,semester,COUNT(*) courses FROM course_catalog GROUP BY level,semester ORDER BY CAST(level AS INTEGER),semester;
SELECT f.name faculty,d.name department,COUNT(cc.id) courses FROM departments d JOIN faculties f ON f.id=d.faculty_id LEFT JOIN course_catalog cc ON cc.department_id=d.id GROUP BY d.id HAVING COUNT(cc.id)=0;
SELECT * FROM universities WHERE ownership_type NOT IN ('Public','State','Private') OR trim(name)='';
SELECT * FROM faculties WHERE trim(name)='';
SELECT * FROM departments WHERE trim(name)='';
SELECT * FROM course_catalog WHERE level NOT IN ('100','200','300','400','500','600') OR semester NOT IN ('First semester','Second semester') OR trim(code)='' OR trim(title)='' OR trim(source_url)='';
SELECT department_id,level,code,COUNT(*) duplicates FROM course_catalog GROUP BY department_id,level,code HAVING COUNT(*)>1;
SELECT name,COUNT(*) duplicates FROM universities GROUP BY lower(name) HAVING COUNT(*)>1;
SELECT faculty_id,name,COUNT(*) duplicates FROM departments GROUP BY faculty_id,lower(name) HAVING COUNT(*)>1;

-- Authentication and ownership
SELECT lower(email),COUNT(*) duplicates FROM users GROUP BY lower(email) HAVING COUNT(*)>1;
SELECT * FROM users WHERE role NOT IN ('admin','teacher') OR trim(name)='' OR trim(email)='' OR trim(password_hash)='';
SELECT * FROM users WHERE active NOT IN (0,1);
SELECT c.* FROM classes c LEFT JOIN users u ON u.id=c.teacher_id WHERE u.id IS NULL OR u.role<>'teacher';
SELECT q.* FROM quizzes q LEFT JOIN users u ON u.id=q.teacher_id WHERE u.id IS NULL OR u.role<>'teacher';
SELECT r.* FROM resources r LEFT JOIN users u ON u.id=r.teacher_id WHERE u.id IS NULL OR u.role<>'teacher';

-- Course groups, rosters, quizzes, and questions
SELECT * FROM classes WHERE trim(name)='' OR trim(course)='' OR trim(join_code)='' OR level IS NULL OR session IS NULL;
SELECT join_code,COUNT(*) duplicates FROM classes GROUP BY join_code HAVING COUNT(*)>1;
SELECT s.* FROM students s LEFT JOIN classes c ON c.id=s.class_id WHERE c.id IS NULL;
SELECT class_id,student_number,COUNT(*) duplicates FROM students WHERE student_number IS NOT NULL AND trim(student_number)<>'' GROUP BY class_id,student_number HAVING COUNT(*)>1;
SELECT * FROM quizzes WHERE status NOT IN ('Draft','Live','Closed') OR trim(title)='' OR trim(share_code)='' OR time_limit<=0;
SELECT share_code,COUNT(*) duplicates FROM quizzes GROUP BY share_code HAVING COUNT(*)>1;
SELECT q.* FROM quizzes q JOIN classes c ON c.id=q.class_id WHERE q.teacher_id<>c.teacher_id;
SELECT qu.* FROM questions qu LEFT JOIN quizzes q ON q.id=qu.quiz_id WHERE q.id IS NULL;
SELECT * FROM questions WHERE trim(prompt)='' OR points<=0 OR question_type NOT IN ('Multiple choice','Open ended');
SELECT * FROM questions WHERE question_type='Multiple choice' AND (options_json IS NULL OR options_json IN ('','[]'));

-- Attempts, scoring, timestamps, and monitoring
SELECT a.* FROM attempts a LEFT JOIN quizzes q ON q.id=a.quiz_id LEFT JOIN students s ON s.id=a.student_id WHERE q.id IS NULL OR s.id IS NULL;
SELECT a.* FROM attempts a JOIN quizzes q ON q.id=a.quiz_id JOIN students s ON s.id=a.student_id WHERE s.class_id<>q.class_id;
SELECT * FROM attempts WHERE status NOT IN ('in_progress','submitted');
SELECT * FROM attempts WHERE datetime(started_at) IS NULL OR (submitted_at IS NOT NULL AND datetime(submitted_at)<datetime(started_at));
SELECT * FROM attempts WHERE score<0 OR max_score<0 OR score>max_score;
SELECT * FROM attempts WHERE status='submitted' AND submitted_at IS NULL;
SELECT * FROM attempts WHERE status='in_progress' AND submitted_at IS NOT NULL;
SELECT quiz_id,student_id,COUNT(*) active_attempts FROM attempts WHERE status='in_progress' GROUP BY quiz_id,student_id HAVING COUNT(*)>1;
SELECT e.* FROM activity_events e LEFT JOIN attempts a ON a.id=e.attempt_id WHERE a.id IS NULL;
SELECT * FROM activity_events WHERE duration_seconds<0 OR datetime(started_at) IS NULL OR (ended_at IS NOT NULL AND datetime(ended_at)<datetime(started_at));
SELECT * FROM activity_events WHERE event_type IS NULL OR trim(event_type)='';
SELECT a.id,a.started_at,a.submitted_at,CAST((julianday(a.submitted_at)-julianday(a.started_at))*86400 AS INTEGER) elapsed_seconds FROM attempts a WHERE a.submitted_at IS NOT NULL AND (julianday(a.submitted_at)-julianday(a.started_at))*86400<0;

-- Resources
SELECT r.* FROM resources r LEFT JOIN classes c ON c.id=r.class_id WHERE c.id IS NULL OR c.teacher_id<>r.teacher_id;
SELECT * FROM resources WHERE kind NOT IN ('file','link') OR trim(title)='' OR trim(location)='';

-- Reporting views: representative acceptance queries
SELECT * FROM v_university_register ORDER BY university_type,university LIMIT 20;
SELECT * FROM v_academic_catalog ORDER BY faculty,department,CAST(level AS INTEGER),semester,course_code LIMIT 100;
SELECT * FROM v_course_catalog ORDER BY faculty,department,CAST(level AS INTEGER),semester,code LIMIT 100;
SELECT * FROM v_teacher_courses ORDER BY teacher,session DESC,level,semester;
SELECT * FROM v_quiz_overview ORDER BY teacher,course_group,quiz_id;
SELECT * FROM v_attempt_reporting ORDER BY started_at DESC;
SELECT * FROM v_activity_event_audit ORDER BY started_at DESC;
SELECT * FROM v_resource_sharing ORDER BY created_at DESC;
