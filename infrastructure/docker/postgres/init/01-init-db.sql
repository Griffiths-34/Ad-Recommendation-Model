-- Initialize databases for the ad platform
-- This script is executed when PostgreSQL container starts

\c event_db;

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Events table (hypertable for time-series data)
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    session_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    properties JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes after table creation
CREATE INDEX IF NOT EXISTS idx_event_name ON events(event_name);
CREATE INDEX IF NOT EXISTS idx_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_session_id ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_properties ON events USING GIN(properties);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('events', 'timestamp', if_not_exists => TRUE);

-- User events aggregation table
CREATE TABLE IF NOT EXISTS user_event_aggregates (
    user_id VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    event_name VARCHAR(100) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, date, event_name)
);

CREATE INDEX IF NOT EXISTS idx_user_aggregates_date ON user_event_aggregates(date DESC);

\c user_db;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id VARCHAR(100) PRIMARY KEY,
    anonymous_id VARCHAR(100),
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    properties JSONB,
    segments JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_anonymous_id ON user_profiles(anonymous_id);
CREATE INDEX IF NOT EXISTS idx_email ON user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_properties ON user_profiles USING GIN(properties);

-- User segments table
CREATE TABLE IF NOT EXISTS user_segments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    rules JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User interests/features for recommendations
CREATE TABLE IF NOT EXISTS user_features (
    user_id VARCHAR(100) PRIMARY KEY,
    features JSONB NOT NULL,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

\c ad_db;

CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Ad campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    advertiser_id VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'ended')),
    budget DECIMAL(10, 2),
    daily_budget DECIMAL(10, 2),
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_advertiser ON campaigns(advertiser_id);

-- Ad creatives table
CREATE TABLE IF NOT EXISTS ad_creatives (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('banner', 'video', 'native', 'interstitial')),
    creative_url TEXT NOT NULL,
    landing_url TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE INDEX IF NOT EXISTS idx_creatives_campaign ON ad_creatives(campaign_id);
CREATE INDEX IF NOT EXISTS idx_creatives_type ON ad_creatives(type);

-- Ad impressions table (hypertable)
CREATE TABLE IF NOT EXISTS ad_impressions (
    id BIGSERIAL PRIMARY KEY,
    ad_id INTEGER NOT NULL,
    user_id VARCHAR(100),
    session_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    bid_price DECIMAL(10, 4),
    win_price DECIMAL(10, 4),
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_impressions_ad ON ad_impressions(ad_id);
CREATE INDEX IF NOT EXISTS idx_impressions_user ON ad_impressions(user_id);
CREATE INDEX IF NOT EXISTS idx_impressions_timestamp ON ad_impressions(timestamp DESC);

-- Ad clicks table (hypertable)
CREATE TABLE IF NOT EXISTS ad_clicks (
    id BIGSERIAL PRIMARY KEY,
    ad_id INTEGER NOT NULL,
    impression_id BIGINT,
    user_id VARCHAR(100),
    session_id VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clicks_ad ON ad_clicks(ad_id);
CREATE INDEX IF NOT EXISTS idx_clicks_user ON ad_clicks(user_id);
CREATE INDEX IF NOT EXISTS idx_clicks_timestamp ON ad_clicks(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_clicks_impression ON ad_clicks(impression_id);

-- Campaign performance aggregates
CREATE TABLE IF NOT EXISTS campaign_performance (
    campaign_id INTEGER NOT NULL,
    date DATE NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    spend DECIMAL(10, 2) NOT NULL DEFAULT 0,
    revenue DECIMAL(10, 2) NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (campaign_id, date),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

CREATE INDEX IF NOT EXISTS idx_performance_date ON campaign_performance(date DESC);
