-- Signal: Promotion - Change title columns to JSONB arrays
-- Store full arrays instead of just first element

ALTER TABLE extracted.signal_promotion
    DROP COLUMN IF EXISTS new_title,
    DROP COLUMN IF EXISTS previous_title;

ALTER TABLE extracted.signal_promotion
    ADD COLUMN new_titles JSONB,
    ADD COLUMN previous_titles JSONB;

COMMENT ON COLUMN extracted.signal_promotion.new_titles IS 'Array of new titles from payload';
COMMENT ON COLUMN extracted.signal_promotion.previous_titles IS 'Array of previous titles from payload';
