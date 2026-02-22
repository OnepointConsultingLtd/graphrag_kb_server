-- Migration: Add DOCUMENT_IMAGE and DOCUMENT_LINKS columns to TB_SEARCH_RESULTS
-- Date: 2026-02-16
-- Description: Adds image path and document links fields to search results.
--
-- This script finds all schemas that contain a TB_SEARCH_RESULTS table
-- and adds the new columns if they don't already exist.

DO $$
DECLARE
    schema_rec RECORD;
BEGIN
    FOR schema_rec IN
        SELECT DISTINCT table_schema
        FROM information_schema.tables
        WHERE table_name = 'tb_search_results'
    LOOP
        -- Add DOCUMENT_IMAGE column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.table_schema
              AND table_name = 'tb_search_results'
              AND column_name = 'document_image'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.tb_search_results ADD COLUMN document_image CHARACTER VARYING(8192) NULL',
                schema_rec.table_schema
            );
            RAISE NOTICE 'Added DOCUMENT_IMAGE to %.tb_search_results', schema_rec.table_schema;
        END IF;

        -- Add DOCUMENT_LINKS column if it doesn't exist
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = schema_rec.table_schema
              AND table_name = 'tb_search_results'
              AND column_name = 'document_links'
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I.tb_search_results ADD COLUMN document_links TEXT[] NULL',
                schema_rec.table_schema
            );
            RAISE NOTICE 'Added DOCUMENT_LINKS to %.tb_search_results', schema_rec.table_schema;
        END IF;
    END LOOP;
END
$$;
