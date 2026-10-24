CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    csrf_token TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_profiles (
    student_id TEXT PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    major TEXT,
    standing TEXT NOT NULL DEFAULT 'unspecified'
        CHECK (standing IN ('freshman', 'sophomore', 'junior', 'senior', 'graduate', 'unspecified')),
    gpa REAL CHECK (gpa >= 0 AND gpa <= 4),
    earned_units INTEGER CHECK (earned_units IS NULL OR (earned_units >= 0 AND typeof(earned_units) = 'integer')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (major) REFERENCES major_roadmaps(major_code)
);

CREATE TABLE IF NOT EXISTS student_course_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    term TEXT,
    status TEXT NOT NULL CHECK (status IN ('completed', 'in_progress', 'planned')),
    grade TEXT CHECK (grade IN ('A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'CR', 'NC', 'WU', 'IC', 'W', 'I', 'RP', 'RD', 'AU')),
    CHECK (status = 'completed' OR grade IS NULL),
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id),
    FOREIGN KEY (term) REFERENCES terms(id),
    UNIQUE (student_id, course_id)
);

CREATE TABLE IF NOT EXISTS demo_seed_state (
    name TEXT PRIMARY KEY,
    completed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
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
    id TEXT PRIMARY KEY,
    term TEXT NOT NULL,
    class_number TEXT NOT NULL,
    section_number TEXT NOT NULL,
    course_id TEXT NOT NULL,
    title TEXT NOT NULL,
    mode TEXT NOT NULL,
    units REAL,
    open_seats INTEGER CHECK (open_seats >= 0),
    notes TEXT,
    source_url TEXT NOT NULL,
    last_checked_at TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (term) REFERENCES terms(id)
);

CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    days_json TEXT NOT NULL,
    start_time TEXT,
    end_time TEXT,
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
    major_code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    degree_type TEXT NOT NULL DEFAULT 'BS',
    description TEXT
);

CREATE TABLE IF NOT EXISTS roadmap_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    major_code TEXT NOT NULL,
    course_id TEXT NOT NULL,
    term_order INTEGER NOT NULL CHECK (term_order >= 1),
    is_required INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (major_code) REFERENCES major_roadmaps(major_code) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (major_code, course_id)
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
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id TEXT PRIMARY KEY NOT NULL,
    event_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type = 'section_opened'),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
    created_at TEXT NOT NULL,
    sent_at TEXT,
    last_error TEXT,
    FOREIGN KEY (student_id) REFERENCES student_profiles(student_id) ON DELETE CASCADE,
    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES availability_events(id) ON DELETE CASCADE,
    UNIQUE (event_id, student_id)
);

CREATE TABLE IF NOT EXISTS terms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS availability_events (
    id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL REFERENCES sections(id),
    previous_seats INTEGER NOT NULL CHECK (previous_seats = 0),
    new_seats INTEGER NOT NULL CHECK (new_seats > 0),
    detected_at TEXT NOT NULL,
    processed_at TEXT
);
