-- Baseline schema migration
-- This marks the baseline schema version for databases created with the initial schema
-- For new databases, this is a no-op since create_schema() handles everything
-- For existing databases, all tables and columns should already exist

-- This is a marker migration that establishes version 1
SELECT 1;
