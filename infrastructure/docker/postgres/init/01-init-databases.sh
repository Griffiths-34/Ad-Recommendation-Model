#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create databases
    CREATE DATABASE event_db;
    CREATE DATABASE user_db;
    CREATE DATABASE ad_db;

    -- Connect to event_db and create schema
    \c event_db

    -- Enable extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "timescaledb";

    -- Create events table
    CREATE TABLE IF NOT EXISTS events (
        id BIGSERIAL PRIMARY KEY,
        event_name VARCHAR(100) NOT NULL,
        user_id VARCHAR(100),
        session_id VARCHAR(100) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        properties JSONB,
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        INDEX idx_event_name (event_name),
        INDEX idx_user_id (user_id),
        INDEX idx_session_id (session_id),
        INDEX idx_timestamp (timestamp)
    );

    -- Convert to hypertable for time-series optimization
    SELECT create_hypertable('events', 'timestamp', if_not_exists => TRUE);

    -- Create user_events materialized view
    CREATE MATERIALIZED VIEW IF NOT EXISTS user_event_summary AS
    SELECT 
        user_id,
        event_name,
        COUNT(*) as event_count,
        MAX(timestamp) as last_event_time
    FROM events
    WHERE user_id IS NOT NULL
    GROUP BY user_id, event_name;

    -- Create index on materialized view
    CREATE INDEX IF NOT EXISTS idx_user_event_summary_user_id ON user_event_summary(user_id);

    -- Connect to user_db and create schema
    \c user_db

    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Create users table
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id VARCHAR(100) UNIQUE NOT NULL,
        email VARCHAR(255),
        properties JSONB,
        first_seen_at TIMESTAMPTZ DEFAULT NOW(),
        last_seen_at TIMESTAMPTZ DEFAULT NOW(),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Create user_profiles table
    CREATE TABLE IF NOT EXISTS user_profiles (
        id BIGSERIAL PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        profile_data JSONB,
        embedding FLOAT8[],
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

    -- Connect to ad_db and create schema
    \c ad_db

    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- Create campaigns table
    CREATE TABLE IF NOT EXISTS campaigns (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        status VARCHAR(50) DEFAULT 'active',
        budget DECIMAL(10, 2),
        spent DECIMAL(10, 2) DEFAULT 0,
        start_date TIMESTAMPTZ,
        end_date TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Create ads table
    CREATE TABLE IF NOT EXISTS ads (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        campaign_id UUID NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        image_url VARCHAR(500),
        destination_url VARCHAR(500),
        status VARCHAR(50) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    );

    -- Create ad_impressions table
    CREATE TABLE IF NOT EXISTS ad_impressions (
        id BIGSERIAL PRIMARY KEY,
        ad_id UUID NOT NULL,
        user_id VARCHAR(100),
        session_id VARCHAR(100),
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        properties JSONB,
        FOREIGN KEY (ad_id) REFERENCES ads(id)
    );

    -- Create ad_clicks table
    CREATE TABLE IF NOT EXISTS ad_clicks (
        id BIGSERIAL PRIMARY KEY,
        ad_id UUID NOT NULL,
        user_id VARCHAR(100),
        session_id VARCHAR(100),
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        properties JSONB,
        FOREIGN KEY (ad_id) REFERENCES ads(id)
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_ads_campaign_id ON ads(campaign_id);
    CREATE INDEX IF NOT EXISTS idx_ad_impressions_ad_id ON ad_impressions(ad_id);
    CREATE INDEX IF NOT EXISTS idx_ad_impressions_user_id ON ad_impressions(user_id);
    CREATE INDEX IF NOT EXISTS idx_ad_clicks_ad_id ON ad_clicks(ad_id);
    CREATE INDEX IF NOT EXISTS idx_ad_clicks_user_id ON ad_clicks(user_id);

    -- Grant permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;

EOSQL

echo "Database initialization completed successfully!"
