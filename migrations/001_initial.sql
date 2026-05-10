-- ============================================================================
-- AI Chatbot Service - Initial Migration
-- ============================================================================
-- Requires: PostgreSQL 15+ with pgvector extension
-- Run: psql -U postgres -d ai_chatbot -f migrations/001_initial.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- 1. AI PROVIDERS - Global registry of supported AI models
-- ============================================================================
CREATE TABLE ai_providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    model_name VARCHAR(100) NOT NULL,
    provider_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- 2. CLIENTS - Registered external systems
-- ============================================================================
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) NOT NULL UNIQUE,
    api_secret VARCHAR(255) NOT NULL,
    provider_id UUID REFERENCES ai_providers(id),
    config JSONB NOT NULL DEFAULT '{}',
    welcome_message TEXT DEFAULT 'Hello! How can I help you today?',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clients_api_key ON clients(api_key);

-- ============================================================================
-- 3. ENTITY TYPES - Per-client data categories (auto-created on first sync)
-- ============================================================================
CREATE TABLE entity_types (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    icon VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(client_id, name)
);

CREATE INDEX idx_entity_types_client ON entity_types(client_id);

-- ============================================================================
-- 4. AI ENTITIES - Raw synced data from external systems
-- ============================================================================
CREATE TABLE ai_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    entity_type_id UUID NOT NULL REFERENCES entity_types(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(client_id, entity_type_id, external_id)
);

CREATE INDEX idx_ai_entities_client ON ai_entities(client_id);
CREATE INDEX idx_ai_entities_type ON ai_entities(entity_type_id);
CREATE INDEX idx_ai_entities_external ON ai_entities(client_id, external_id);

-- ============================================================================
-- 5. AI KNOWLEDGE - Embeddings + summaries for semantic search (pgvector)
-- ============================================================================
CREATE TABLE ai_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES ai_entities(id) ON DELETE CASCADE,
    entity_type_id UUID NOT NULL REFERENCES entity_types(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    embedding vector(768), -- Updated to 768 for Ollama's nomic-embed-text
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_knowledge_client ON ai_knowledge(client_id);
CREATE INDEX idx_ai_knowledge_entity ON ai_knowledge(entity_id);
CREATE INDEX idx_ai_knowledge_type ON ai_knowledge(entity_type_id);

-- HNSW index for fast vector similarity search
CREATE INDEX idx_ai_knowledge_embedding ON ai_knowledge
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- 6. CONVERSATIONS - Chat history with embedded user info & Human Handover
-- ============================================================================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    session_id VARCHAR(255) NOT NULL,
    user_phone VARCHAR(50), -- Added for user identification
    user_info JSONB NOT NULL DEFAULT '{}',
    messages JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- Added for Human Handover logic
    selected_entity_type_id UUID REFERENCES entity_types(id),
    metadata JSONB NOT NULL DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_client ON conversations(client_id);
CREATE INDEX idx_conversations_session ON conversations(client_id, session_id);
CREATE INDEX idx_conversations_status ON conversations(status);

-- ============================================================================
-- Seed default AI providers (including Ollama)
-- ============================================================================
INSERT INTO ai_providers (name, model_name, provider_type, config) VALUES
    ('OpenAI GPT-4o Mini', 'gpt-4o-mini', 'openai', '{"temperature": 0.7}'),
    ('OpenAI GPT-4o', 'gpt-4o', 'openai', '{"temperature": 0.7}'),
    ('Gemini 1.5 Flash', 'gemini-1.5-flash', 'google', '{"temperature": 0.7}'),
    ('Gemini 1.5 Pro', 'gemini-1.5-pro', 'google', '{"temperature": 0.7}'),
    ('Ollama Llama 3.2', 'llama3.2:latest', 'ollama', '{"temperature": 0.7}'),
    ('Ollama Mistral', 'mistral', 'ollama', '{"temperature": 0.7}'),
    ('Ollama Qwen2', 'qwen2', 'ollama', '{"temperature": 0.7}');