-- =============================================================================
-- FELLOW BOT PLATFORM — Complete Database Schema
-- Version: 1.0.0
-- Company: Fellowly Technology
-- All timestamps in UTC. pgvector required.
-- Run: psql -U postgres -d ai_chatbot_db -f 001_fellow_bot_schema.sql
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- SECTION 1: ENUMS
-- =============================================================================

CREATE TYPE user_role AS ENUM ('super_admin', 'org_admin', 'member', 'agent');
CREATE TYPE member_role AS ENUM ('admin', 'editor', 'viewer', 'agent');
CREATE TYPE plan_slug AS ENUM ('free', 'starter', 'professional', 'enterprise');
CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'cancelled', 'paused');
CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'refunded');
CREATE TYPE payment_gateway AS ENUM ('sslcommerz', 'bkash', 'nagad', 'rocket', 'stripe', 'paypal', 'zelle', 'bank_transfer', 'manual');
CREATE TYPE provider_type AS ENUM ('openai', 'anthropic', 'google', 'ollama', 'groq', 'mistral', 'custom');
CREATE TYPE model_capability AS ENUM ('chat', 'embedding', 'vision', 'tts', 'stt', 'translation');
CREATE TYPE provider_source AS ENUM ('platform', 'org_custom');
CREATE TYPE personality_type AS ENUM ('professional', 'friendly', 'formal', 'playful', 'empathetic');
CREATE TYPE domain_type AS ENUM ('general', 'medical', 'legal', 'tech', 'retail', 'education', 'finance', 'real_estate', 'hospitality');
CREATE TYPE fallback_behavior AS ENUM ('escalate', 'clarify', 'suggest', 'apologize');
CREATE TYPE prompt_layer AS ENUM ('foundation', 'tenant', 'contextual', 'guardrail');
CREATE TYPE deployment_channel AS ENUM ('web_widget', 'mobile_sdk', 'whatsapp', 'telegram', 'slack', 'rest_api', 'facebook');
CREATE TYPE source_type AS ENUM ('file_upload', 'url_crawl', 'api_sync', 'manual_entry', 'database_sync', 'sitemap');
CREATE TYPE document_status AS ENUM ('pending', 'processing', 'indexed', 'failed', 'outdated');
CREATE TYPE conversation_status AS ENUM ('active', 'resolved', 'human_escalated', 'abandoned', 'spam');
CREATE TYPE message_role AS ENUM ('user', 'assistant', 'system', 'agent');
CREATE TYPE message_type AS ENUM ('text', 'image', 'file', 'voice', 'form_submission', 'system_event');
CREATE TYPE escalation_trigger AS ENUM ('low_confidence', 'high_eil', 'user_requested', 'keyword_match', 'admin_manual');
CREATE TYPE escalation_status AS ENUM ('pending', 'active', 'resolved', 'timeout');
CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'waiting_client', 'resolved', 'closed');
CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE webhook_event AS ENUM (
    'conversation.started', 'conversation.ended', 'conversation.escalated',
    'message.received', 'message.sent',
    'escalation.triggered', 'escalation.resolved',
    'knowledge.synced', 'payment.completed', 'subscription.changed'
);
CREATE TYPE api_key_scope AS ENUM ('chat', 'admin', 'knowledge', 'analytics', 'full');
CREATE TYPE token_ledger_type AS ENUM ('credit', 'debit');
CREATE TYPE token_action AS ENUM ('chat_message', 'embedding', 'vision', 'tts', 'stt', 'translation', 'top_up', 'plan_credit', 'refund');

