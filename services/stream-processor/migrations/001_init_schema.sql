-- Database schema for Stream Processor
-- Creates tables for events, user features, and product features

-- Events table (raw event storage with full audit trail)
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    session_id VARCHAR(255) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for events table
CREATE INDEX IF NOT EXISTS idx_events_user_id ON events (user_id);
CREATE INDEX IF NOT EXISTS idx_events_session_id ON events (session_id);
CREATE INDEX IF NOT EXISTS idx_events_event_name ON events (event_name);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_properties_product_id ON events ((properties->>'productId'));

-- User features table (aggregated ML features)
CREATE TABLE IF NOT EXISTS user_features (
    user_id VARCHAR(255) PRIMARY KEY,
    
    -- Viewing behavior
    total_views INTEGER DEFAULT 0,
    categories_viewed TEXT[] DEFAULT '{}',
    brands_viewed TEXT[] DEFAULT '{}',
    avg_price_viewed DECIMAL(10,2) DEFAULT 0.0,
    max_price_viewed DECIMAL(10,2) DEFAULT 0.0,
    
    -- Search behavior
    search_count INTEGER DEFAULT 0,
    top_search_terms TEXT[] DEFAULT '{}',
    
    -- Cart behavior
    add_to_cart_count INTEGER DEFAULT 0,
    remove_from_cart_count INTEGER DEFAULT 0,
    cart_abandonment_rate DECIMAL(5,4) DEFAULT 0.0,
    
    -- Purchase behavior
    purchase_count INTEGER DEFAULT 0,
    total_revenue DECIMAL(12,2) DEFAULT 0.0,
    avg_order_value DECIMAL(10,2) DEFAULT 0.0,
    purchased_categories TEXT[] DEFAULT '{}',
    
    -- Time patterns
    active_hours INTEGER[] DEFAULT '{}',
    active_days TEXT[] DEFAULT '{}',
    last_active TIMESTAMP,
    
    -- Session info
    avg_session_duration DECIMAL(10,2) DEFAULT 0.0,
    sessions_count INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for user_features
CREATE INDEX IF NOT EXISTS idx_user_features_updated_at ON user_features (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_features_purchase_count ON user_features (purchase_count DESC);

-- Product features table (aggregated product metrics)
CREATE TABLE IF NOT EXISTS product_features (
    product_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500),
    category VARCHAR(100),
    brand VARCHAR(100),
    price DECIMAL(10,2),
    
    -- Popularity metrics
    view_count INTEGER DEFAULT 0,
    purchase_count INTEGER DEFAULT 0,
    add_to_cart_count INTEGER DEFAULT 0,
    conversion_rate DECIMAL(5,4) GENERATED ALWAYS AS (
        CASE 
            WHEN view_count > 0 THEN CAST(purchase_count AS DECIMAL) / view_count
            ELSE 0
        END
    ) STORED,
    
    -- Co-occurrence (stored as JSONB for flexibility)
    also_viewed JSONB DEFAULT '{}',
    also_purchased JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for product_features
CREATE INDEX IF NOT EXISTS idx_product_features_category ON product_features (category);
CREATE INDEX IF NOT EXISTS idx_product_features_brand ON product_features (brand);
CREATE INDEX IF NOT EXISTS idx_product_features_view_count ON product_features (view_count DESC);
CREATE INDEX IF NOT EXISTS idx_product_features_purchase_count ON product_features (purchase_count DESC);
CREATE INDEX IF NOT EXISTS idx_product_features_conversion_rate ON product_features (conversion_rate DESC);

-- Recommendations table (cache for pre-computed recommendations)
CREATE TABLE IF NOT EXISTS recommendations (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    score DECIMAL(10,6) NOT NULL,
    reason VARCHAR(255),
    algorithm VARCHAR(50),  -- 'collaborative', 'content', 'hybrid', 'popular'
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL DEFAULT NOW() + INTERVAL '1 hour',
    
    -- Constraints
    UNIQUE(user_id, product_id)
);

-- Indexes for recommendations
CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations (user_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_score ON recommendations (score DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_expires_at ON recommendations (expires_at);

-- User-product interactions (for collaborative filtering)
CREATE TABLE IF NOT EXISTS user_product_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    product_id VARCHAR(255) NOT NULL,
    
    -- Interaction types (weighted scores)
    view_count INTEGER DEFAULT 0,
    cart_count INTEGER DEFAULT 0,
    purchase_count INTEGER DEFAULT 0,
    
    -- Calculated interaction strength (for similarity calculations)
    interaction_score DECIMAL(10,6) GENERATED ALWAYS AS (
        view_count * 1.0 +
        cart_count * 3.0 +
        purchase_count * 10.0
    ) STORED,
    
    first_interaction TIMESTAMP NOT NULL,
    last_interaction TIMESTAMP NOT NULL,
    
    -- Constraints
    UNIQUE(user_id, product_id)
);

-- Indexes for user_product_interactions
CREATE INDEX IF NOT EXISTS idx_interactions_user_id ON user_product_interactions (user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_product_id ON user_product_interactions (product_id);
CREATE INDEX IF NOT EXISTS idx_interactions_score ON user_product_interactions (interaction_score DESC);

-- Create materialized view for trending products (refresh periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS trending_products AS
SELECT 
    product_id,
    name,
    category,
    brand,
    price,
    view_count,
    purchase_count,
    conversion_rate,
    -- Trending score based on recent activity
    (
        view_count * 0.3 +
        purchase_count * 0.7
    ) AS trending_score
FROM product_features
WHERE updated_at > NOW() - INTERVAL '7 days'
ORDER BY trending_score DESC
LIMIT 100;

-- Index on materialized view
CREATE INDEX IF NOT EXISTS idx_trending_products_score ON trending_products (trending_score DESC);

-- Function to update user features timestamp
CREATE OR REPLACE FUNCTION update_user_features_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update timestamp
CREATE TRIGGER trigger_update_user_features_timestamp
BEFORE UPDATE ON user_features
FOR EACH ROW
EXECUTE FUNCTION update_user_features_timestamp();

-- Same for product features
CREATE OR REPLACE FUNCTION update_product_features_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_product_features_timestamp
BEFORE UPDATE ON product_features
FOR EACH ROW
EXECUTE FUNCTION update_product_features_timestamp();

-- Refresh materialized view periodically (can be called by cron or app)
-- To manually refresh: REFRESH MATERIALIZED VIEW CONCURRENTLY trending_products;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
