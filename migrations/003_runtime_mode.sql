ALTER TABLE runs ADD COLUMN IF NOT EXISTS mode text NOT NULL DEFAULT 'offline';
ALTER TABLE runs ADD CONSTRAINT runtime_mode_valid CHECK(mode IN ('offline','paper','dev','live'));
