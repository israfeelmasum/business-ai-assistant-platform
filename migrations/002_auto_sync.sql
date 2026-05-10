-- ============================================
-- Migration 002: Auto-Sync Integration System
-- Enables pull-based data sync from external APIs
-- ============================================

-- Data Source Configuration Table
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    api_url TEXT NOT NULL,
    auth_type VARCHAR(20) NOT NULL DEFAULT 'none',
    auth_config JSONB DEFAULT '{}',
    request_headers JSONB DEFAULT '{}',
    pagination_type VARCHAR(20) DEFAULT 'none',
    pagination_config JSONB DEFAULT '{}',
    data_path VARCHAR(255) DEFAULT '',
    id_field VARCHAR(255) DEFAULT 'id',
    field_mapping JSONB DEFAULT '{}',
    sync_interval_minutes INT DEFAULT 30,
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(client_id, name)
);

-- Sync Logs Table
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE,
    total_fetched INT DEFAULT 0,
    created_count INT DEFAULT 0,
    updated_count INT DEFAULT 0,
    skipped_count INT DEFAULT 0,
    deleted_count INT DEFAULT 0,
    error_count INT DEFAULT 0,
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add data_hash column to ai_entities for change detection
ALTER TABLE ai_entities ADD COLUMN IF NOT EXISTS data_hash VARCHAR(64);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_data_sources_client_id ON data_sources(client_id);
CREATE INDEX IF NOT EXISTS idx_data_sources_active ON data_sources(is_active, last_synced_at);
CREATE INDEX IF NOT EXISTS idx_sync_logs_data_source_id ON sync_logs(data_source_id);
CREATE INDEX IF NOT EXISTS idx_sync_logs_client_id ON sync_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_ai_entities_data_hash ON ai_entities(data_hash);
