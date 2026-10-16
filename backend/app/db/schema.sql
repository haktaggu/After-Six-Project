-- Initial application tables; no data is inserted at startup.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_profiles (
    student_id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student',
    major TEXT NOT NULL DEFAULT 'CMPE_BS',
    standing TEXT NOT NULL DEFAULT 'unspecified',
    gpa REAL NOT NULL DEFAULT 0,
    earned_units INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_course_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    catalog_number TEXT NOT NULL,
    status TEXT NOT NULL, -- 'completed' or 'in_progress'
    grade TEXT,
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY, -- e.g. 'CMPE-130'
    subject TEXT NOT NULL,
    catalog_number TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    units_min REAL,
    units_max REAL,
    prerequisite_text TEXT,
    corequisite_text TEXT,
    restrictions_text TEXT,
    prerequisite_rule_json TEXT,
    catalog_url TEXT
);

CREATE TABLE IF NOT EXISTS sections (
    id TEXT PRIMARY KEY, -- e.g. 'fall-2026:45123'
    term TEXT NOT NULL,
    class_number TEXT NOT NULL,
    section_number TEXT NOT NULL,
    course_id TEXT NOT NULL,
    title TEXT NOT NULL,
    mode TEXT NOT NULL,
    units REAL,
    open_seats INTEGER,
    notes TEXT,
    source_url TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    days_json TEXT NOT NULL, -- JSON list of days, e.g. ["M", "W"]
    start_time TEXT, -- HH:MM
    end_time TEXT,   -- HH:MM
    location TEXT,
    is_tba INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS instructors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS major_roadmaps (
    major_code TEXT PRIMARY KEY, -- e.g. 'CMPE_BS'
    title TEXT NOT NULL,
    degree_type TEXT NOT NULL DEFAULT 'BS',
    description TEXT
);

CREATE TABLE IF NOT EXISTS roadmap_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_code TEXT NOT NULL,
    course_id TEXT NOT NULL,
    term_order INTEGER NOT NULL, -- semester 1-8
    is_required INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (major_code) REFERENCES major_roadmaps(major_code) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watchlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    term TEXT NOT NULL,
    added_at TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
    UNIQUE (student_id, section_id)
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    student_id TEXT PRIMARY KEY,
    email TEXT,
    phone TEXT,
    discord_webhook TEXT,
    slack_webhook TEXT,
    enabled_channels TEXT NOT NULL DEFAULT '["email"]',
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    destination TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    sent_at TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE
);
