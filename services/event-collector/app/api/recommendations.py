"""
Recommendations API Endpoints

Provides personalized product recommendations by querying the database
for ML-generated recommendations from the Stream Processor.
"""

import structlog
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import asyncpg
from app.core.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            min_size=2,
            max_size=10
        )
        logger.info("Database pool created for recommendations")
    return db_pool


@router.get("/{user_id}")
async def get_recommendations(
    user_id: str,
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations")
):
    """
    Get personalized recommendations for a user.
    
    Returns:
    - Collaborative filtering: What similar users liked
    - Content-based: Products similar to user's interests
    - Popularity: Trending products
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get user features to check if user exists
            user_query = """
                SELECT user_id, total_views, purchase_count, total_revenue, add_to_cart_count
                FROM user_features
                WHERE user_id = $1
            """
            user = await conn.fetchrow(user_query, user_id)
            
            if not user:
                # Return popular products for new users (cold start)
                logger.info("cold_start_user", user_id=user_id)
                popular_query = """
                    SELECT 
                        product_id,
                        view_count,
                        purchase_count,
                        category,
                        brand,
                        price
                    FROM product_features
                    ORDER BY view_count DESC, purchase_count DESC
                    LIMIT $1
                """
                products = await conn.fetch(popular_query, limit)
                
                return {
                    "user_id": user_id,
                    "type": "cold_start",
                    "recommendations": [
                        {
                            "product_id": p["product_id"],
                            "score": float(p["view_count"]) / 100.0,
                            "category": p["category"],
                            "brand": p["brand"],
                            "price": float(p["price"]) if p["price"] else None,
                            "views": p["view_count"],
                            "purchases": p["purchase_count"],
                            "reason": "Popular product - Trending now!"
                        }
                        for p in products
                    ]
                }
            
            # Get user's similar users (collaborative filtering)
            similar_users_query = """
                SELECT similar_user_id, similarity_score
                FROM user_similarity
                WHERE user_id = $1
                ORDER BY similarity_score DESC
                LIMIT 10
            """
            similar_users = await conn.fetch(similar_users_query, user_id)
            
            # Get products from similar users
            collab_recommendations = []
            if similar_users:
                similar_user_ids = [u["similar_user_id"] for u in similar_users]
                collab_query = """
                    SELECT DISTINCT
                        (e.properties->>'productId') as product_id,
                        p.category,
                        p.brand,
                        p.price,
                        p.view_count,
                        p.purchase_count,
                        COUNT(*) as similar_user_interactions
                    FROM events e
                    JOIN product_features p ON (e.properties->>'productId') = p.product_id
                    WHERE e.user_id = ANY($1)
                    AND e.event_name IN ('product_view', 'purchase', 'add_to_cart')
                    AND (e.properties->>'productId') NOT IN (
                        SELECT properties->>'productId' FROM events 
                        WHERE user_id = $2 AND event_name = 'purchase'
                    )
                    GROUP BY (e.properties->>'productId'), p.category, p.brand, p.price, p.view_count, p.purchase_count
                    ORDER BY similar_user_interactions DESC, p.purchase_count DESC
                    LIMIT $3
                """
                collab_products = await conn.fetch(collab_query, similar_user_ids, user_id, limit)
                collab_recommendations = [
                    {
                        "product_id": p["product_id"],
                        "score": float(p["similar_user_interactions"]) * 0.5,
                        "category": p["category"],
                        "brand": p["brand"],
                        "price": float(p["price"]) if p["price"] else None,
                        "views": p["view_count"],
                        "purchases": p["purchase_count"],
                        "reason": f"Users like you bought this ({p['similar_user_interactions']} similar users)"
                    }
                    for p in collab_products
                ]
            
            # Get user's viewed categories for content-based
            category_query = """
                SELECT DISTINCT p.category
                FROM events e
                JOIN product_features p ON (e.properties->>'productId') = p.product_id
                WHERE e.user_id = $1
                AND e.event_name IN ('product_view', 'add_to_cart')
                LIMIT 5
            """
            user_categories = await conn.fetch(category_query, user_id)
            
            # Get content-based recommendations (same category)
            content_recommendations = []
            if user_categories:
                categories = [c["category"] for c in user_categories if c["category"]]
                content_query = """
                    SELECT 
                        product_id,
                        category,
                        brand,
                        price,
                        view_count,
                        purchase_count
                    FROM product_features
                    WHERE category = ANY($1)
                    AND product_id NOT IN (
                        SELECT properties->>'productId' FROM events 
                        WHERE user_id = $2 AND event_name IN ('product_view', 'purchase')
                    )
                    ORDER BY purchase_count DESC, view_count DESC
                    LIMIT $3
                """
                content_products = await conn.fetch(content_query, categories, user_id, limit)
                content_recommendations = [
                    {
                        "product_id": p["product_id"],
                        "score": float(p["purchase_count"]) * 0.3,
                        "category": p["category"],
                        "brand": p["brand"],
                        "price": float(p["price"]) if p["price"] else None,
                        "views": p["view_count"],
                        "purchases": p["purchase_count"],
                        "reason": f"Based on your interest in {p['category']}"
                    }
                    for p in content_products
                ]
            
            # Combine and deduplicate recommendations
            all_recs = {}
            for rec in collab_recommendations + content_recommendations:
                if rec["product_id"] not in all_recs:
                    all_recs[rec["product_id"]] = rec
                else:
                    # Combine scores
                    all_recs[rec["product_id"]]["score"] += rec["score"]
                    all_recs[rec["product_id"]]["reason"] += f" & {rec['reason']}"
            
            # Sort by score and limit
            final_recs = sorted(
                all_recs.values(),
                key=lambda x: x["score"],
                reverse=True
            )[:limit]
            
            logger.info(
                "recommendations_served",
                user_id=user_id,
                count=len(final_recs),
                has_collab=len(collab_recommendations) > 0,
                has_content=len(content_recommendations) > 0
            )
            
            return {
                "user_id": user_id,
                "type": "personalized",
                "recommendations": final_recs
            }
            
    except Exception as e:
        logger.error("recommendations_error", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recommendations: {str(e)}"
        )


@router.get("/complementary/{product_id}")
async def get_complementary_products(
    product_id: str,
    limit: int = Query(6, ge=1, le=20, description="Number of complementary products")
):
    """
    Get complementary products (frequently bought together).
    
    Based on:
    - Same category products
    - Products viewed by users who viewed this product
    """
    try:
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            # Get product details
            product_query = """
                SELECT product_id, category, brand, price, view_count, purchase_count
                FROM product_features
                WHERE product_id = $1
            """
            product = await conn.fetchrow(product_query, product_id)
            
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            # Get users who viewed this product
            viewers_query = """
                SELECT DISTINCT user_id
                FROM events
                WHERE properties->>'productId' = $1
                AND event_name IN ('product_view', 'purchase', 'add_to_cart')
                LIMIT 100
            """
            viewers = await conn.fetch(viewers_query, product_id)
            viewer_ids = [v["user_id"] for v in viewers]
            
            # Get products these users also viewed
            complementary_query = """
                SELECT 
                    (e.properties->>'productId') as product_id,
                    p.category,
                    p.brand,
                    p.price,
                    p.view_count,
                    p.purchase_count,
                    COUNT(DISTINCT e.user_id) as co_viewers
                FROM events e
                JOIN product_features p ON (e.properties->>'productId') = p.product_id
                WHERE e.user_id = ANY($1)
                AND (e.properties->>'productId') != $2
                AND e.event_name IN ('product_view', 'purchase', 'add_to_cart')
                GROUP BY (e.properties->>'productId'), p.category, p.brand, p.price, p.view_count, p.purchase_count
                ORDER BY co_viewers DESC, p.purchase_count DESC
                LIMIT $3
            """
            complementary = await conn.fetch(complementary_query, viewer_ids, product_id, limit)
            
            results = [
                {
                    "product_id": p["product_id"],
                    "category": p["category"],
                    "brand": p["brand"],
                    "price": float(p["price"]) if p["price"] else None,
                    "views": p["view_count"],
                    "purchases": p["purchase_count"],
                    "co_viewers": p["co_viewers"],
                    "reason": f"Bought by {p['co_viewers']} customers who viewed this product"
                }
                for p in complementary
            ]
            
            logger.info(
                "complementary_products_served",
                product_id=product_id,
                count=len(results)
            )
            
            return {
                "product_id": product_id,
                "complementary_products": results
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("complementary_error", product_id=product_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get complementary products: {str(e)}"
        )