-- =============================================================================
-- SECTION 2: AUTH & IDENTITY
-- =============================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    avatar_url      TEXT,
    phone           VARCHAR(30),
    role            user_role NOT NULL DEFAULT 'member',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_sessions (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash  VARCHAR(255) NOT NULL UNIQUE,
    device_info         JSONB DEFAULT '{}',
    ip_address          INET,
    user_agent          TEXT,
    expires_at          TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 3: ORGANIZATIONS (TENANTS)
-- =============================================================================

CREATE TABLE organizations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(100) NOT NULL UNIQUE,
    logo_url            TEXT,
    favicon_url         TEXT,
    website             VARCHAR(255),
    email               VARCHAR(255),
    phone               VARCHAR(30),
    address             TEXT,
    country             VARCHAR(100),
    timezone            VARCHAR(100) NOT NULL DEFAULT 'UTC',
    default_language    VARCHAR(10) NOT NULL DEFAULT 'en',
    custom_domain       VARCHAR(255),
    -- Branding
    brand_color_primary     VARCHAR(7) DEFAULT '#2563EB',
    brand_color_secondary   VARCHAR(7) DEFAULT '#7C3AED',
    brand_color_accent      VARCHAR(7) DEFAULT '#06B6D4',
    -- Legal
    privacy_policy_url  TEXT,
    terms_url           TEXT,
    -- Business hours (JSON: {"mon": {"open": "09:00", "close": "18:00"}, ...})
    business_hours      JSONB DEFAULT '{}',
    -- Settings
    settings            JSONB DEFAULT '{}',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE org_members (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        member_role NOT NULL DEFAULT 'viewer',
    invited_by  UUID REFERENCES users(id),
    joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chatbot_id      UUID,   -- FK added after chatbots table
    name            VARCHAR(100) NOT NULL,
    key_prefix      VARCHAR(10) NOT NULL,
    key_hash        VARCHAR(255) NOT NULL UNIQUE,
    scopes          api_key_scope[] NOT NULL DEFAULT '{chat}',
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 4: SUBSCRIPTIONS & BILLING
-- =============================================================================

CREATE TABLE plans (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                    VARCHAR(100) NOT NULL,
    slug                    plan_slug NOT NULL UNIQUE,
    description             TEXT,
    price_monthly           DECIMAL(10,2) NOT NULL DEFAULT 0,
    price_annual            DECIMAL(10,2) NOT NULL DEFAULT 0,
    -- Limits (NULL = unlimited)
    max_chatbots            INT,
    max_messages_per_month  INT,
    max_tokens_per_month    BIGINT,
    max_team_members        INT,
    max_knowledge_mb        INT,
    max_documents           INT,
    max_api_calls_per_day   INT,
    max_concurrent_users    INT,
    max_agent_seats         INT,
    -- Features (boolean flags)
    features                JSONB NOT NULL DEFAULT '{}',
    -- e.g. {"byok": true, "vision": true, "tts": false, "analytics": true,
    --        "webhooks": true, "custom_domain": false, "white_label": false,
    --        "priority_support": false, "sla_guarantee": false}
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order              INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id                      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id                     UUID NOT NULL REFERENCES plans(id),
    status                      subscription_status NOT NULL DEFAULT 'trialing',
    billing_cycle               VARCHAR(10) NOT NULL DEFAULT 'monthly', -- monthly | annual
    current_period_start        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    current_period_end          TIMESTAMPTZ NOT NULL,
    trial_ends_at               TIMESTAMPTZ,
    cancelled_at                TIMESTAMPTZ,
    cancel_reason               TEXT,
    external_subscription_id    VARCHAR(255),   -- Stripe subscription ID etc.
    metadata                    JSONB DEFAULT '{}',
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id)
);

CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id),
    invoice_number  VARCHAR(50) NOT NULL UNIQUE,
    amount          DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    status          payment_status NOT NULL DEFAULT 'pending',
    due_date        TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    pdf_url         TEXT,
    line_items      JSONB NOT NULL DEFAULT '[]',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE payments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id          UUID REFERENCES invoices(id),
    gateway             payment_gateway NOT NULL,
    amount              DECIMAL(10,2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    status              payment_status NOT NULL DEFAULT 'pending',
    -- Gateway-specific
    gateway_txn_id      VARCHAR(255),
    gateway_response    JSONB DEFAULT '{}',
    payment_proof_url   TEXT,   -- for manual/bank transfer
    -- Metadata
    payer_name          VARCHAR(255),
    payer_email         VARCHAR(255),
    payer_phone         VARCHAR(30),
    notes               TEXT,
    processed_by        UUID REFERENCES users(id),
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 5: TOKEN SYSTEM
-- =============================================================================

CREATE TABLE token_packages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) NOT NULL,
    tokens          BIGINT NOT NULL,
    price           DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    bonus_tokens    BIGINT NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE token_ledger (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chatbot_id      UUID,   -- FK added after chatbots table (nullable = org-level)
    type            token_ledger_type NOT NULL,
    action          token_action NOT NULL,
    tokens          BIGINT NOT NULL,
    balance_after   BIGINT NOT NULL,
    reference_id    UUID,   -- message_id, payment_id etc.
    model_used      VARCHAR(100),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE usage_records (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chatbot_id              UUID,   -- FK added after chatbots table
    period_year             INT NOT NULL,
    period_month            INT NOT NULL,
    messages_count          BIGINT NOT NULL DEFAULT 0,
    tokens_used             BIGINT NOT NULL DEFAULT 0,
    storage_bytes_used      BIGINT NOT NULL DEFAULT 0,
    api_calls_count         BIGINT NOT NULL DEFAULT 0,
    vision_calls_count      BIGINT NOT NULL DEFAULT 0,
    tts_calls_count         BIGINT NOT NULL DEFAULT 0,
    stt_calls_count         BIGINT NOT NULL DEFAULT 0,
    translation_calls_count BIGINT NOT NULL DEFAULT 0,
    unique_users_count      INT NOT NULL DEFAULT 0,
    escalations_count       INT NOT NULL DEFAULT 0,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, chatbot_id, period_year, period_month)
);

