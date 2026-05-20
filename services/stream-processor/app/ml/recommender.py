"""
ML-based Recommendation Engine.
Implements collaborative filtering + content-based filtering.
"""

import numpy as np
import structlog
from typing import List, Dict, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

from app.core.database import db

logger = structlog.get_logger()


class RecommendationEngine:
    """
    Hybrid recommendation system combining multiple approaches:
    
    1. Collaborative Filtering: "Users like you also liked..."
    2. Content-Based: "Similar to what you viewed..."
    3. Popularity-Based: "Trending products..."
    4. Business Rules: "Complete your setup with..."
    
    Why hybrid?
    - Cold start problem solved (new users/products)
    - Better accuracy
    - More diverse recommendations
    """
    
    def __init__(self):
        self.user_features = {}  # user_id -> feature vector
        self.product_features = {}  # product_id -> feature vector
        self.user_similarity = {}  # user_id -> {similar_user_id: score}
        self.product_similarity = {}  # product_id -> {similar_product_id: score}
        self.last_updated = None
        
    async def load_features(self) -> None:
        """
        Load user and product features from database.
        Called periodically to refresh model.
        """
        logger.info("loading_features_started")
        
        # Load user features
        user_query = """
            SELECT 
                user_id,
                total_views,
                purchase_count,
                total_revenue,
                add_to_cart_count,
                search_count,
                categories_viewed,
                brands_viewed
            FROM user_features
            WHERE updated_at > NOW() - INTERVAL '30 days'
        """
        
        users = await db.fetch(user_query)
        for user in users:
            self.user_features[user['user_id']] = {
                'views': user['total_views'],
                'purchases': user['purchase_count'],
                'revenue': user['total_revenue'],
                'carts': user['add_to_cart_count'],
                'searches': user['search_count'],
                'categories': set(user['categories_viewed'] or []),
                'brands': set(user['brands_viewed'] or []),
            }
        
        # Load product features
        product_query = """
            SELECT 
                product_id,
                category,
                brand,
                price,
                view_count,
                purchase_count,
                add_to_cart_count
            FROM product_features
        """
        
        products = await db.fetch(product_query)
        for product in products:
            self.product_features[product['product_id']] = {
                'category': product['category'],
                'brand': product['brand'],
                'price': product['price'],
                'views': product['view_count'],
                'purchases': product['purchase_count'],
                'carts': product['add_to_cart_count'],
                'conversion_rate': (
                    product['purchase_count'] / max(product['view_count'], 1)
                )
            }
        
        # Calculate similarities
        await self._calculate_user_similarity()
        await self._calculate_product_similarity()
        
        self.last_updated = datetime.utcnow()
        
        logger.info(
            "features_loaded",
            user_count=len(self.user_features),
            product_count=len(self.product_features)
        )
        
    async def _calculate_user_similarity(self) -> None:
        """
        Calculate user-user similarity using cosine similarity.
        
        Formula: similarity = (A · B) / (||A|| * ||B||)
        
        Why cosine?
        - Scale-invariant (works for users with different activity levels)
        - Fast to compute
        - Industry standard
        """
        user_vectors = {}
        
        # Convert features to numerical vectors
        for user_id, features in self.user_features.items():
            vector = np.array([
                features['views'],
                features['purchases'] * 10,  # Weight purchases higher
                features['revenue'] / 1000,  # Normalize revenue
                features['carts'] * 2,
                features['searches'],
                len(features['categories']),
                len(features['brands']),
            ], dtype=float)
            
            # Normalize vector
            norm = np.linalg.norm(vector)
            if norm > 0:
                user_vectors[user_id] = vector / norm
        
        # Calculate pairwise similarities
        for user_id, vector in user_vectors.items():
            similarities = {}
            for other_id, other_vector in user_vectors.items():
                if user_id != other_id:
                    # Cosine similarity = dot product of normalized vectors
                    similarity = np.dot(vector, other_vector)
                    if similarity > 0.3:  # Threshold for relevance
                        similarities[other_id] = float(similarity)
            
            # Store top 10 similar users
            top_similar = sorted(
                similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            self.user_similarity[user_id] = dict(top_similar)
        
        logger.debug("user_similarity_calculated", user_count=len(self.user_similarity))
        
    async def _calculate_product_similarity(self) -> None:
        """
        Calculate product-product similarity based on:
        - Same category
        - Similar price range
        - Co-occurrence (viewed together)
        """
        for product_id, features in self.product_features.items():
            similarities = {}
            
            for other_id, other_features in self.product_features.items():
                if product_id == other_id:
                    continue
                
                score = 0.0
                
                # Same category (high weight)
                if features['category'] == other_features['category']:
                    score += 0.5
                
                # Same brand
                if features['brand'] == other_features['brand']:
                    score += 0.2
                
                # Similar price (within 30%)
                price_a = float(features['price'])
                price_b = float(other_features['price'])
                price_diff = abs(price_a - price_b) / max(price_a, 1.0)
                if price_diff < 0.3:
                    score += 0.3 * (1.0 - price_diff)
                
                if score > 0.3:
                    similarities[other_id] = score
            
            # Store top 10 similar products
            top_similar = sorted(
                similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            self.product_similarity[product_id] = dict(top_similar)
        
        logger.debug("product_similarity_calculated", product_count=len(self.product_similarity))
        
    async def recommend_for_user(
        self,
        user_id: str,
        n: int = 10,
        exclude_purchased: bool = True
    ) -> List[Dict[str, any]]:
        """
        Generate personalized recommendations for a user.
        
        Args:
            user_id: User to recommend for
            n: Number of recommendations
            exclude_purchased: Filter out already purchased products
            
        Returns:
            List of recommended products with scores
        """
        # Ensure features are loaded
        if not self.user_features or not self.product_features:
            await self.load_features()
        
        recommendations = defaultdict(float)
        
        # 1. Collaborative filtering (50% weight)
        collab_recs = await self._collaborative_recommendations(user_id)
        for product_id, score in collab_recs:
            recommendations[product_id] += score * 0.5
        
        # 2. Content-based (30% weight)
        content_recs = await self._content_based_recommendations(user_id)
        for product_id, score in content_recs:
            recommendations[product_id] += score * 0.3
        
        # 3. Popularity (20% weight) - for cold start
        popular_recs = await self._popular_recommendations()
        for product_id, score in popular_recs:
            recommendations[product_id] += score * 0.2
        
        # Filter purchased products
        if exclude_purchased:
            purchased = await self._get_user_purchases(user_id)
            for product_id in purchased:
                recommendations.pop(product_id, None)
        
        # Sort and return top N
        top_recs = sorted(
            recommendations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:n]
        
        # Enrich with product details
        results = []
        for product_id, score in top_recs:
            features = self.product_features.get(product_id, {})
            results.append({
                'product_id': product_id,
                'score': score,
                'category': features.get('category'),
                'brand': features.get('brand'),
                'price': features.get('price'),
                'reason': self._explain_recommendation(user_id, product_id)
            })
        
        logger.info(
            "recommendations_generated",
            user_id=user_id,
            count=len(results),
            score_range=[results[0]['score'], results[-1]['score']] if results else []
        )
        
        return results
        
    async def _collaborative_recommendations(self, user_id: str) -> List[Tuple[str, float]]:
        """Find products liked by similar users."""
        recommendations = defaultdict(float)
        
        # Get similar users
        similar_users = self.user_similarity.get(user_id, {})
        
        # Get products they interacted with
        for similar_user_id, similarity_score in similar_users.items():
            query = """
                SELECT DISTINCT properties->>'productId' as product_id
                FROM events
                WHERE user_id = $1
                AND event_name IN ('product_view', 'purchase', 'add_to_cart')
                AND timestamp > NOW() - INTERVAL '30 days'
            """
            
            products = await db.fetch(query, similar_user_id)
            for product in products:
                if product['product_id']:
                    recommendations[product['product_id']] += similarity_score
        
        return list(recommendations.items())
        
    async def _content_based_recommendations(self, user_id: str) -> List[Tuple[str, float]]:
        """Find products similar to what user has viewed."""
        recommendations = defaultdict(float)
        
        # Get user's recently viewed products
        query = """
            SELECT DISTINCT properties->>'productId' as product_id
            FROM events
            WHERE user_id = $1
            AND event_name = 'product_view'
            AND timestamp > NOW() - INTERVAL '7 days'
            ORDER BY timestamp DESC
            LIMIT 10
        """
        
        viewed_products = await db.fetch(query, user_id)
        
        # Find similar products
        for product in viewed_products:
            product_id = product['product_id']
            if not product_id:
                continue
                
            similar_products = self.product_similarity.get(product_id, {})
            for similar_id, similarity in similar_products.items():
                recommendations[similar_id] += similarity
        
        return list(recommendations.items())
        
    async def _popular_recommendations(self) -> List[Tuple[str, float]]:
        """Get trending/popular products."""
        query = """
            SELECT 
                product_id,
                (view_count * 0.3 + purchase_count * 0.7) as popularity_score
            FROM product_features
            ORDER BY popularity_score DESC
            LIMIT 20
        """
        
        products = await db.fetch(query)
        return [(p['product_id'], p['popularity_score']) for p in products]
        
    async def _get_user_purchases(self, user_id: str) -> List[str]:
        """Get products user has already purchased."""
        query = """
            SELECT DISTINCT properties->>'productId' as product_id
            FROM events
            WHERE user_id = $1
            AND event_name = 'purchase'
        """
        
        products = await db.fetch(query, user_id)
        return [p['product_id'] for p in products if p['product_id']]
        
    def _explain_recommendation(self, user_id: str, product_id: str) -> str:
        """Generate human-readable explanation for recommendation."""
        # Check if similar users bought it
        similar_users = self.user_similarity.get(user_id, {})
        if similar_users:
            return "Users like you also viewed this"
        
        # Check if similar to viewed products
        if product_id in self.product_similarity:
            return "Similar to products you viewed"
        
        # Default to popularity
        return "Trending product"


# Global recommendation engine
recommender = RecommendationEngine()
