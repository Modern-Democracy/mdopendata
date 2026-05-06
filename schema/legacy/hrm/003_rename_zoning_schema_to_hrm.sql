DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.schemata
    WHERE schema_name = 'zoning'
  ) AND NOT EXISTS (
    SELECT 1
    FROM information_schema.schemata
    WHERE schema_name = 'hrm'
  ) THEN
    EXECUTE 'ALTER SCHEMA zoning RENAME TO hrm';
  END IF;
END $$;