-- =============================================================================
-- SECTION 6: AI PROVIDERS
-- =============================================================================

CREATE TABLE ai_providers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) NOT NULL,
    provider_type   provider_type NOT NULL,
    base_url        TEXT,
    -- Encrypted API key (platform-level, managed by Fellowly)
    api_key_enc     TEXT,
    -- Default configs
    config          JSONB DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_provider_models (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id     UUID NOT NULL REFERENCES ai_providers(id) ON DELETE CASCADE,
    model_id        VARCHAR(100) NOT NULL,
    display_name    VARCHAR(150) NOT NULL,
    capability      model_capability NOT NULL,
    context_window  INT,
    max_tokens      INT,
    -- Cost per 1M tokens (for platform usage metering)
    cost_input_per_1m   DECIMAL(10,6) DEFAULT 0,
    cost_output_per_1m  DECIMAL(10,6) DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INT NOT NULL DEFAULT 0,
    UNIQUE(provider_id, model_id, capability)
);

CREATE TABLE org_ai_providers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    provider_type   provider_type NOT NULL,
    base_url        TEXT,
    api_key_enc     TEXT NOT NULL,   -- Encrypted with platform secret
    config          JSONB DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 7: CHATBOTS
-- =============================================================================

CREATE TABLE chatbots (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) NOT NULL,
    description     TEXT,
    avatar_url      TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_published    BOOLEAN NOT NULL DEFAULT FALSE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, slug)
);

-- Add FK from api_keys and token_ledger to chatbots
ALTER TABLE api_keys ADD CONSTRAINT fk_api_keys_chatbot
    FOREIGN KEY (chatbot_id) REFERENCES chatbots(id) ON DELETE SET NULL;

ALTER TABLE token_ledger ADD CONSTRAINT fk_token_ledger_chatbot
    FOREIGN KEY (chatbot_id) REFERENCES chatbots(id) ON DELETE SET NULL;

ALTER TABLE usage_records ADD CONSTRAINT fk_usage_records_chatbot
    FOREIGN KEY (chatbot_id) REFERENCES chatbots(id) ON DELETE SET NULL;

CREATE TABLE chatbot_model_config (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id      UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    task            model_capability NOT NULL,
    provider_source provider_source NOT NULL DEFAULT 'platform',
    -- Either platform provider or org custom provider (one must be set)
    provider_id         UUID REFERENCES ai_providers(id) ON DELETE SET NULL,
    org_provider_id     UUID REFERENCES org_ai_providers(id) ON DELETE SET NULL,
    model_id            VARCHAR(100) NOT NULL,
    parameters          JSONB DEFAULT '{"temperature": 0.7, "max_tokens": 1024}',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(chatbot_id, task)
);

