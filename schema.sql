-- Skill Swap Database Schema

CREATE TABLE users (
  id              SERIAL PRIMARY KEY,
  name            TEXT                     NOT NULL,
  bio             TEXT,
  email           TEXT UNIQUE              NOT NULL,
  password_hash   TEXT                     NOT NULL,
  location        TEXT,
  photo_url       TEXT,
  is_public       BOOLEAN      DEFAULT TRUE,
  availability    TEXT[]       DEFAULT ARRAY[]::TEXT[],   -- e.g. {'weekends','evenings'}
  created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE TABLE skills (
  id        SERIAL PRIMARY KEY,
  name      TEXT        NOT NULL,
  category  TEXT        NOT NULL             -- e.g. 'Software', 'Art', 'Language'
);
CREATE UNIQUE INDEX idx_skill_name ON skills (LOWER(name));

CREATE TABLE user_skills (
  id        SERIAL PRIMARY KEY,
  user_id   INT  REFERENCES users(id)      ON DELETE CASCADE,
  skill_id  INT  REFERENCES skills(id)     ON DELETE CASCADE,
  role      TEXT CHECK (role IN ('offered','wanted')),
  description TEXT,                        -- optional extra context
  CONSTRAINT uniq_user_skill UNIQUE (user_id, skill_id, role)
);

CREATE TABLE swaps (
  id                SERIAL PRIMARY KEY,
  from_user_id      INT REFERENCES users(id),
  to_user_id        INT REFERENCES users(id),
  skill_offered_us  INT REFERENCES user_skills(id),  -- what sender offers
  skill_requested_us INT REFERENCES user_skills(id), -- what sender wants
  status            TEXT
        CHECK (status IN ('pending','accepted','rejected','cancelled')),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_swaps_status ON swaps (status);

CREATE TABLE feedback (
  id          SERIAL PRIMARY KEY,
  swap_id     INT REFERENCES swaps(id) ON DELETE CASCADE,
  from_user   INT REFERENCES users(id),
  rating      INT  CHECK (rating BETWEEN 1 AND 5),
  comment     TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE admin_logs (
  id           SERIAL PRIMARY KEY,
  entity_type  TEXT,            -- 'skill','swap','user', etc.
  entity_id    INT,
  action       TEXT,            -- 'flag','ban','delete'
  reason       TEXT,
  admin_id     INT,             -- who did it
  logged_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Insert some sample skills
INSERT INTO skills (name, category) VALUES
('JavaScript', 'Software'),
('Python', 'Software'),
('React', 'Software'),
('Node.js', 'Software'),
('Guitar', 'Music'),
('Piano', 'Music'),
('Spanish', 'Language'),
('French', 'Language'),
('Cooking', 'Lifestyle'),
('Photography', 'Art'),
('Drawing', 'Art'),
('Yoga', 'Fitness'),
('Swimming', 'Fitness'),
('Chess', 'Games'),
('Gardening', 'Lifestyle'); 