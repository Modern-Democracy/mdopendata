DO $$
DECLARE
  project_table record;
BEGIN
  FOR project_table IN
    SELECT n.nspname AS schema_name, c.relname AS table_name
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname IN ('public', 'zoning', 'budget', 'council', 'help')
      AND c.relkind IN ('r', 'p')
    ORDER BY n.nspname, c.relname
  LOOP
    EXECUTE format(
      'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
      project_table.schema_name,
      project_table.table_name
    );
  END LOOP;
END $$;
