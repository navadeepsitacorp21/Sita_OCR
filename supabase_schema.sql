-- ==============================================================================
-- ABP Medical Report & Biomarker Schema for Supabase PostgreSQL
-- (Structured Extracted Data Only - No File/Binary Storage)
-- ==============================================================================

-- 1. Enable UUID Extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Medical Reports Table
CREATE TABLE IF NOT EXISTS medical_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    report_type VARCHAR(64) NOT NULL,
    report_date VARCHAR(64),
    collection_date VARCHAR(64),
    reported_date VARCHAR(64),
    ocr_status VARCHAR(32) NOT NULL DEFAULT 'completed',
    page_count INTEGER NOT NULL DEFAULT 1,
    overall_status VARCHAR(64) DEFAULT 'normal',
    abnormal_count INTEGER DEFAULT 0,
    analyzed_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- Indexes for medical_reports
CREATE INDEX IF NOT EXISTS idx_medical_reports_user_id ON medical_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_medical_reports_user_date ON medical_reports(user_id, report_date);
CREATE INDEX IF NOT EXISTS idx_medical_reports_created ON medical_reports(created_at DESC);

-- 3. Biomarkers Table
CREATE TABLE IF NOT EXISTS biomarkers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    report_id UUID NOT NULL REFERENCES medical_reports(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    value NUMERIC,
    unit VARCHAR(64),
    reference_min NUMERIC,
    reference_max NUMERIC,
    reference_text TEXT,
    status VARCHAR(64) DEFAULT 'normal',
    reference_source VARCHAR(64) DEFAULT 'report',
    confidence NUMERIC DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- Indexes for biomarkers
CREATE INDEX IF NOT EXISTS idx_biomarkers_user_id ON biomarkers(user_id);
CREATE INDEX IF NOT EXISTS idx_biomarkers_report_id ON biomarkers(report_id);
CREATE INDEX IF NOT EXISTS idx_biomarkers_user_name ON biomarkers(user_id, name);

-- 4. Supabase Row Level Security (RLS)
ALTER TABLE medical_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE biomarkers ENABLE ROW LEVEL SECURITY;

-- Allow users to only view and manage their own reports
CREATE POLICY "Users can only access their own medical reports"
    ON medical_reports
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Allow users to only view and manage their own biomarkers
CREATE POLICY "Users can only access their own biomarkers"
    ON biomarkers
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Allow ABP Backend (service_role) full access to insert & query
CREATE POLICY "Service role full access on medical_reports"
    ON medical_reports
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on biomarkers"
    ON biomarkers
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