CREATE TABLE chatbot_personas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id      UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    persona_name    VARCHAR(100) NOT NULL DEFAULT 'Assistant',
    personality     personality_type NOT NULL DEFAULT 'professional',
    domain          domain_type NOT NULL DEFAULT 'general',
    default_language    VARCHAR(10) NOT NULL DEFAULT 'en',
    supported_languages VARCHAR(10)[] NOT NULL DEFAULT '{en}',
    greeting_message    TEXT,
    farewell_message    TEXT,
    offline_message     TEXT,
    fallback_behavior   fallback_behavior NOT NULL DEFAULT 'escalate',
    -- Voice config (future TTS/STT)
    voice_id        VARCHAR(100),
    voice_speed     DECIMAL(3,1) DEFAULT 1.0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    version         INT NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chatbot_prompts (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id  UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    layer       prompt_layer NOT NULL,
    name        VARCHAR(150) NOT NULL,
    content     TEXT NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    version     INT NOT NULL DEFAULT 1,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chatbot_guardrails (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id  UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    name        VARCHAR(150) NOT NULL,
    rule_type   VARCHAR(50) NOT NULL,
    -- e.g. 'topic_restriction', 'mandatory_disclaimer', 'keyword_block',
    --      'escalation_trigger', 'confidence_threshold', 'eil_threshold'
    rule_config JSONB NOT NULL DEFAULT '{}',
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chatbot_deployments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id  UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    channel     deployment_channel NOT NULL,
    name        VARCHAR(100),
    config      JSONB DEFAULT '{}',
    -- e.g. for web_widget: {"allowed_domains": [], "position": "bottom-right"}
    -- e.g. for whatsapp: {"phone_number_id": "...", "verify_token": "..."}
    api_key_id  UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(chatbot_id, channel)
);

CREATE TABLE chatbot_themes (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id              UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    -- Colors
    color_primary           VARCHAR(7) DEFAULT '#2563EB',
    color_secondary         VARCHAR(7) DEFAULT '#7C3AED',
    color_accent            VARCHAR(7) DEFAULT '#06B6D4',
    color_background        VARCHAR(7) DEFAULT '#FFFFFF',
    color_text              VARCHAR(7) DEFAULT '#111827',
    color_user_bubble       VARCHAR(7) DEFAULT '#2563EB',
    color_bot_bubble        VARCHAR(7) DEFAULT '#F3F4F6',
    -- Typography
    font_family             VARCHAR(100) DEFAULT 'Inter',
    font_size_base          INT DEFAULT 14,
    -- Layout
    border_radius           INT DEFAULT 12,
    widget_width            INT DEFAULT 380,
    widget_height           INT DEFAULT 600,
    position                VARCHAR(20) DEFAULT 'bottom-right',
    -- Dark mode
    dark_mode_enabled       BOOLEAN DEFAULT FALSE,
    dark_color_background   VARCHAR(7) DEFAULT '#1F2937',
    dark_color_text         VARCHAR(7) DEFAULT '#F9FAFB',
    -- Custom CSS override
    custom_css              TEXT,
    -- RTL
    rtl_enabled             BOOLEAN DEFAULT FALSE,
    -- Template
    template_name           VARCHAR(50) DEFAULT 'modern',
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prechat form config
CREATE TABLE chatbot_prechat_forms (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id  UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    is_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    title       VARCHAR(255) DEFAULT 'Before we start...',
    message     TEXT,
    fields      JSONB NOT NULL DEFAULT '[]',
    -- e.g. [{"key":"name","type":"text","label":"Full Name","required":true},
    --        {"key":"email","type":"email","label":"Email","required":false}]
    remember_user   BOOLEAN DEFAULT TRUE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 8: KNOWLEDGE BASE
-- =============================================================================

CREATE TABLE knowledge_bases (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id      UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE knowledge_sources (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id       UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_type             source_type NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    -- API sync config
    api_url                 TEXT,
    auth_type               VARCHAR(30),
    auth_config             JSONB DEFAULT '{}',
    pagination_config       JSONB DEFAULT '{}',
    field_mapping           JSONB DEFAULT '{}',
    data_path               VARCHAR(100),
    id_field                VARCHAR(50) DEFAULT 'id',
    -- URL crawl config
    crawl_url               TEXT,
    crawl_depth             INT DEFAULT 2,
    crawl_include_patterns  TEXT[],
    crawl_exclude_patterns  TEXT[],
    -- Sync schedule
    sync_interval_minutes   INT DEFAULT 720,
    last_synced_at          TIMESTAMPTZ,
    next_sync_at            TIMESTAMPTZ,
    -- Status
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE knowledge_documents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id   UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    source_id           UUID REFERENCES knowledge_sources(id) ON DELETE SET NULL,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title               VARCHAR(500),
    content_type        VARCHAR(50),  -- 'pdf', 'docx', 'txt', 'csv', 'json', 'html', 'manual'
    content_hash        VARCHAR(64),  -- SHA256 for change detection
    raw_content         TEXT,
    file_url            TEXT,
    file_size_bytes     BIGINT,
    external_id         VARCHAR(255), -- ID from external API
    status              document_status NOT NULL DEFAULT 'pending',
    error_message       TEXT,
    metadata            JSONB DEFAULT '{}',
    chunk_count         INT DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE knowledge_chunks (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id         UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    knowledge_base_id   UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    content             TEXT NOT NULL,
    chunk_index         INT NOT NULL,
    token_count         INT,
    embedding           vector(1536),
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE knowledge_sync_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id           UUID NOT NULL REFERENCES knowledge_sources(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    status              VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    -- Stats
    docs_created        INT DEFAULT 0,
    docs_updated        INT DEFAULT 0,
    docs_deleted        INT DEFAULT 0,
    docs_skipped        INT DEFAULT 0,
    docs_failed         INT DEFAULT 0,
    chunks_created      INT DEFAULT 0,
    -- Errors
    errors              JSONB DEFAULT '[]'
);

-- Q&A pairs (direct training, bypass full RAG)
CREATE TABLE knowledge_qa_pairs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    knowledge_base_id   UUID NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    question            TEXT NOT NULL,
    answer              TEXT NOT NULL,
    embedding           vector(1536),
    tags                TEXT[],
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 9: CONVERSATIONS & MESSAGES
-- =============================================================================

CREATE TABLE end_users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chatbot_id      UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    -- Identity (may be anonymous)
    external_id     VARCHAR(255),   -- device fingerprint or user ID from client system
    name            VARCHAR(255),
    email           VARCHAR(255),
    phone           VARCHAR(30),
    -- Profile built over time
    language        VARCHAR(10),
    timezone        VARCHAR(100),
    metadata        JSONB DEFAULT '{}',
    -- Long-term memory vector profile
    profile_embedding   vector(1536),
    profile_summary     TEXT,
    -- Stats
    total_conversations INT NOT NULL DEFAULT 0,
    last_seen_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, chatbot_id, external_id)
);

CREATE TABLE conversations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id          UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    end_user_id         UUID REFERENCES end_users(id) ON DELETE SET NULL,
    session_id          VARCHAR(100) NOT NULL,
    channel             deployment_channel NOT NULL DEFAULT 'web_widget',
    status              conversation_status NOT NULL DEFAULT 'active',
    language_detected   VARCHAR(10),
    -- User info snapshot at conversation start
    user_info           JSONB DEFAULT '{}',
    -- Form data collected by prechat form
    prechat_data        JSONB DEFAULT '{}',
    -- Assigned human agent (when escalated)
    assigned_agent_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    -- Stats
    message_count       INT NOT NULL DEFAULT 0,
    user_message_count  INT NOT NULL DEFAULT 0,
    -- Timing
    first_response_ms   INT,    -- time to first AI response
    resolved_at         TIMESTAMPTZ,
    last_message_at     TIMESTAMPTZ,
    metadata            JSONB DEFAULT '{}',
    -- UTM / tracking
    utm_source          VARCHAR(100),
    utm_medium          VARCHAR(100),
    referrer_url        TEXT,
    user_agent          TEXT,
    ip_address          INET,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role            message_role NOT NULL,
    type            message_type NOT NULL DEFAULT 'text',
    content         TEXT,
    -- Attachments: images, files, voice
    attachments     JSONB DEFAULT '[]',
    -- AI metadata (for assistant messages)
    model_used      VARCHAR(100),
    tokens_input    INT,
    tokens_output   INT,
    latency_ms      INT,
    confidence      DECIMAL(4,3),
    eil_score       DECIMAL(4,3),
    intent          VARCHAR(100),
    -- RAG sources used
    rag_sources     JSONB DEFAULT '[]',
    -- Suggestions shown to user
    suggestions     TEXT[],
    -- CTA / action card
    action_data     JSONB,
    -- Trace for audit
    trace_id        UUID DEFAULT uuid_generate_v4(),
    -- Sent by human agent (when in escalation)
    agent_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE escalations (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    trigger             escalation_trigger NOT NULL,
    trigger_details     JSONB DEFAULT '{}',
    status              escalation_status NOT NULL DEFAULT 'pending',
    -- Assigned agent
    assigned_agent_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    assigned_at         TIMESTAMPTZ,
    -- SLA
    sla_minutes         INT DEFAULT 30,
    sla_deadline        TIMESTAMPTZ,
    -- Resolution
    resolved_at         TIMESTAMPTZ,
    resolved_by         UUID REFERENCES users(id),
    resolution_notes    TEXT,
    -- Notification
    admin_notified_at   TIMESTAMPTZ,
    admin_notified_via  VARCHAR(50),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE message_reactions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id      UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    reaction        VARCHAR(20) NOT NULL,   -- 'thumbs_up', 'thumbs_down', 'flag'
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE canned_responses (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chatbot_id  UUID REFERENCES chatbots(id) ON DELETE CASCADE,
    title       VARCHAR(200) NOT NULL,
    content     TEXT NOT NULL,
    tags        TEXT[],
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 10: ANALYTICS & AUDIT
-- =============================================================================

CREATE TABLE ai_decision_logs (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trace_id                UUID NOT NULL,
    message_id              UUID REFERENCES messages(id) ON DELETE SET NULL,
    conversation_id         UUID REFERENCES conversations(id) ON DELETE CASCADE,
    chatbot_id              UUID REFERENCES chatbots(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    -- Full audit snapshot
    system_prompt_snapshot  TEXT,
    retrieved_context       JSONB DEFAULT '[]',
    user_message            TEXT,
    ai_response             TEXT,
    -- Model info
    model_used              VARCHAR(100),
    provider_type           VARCHAR(50),
    tokens_input            INT,
    tokens_output           INT,
    -- Intelligence scores
    confidence              DECIMAL(4,3),
    eil_score               DECIMAL(4,3),
    intent                  VARCHAR(100),
    -- Performance
    vector_search_ms        INT,
    llm_ttft_ms             INT,
    total_latency_ms        INT,
    -- Flags
    was_escalated           BOOLEAN DEFAULT FALSE,
    was_hallucination_risk  BOOLEAN DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 90-day retention policy (managed by pg_cron or app-level cleanup)
CREATE INDEX idx_ai_decision_logs_created ON ai_decision_logs(created_at);

CREATE TABLE chatbot_analytics_daily (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chatbot_id              UUID NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    org_id                  UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    date                    DATE NOT NULL,
    -- Volume
    total_conversations     INT DEFAULT 0,
    new_conversations       INT DEFAULT 0,
    total_messages          INT DEFAULT 0,
    -- Quality
    avg_confidence          DECIMAL(4,3),
    avg_eil_score           DECIMAL(4,3),
    avg_response_ms         INT,
    -- Outcomes
    resolved_count          INT DEFAULT 0,
    escalated_count         INT DEFAULT 0,
    abandoned_count         INT DEFAULT 0,
    -- Users
    unique_users            INT DEFAULT 0,
    returning_users         INT DEFAULT 0,
    -- Tokens
    tokens_used             BIGINT DEFAULT 0,
    UNIQUE(chatbot_id, date)
);

-- =============================================================================
-- SECTION 11: WEBHOOKS
-- =============================================================================

CREATE TABLE webhooks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    chatbot_id      UUID REFERENCES chatbots(id) ON DELETE CASCADE,
    name            VARCHAR(150) NOT NULL,
    url             TEXT NOT NULL,
    events          webhook_event[] NOT NULL,
    secret_hash     VARCHAR(255),
    headers         JSONB DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at   TIMESTAMPTZ,
    failure_count       INT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE webhook_deliveries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    webhook_id      UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event           webhook_event NOT NULL,
    payload         JSONB NOT NULL,
    response_status INT,
    response_body   TEXT,
    duration_ms     INT,
    success         BOOLEAN NOT NULL DEFAULT FALSE,
    retries         INT DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 12: SUPPORT SYSTEM
-- =============================================================================

CREATE TABLE support_tickets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES users(id),
    assigned_to     UUID REFERENCES users(id),
    subject         VARCHAR(500) NOT NULL,
    status          ticket_status NOT NULL DEFAULT 'open',
    priority        ticket_priority NOT NULL DEFAULT 'medium',
    category        VARCHAR(100),
    -- Related context
    chatbot_id      UUID REFERENCES chatbots(id) ON DELETE SET NULL,
    -- AI handling
    ai_handled      BOOLEAN DEFAULT FALSE,
    ai_confidence   DECIMAL(4,3),
    escalated_at    TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE support_messages (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id   UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    role        message_role NOT NULL DEFAULT 'user',
    content     TEXT NOT NULL,
    attachments JSONB DEFAULT '[]',
    is_internal BOOLEAN DEFAULT FALSE,  -- internal note for agents only
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE announcements (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       VARCHAR(300) NOT NULL,
    content     TEXT NOT NULL,
    type        VARCHAR(30) DEFAULT 'info',  -- 'info', 'warning', 'maintenance', 'feature'
    target      VARCHAR(30) DEFAULT 'all',   -- 'all', 'plan:pro', 'plan:enterprise' etc.
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    starts_at   TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ,
    created_by  UUID REFERENCES users(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- SECTION 13: INDEXES
-- =============================================================================

-- Auth
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(refresh_token_hash);

-- Organizations
CREATE INDEX idx_org_members_org ON org_members(org_id);
CREATE INDEX idx_org_members_user ON org_members(user_id);
CREATE INDEX idx_api_keys_org ON api_keys(org_id);
CREATE INDEX idx_api_keys_chatbot ON api_keys(chatbot_id);

-- Subscriptions
CREATE INDEX idx_subscriptions_org ON subscriptions(org_id);
CREATE INDEX idx_invoices_org ON invoices(org_id);
CREATE INDEX idx_payments_org ON payments(org_id);

-- Token ledger
CREATE INDEX idx_token_ledger_org ON token_ledger(org_id);
CREATE INDEX idx_token_ledger_chatbot ON token_ledger(chatbot_id);
CREATE INDEX idx_token_ledger_created ON token_ledger(created_at);

-- Usage
CREATE INDEX idx_usage_records_org_period ON usage_records(org_id, period_year, period_month);

-- AI Providers
CREATE INDEX idx_chatbot_model_config_chatbot ON chatbot_model_config(chatbot_id);

-- Chatbots
CREATE INDEX idx_chatbots_org ON chatbots(org_id);
CREATE INDEX idx_chatbot_prompts_chatbot ON chatbot_prompts(chatbot_id, layer);

-- Knowledge Base
CREATE INDEX idx_knowledge_bases_chatbot ON knowledge_bases(chatbot_id);
CREATE INDEX idx_knowledge_documents_kb ON knowledge_documents(knowledge_base_id);
CREATE INDEX idx_knowledge_documents_status ON knowledge_documents(status);
CREATE INDEX idx_knowledge_chunks_kb ON knowledge_chunks(knowledge_base_id);
CREATE INDEX idx_knowledge_chunks_org ON knowledge_chunks(org_id);
CREATE INDEX idx_knowledge_qa_kb ON knowledge_qa_pairs(knowledge_base_id);

-- Vector search — HNSW index (core for RAG performance)
CREATE INDEX idx_knowledge_chunks_embedding ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (ef_construction = 200, m = 16);

CREATE INDEX idx_knowledge_qa_embedding ON knowledge_qa_pairs
    USING hnsw (embedding vector_cosine_ops)
    WITH (ef_construction = 200, m = 16);

CREATE INDEX idx_end_users_profile_embedding ON end_users
    USING hnsw (profile_embedding vector_cosine_ops)
    WITH (ef_construction = 100, m = 16);

-- Conversations
CREATE INDEX idx_conversations_chatbot ON conversations(chatbot_id);
CREATE INDEX idx_conversations_org ON conversations(org_id);
CREATE INDEX idx_conversations_session ON conversations(session_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX idx_end_users_org_chatbot ON end_users(org_id, chatbot_id);

-- Messages
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_org ON messages(org_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_trace ON messages(trace_id);

-- Escalations
CREATE INDEX idx_escalations_conversation ON escalations(conversation_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_org ON escalations(org_id);

-- Analytics
CREATE INDEX idx_chatbot_analytics_daily_chatbot ON chatbot_analytics_daily(chatbot_id, date DESC);
CREATE INDEX idx_ai_decision_logs_org ON ai_decision_logs(org_id, created_at DESC);
CREATE INDEX idx_ai_decision_logs_chatbot ON ai_decision_logs(chatbot_id, created_at DESC);
CREATE INDEX idx_ai_decision_logs_trace ON ai_decision_logs(trace_id);

-- Webhooks
CREATE INDEX idx_webhooks_org ON webhooks(org_id);
CREATE INDEX idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id);

-- Support
CREATE INDEX idx_support_tickets_org ON support_tickets(org_id);
CREATE INDEX idx_support_tickets_status ON support_tickets(status);
CREATE INDEX idx_support_messages_ticket ON support_messages(ticket_id);

-- Knowledge sync
CREATE INDEX idx_knowledge_sources_next_sync ON knowledge_sources(next_sync_at)
    WHERE is_active = TRUE;

-- =============================================================================
-- SECTION 14: DEFAULT DATA — PLANS
-- =============================================================================

INSERT INTO plans (name, slug, description, price_monthly, price_annual,
    max_chatbots, max_messages_per_month, max_tokens_per_month,
    max_team_members, max_knowledge_mb, max_documents,
    max_api_calls_per_day, max_concurrent_users, max_agent_seats, features, sort_order)
VALUES
(
    'Free', 'free', 'Perfect for trying out Fellow BOT',
    0, 0,
    1, 500, 1000000,
    1, 50, 50,
    100, 10, 0,
    '{"byok": false, "vision": false, "tts": false, "stt": false,
      "analytics": false, "webhooks": false, "custom_domain": false,
      "white_label": false, "priority_support": false,
      "a_b_testing": false, "remove_branding": false}',
    1
),
(
    'Starter', 'starter', 'For small businesses getting started',
    29, 290,
    3, 5000, 10000000,
    5, 500, 500,
    1000, 50, 1,
    '{"byok": false, "vision": true, "tts": false, "stt": false,
      "analytics": true, "webhooks": true, "custom_domain": false,
      "white_label": false, "priority_support": false,
      "a_b_testing": false, "remove_branding": false}',
    2
),
(
    'Professional', 'professional', 'For growing businesses',
    99, 990,
    10, 50000, 100000000,
    20, 5000, 5000,
    10000, 500, 5,
    '{"byok": true, "vision": true, "tts": true, "stt": true,
      "analytics": true, "webhooks": true, "custom_domain": true,
      "white_label": false, "priority_support": true,
      "a_b_testing": true, "remove_branding": true}',
    3
),
(
    'Enterprise', 'enterprise', 'Unlimited scale for large organizations',
    299, 2990,
    NULL, NULL, NULL,
    NULL, NULL, NULL,
    NULL, NULL, NULL,
    '{"byok": true, "vision": true, "tts": true, "stt": true,
      "analytics": true, "webhooks": true, "custom_domain": true,
      "white_label": true, "priority_support": true,
      "a_b_testing": true, "remove_branding": true,
      "dedicated_support": true, "sla_guarantee": true,
      "custom_contract": true}',
    4
);

-- =============================================================================
-- SECTION 15: UPDATED_AT TRIGGERS
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_organizations_updated BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_subscriptions_updated BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_invoices_updated BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_payments_updated BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_plans_updated BEFORE UPDATE ON plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_org_ai_providers_updated BEFORE UPDATE ON org_ai_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_ai_providers_updated BEFORE UPDATE ON ai_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_chatbots_updated BEFORE UPDATE ON chatbots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_chatbot_personas_updated BEFORE UPDATE ON chatbot_personas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_chatbot_prompts_updated BEFORE UPDATE ON chatbot_prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_chatbot_deployments_updated BEFORE UPDATE ON chatbot_deployments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_chatbot_themes_updated BEFORE UPDATE ON chatbot_themes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_knowledge_bases_updated BEFORE UPDATE ON knowledge_bases
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_knowledge_sources_updated BEFORE UPDATE ON knowledge_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_knowledge_documents_updated BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_conversations_updated BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_escalations_updated BEFORE UPDATE ON escalations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_support_tickets_updated BEFORE UPDATE ON support_tickets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_canned_responses_updated BEFORE UPDATE ON canned_responses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_end_users_updated BEFORE UPDATE ON end_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_webhooks_updated BEFORE UPDATE ON webhooks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- SCHEMA COMPLETE
-- Fellow BOT v1.0 — Fellowly Technology
-- =============================================================================
