-- =============================================================================
-- FELLOW BOT — Safe Migration from Legacy Schema
-- Renames old tables to _legacy_ prefix, then applies new schema
-- Existing data is preserved in _legacy_ tables
-- =============================================================================

-- Step 1: Rename conflicting old tables to _legacy_ prefix
ALTER TABLE IF EXISTS ai_providers     RENAME TO _legacy_ai_providers;
ALTER TABLE IF EXISTS conversations    RENAME TO _legacy_conversations;
ALTER TABLE IF EXISTS ai_entities      RENAME TO _legacy_ai_entities;
ALTER TABLE IF EXISTS ai_knowledge     RENAME TO _legacy_ai_knowledge;
ALTER TABLE IF EXISTS clients          RENAME TO _legacy_clients;
ALTER TABLE IF EXISTS data_sources     RENAME TO _legacy_data_sources;
ALTER TABLE IF EXISTS entity_types     RENAME TO _legacy_entity_types;
ALTER TABLE IF EXISTS sync_logs        RENAME TO _legacy_sync_logs;
