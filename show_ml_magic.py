"""
🎯 ML RECOMMENDATION ENGINE VISUALIZER
Shows how the recommendation algorithm works step-by-step
"""

import psycopg2
import json
from datetime import datetime
from collections import defaultdict
import math

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "ad_recommendation",
    "user": "postgres",
    "password": "postgres"
}

def print_header(text):
    """Print fancy header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def get_events_summary():
    """Show what events we've collected"""
    print_header("📊 STEP 1: RAW EVENT DATA")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Total events
    cur.execute("SELECT COUNT(*) FROM events")
    total = cur.fetchone()[0]
    print(f"Total events collected: {total}")
    
    if total == 0:
        print("\n⚠️  NO EVENTS YET!")
        print("👉 Go to http://localhost:3000/demo.html and click around!")
        print("   - Click products to view them")
        print("   - Add items to cart")
        print("   - Complete a purchase")
        print("\n   Then run this script again!\n")
        cur.close()
        conn.close()
        return False
    
    # Event breakdown
    cur.execute("""
        SELECT event_name, COUNT(*) as count 
        FROM events 
        GROUP BY event_name 
        ORDER BY count DESC
    """)
    
    print("\nEvent types:")
    for row in cur.fetchall():
        print(f"  • {row[0]:<20} {row[1]:>5} events")
    
    # Sample recent events
    cur.execute("""
        SELECT event_name, user_id, properties, timestamp 
        FROM events 
        ORDER BY timestamp DESC 
        LIMIT 5
    """)
    
    print("\n📝 Recent events:")
    for row in cur.fetchall():
        props = json.loads(row[2]) if isinstance(row[2], str) else row[2]
        print(f"  • {row[0]:<20} by {row[1] or 'anonymous':<15}")
        if 'productName' in props:
            print(f"    └─ Product: {props['productName']}")
    
    cur.close()
    conn.close()
    return True

def show_user_features():
    """Show user behavior patterns (the ML features)"""
    print_header("👥 STEP 2: USER BEHAVIOR PATTERNS (Feature Engineering)")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM user_features")
    user_count = cur.fetchone()[0]
    
    if user_count == 0:
        print("⚠️  No user features calculated yet.")
        print("   Stream Processor needs to process events first.\n")
        cur.close()
        conn.close()
        return False
    
    print(f"Found {user_count} users with calculated features:\n")
    
    cur.execute("""
        SELECT 
            user_id, 
            total_views, 
            purchase_count, 
            total_revenue,
            categories_viewed,
            brands_viewed,
            add_to_cart_count
        FROM user_features 
        ORDER BY total_revenue DESC 
        LIMIT 5
    """)
    
    users_data = []
    for row in cur.fetchall():
        user_id = row[0]
        print(f"🧑 User: {user_id}")
        print(f"   Views:      {row[1]} products")
        print(f"   Purchases:  {row[2]} items")
        print(f"   Revenue:    ${row[3]:.2f}")
        print(f"   Categories: {row[4][:3] if row[4] else []}")
        print(f"   Brands:     {row[5][:3] if row[5] else []}")
        print(f"   Cart adds:  {row[6]}")
        print()
        
        # Create feature vector for similarity calculation
        users_data.append({
            'user_id': user_id,
            'vector': [row[1] or 0, row[2] or 0, float(row[3] or 0), row[6] or 0]
        })
    
    cur.close()
    conn.close()
    return users_data

def show_product_features():
    """Show product popularity and metrics"""
    print_header("📦 STEP 3: PRODUCT POPULARITY METRICS")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM product_features")
    product_count = cur.fetchone()[0]
    
    if product_count == 0:
        print("⚠️  No product features calculated yet.\n")
        cur.close()
        conn.close()
        return False
    
    print(f"Found {product_count} products with metrics:\n")
    
    cur.execute("""
        SELECT 
            product_id,
            name,
            category,
            brand,
            price,
            view_count,
            purchase_count,
            conversion_rate
        FROM product_features 
        ORDER BY view_count DESC 
        LIMIT 10
    """)
    
    print("🏆 Most Popular Products:")
    for idx, row in enumerate(cur.fetchall(), 1):
        print(f"\n{idx}. {row[1]}")
        print(f"   Category:    {row[2]}")
        print(f"   Brand:       {row[3]}")
        print(f"   Price:       ${row[4]}")
        print(f"   Views:       {row[5]}")
        print(f"   Purchases:   {row[6]}")
        print(f"   Conversion:  {float(row[7]):.1%}")
    
    cur.close()
    conn.close()
    return True

def show_collaborative_filtering(users_data):
    """Show how collaborative filtering finds similar users"""
    if len(users_data) < 2:
        return
    
    print_header("🤝 STEP 4: COLLABORATIVE FILTERING (User Similarity)")
    
    print("This is the MAGIC! Finding users who behave similarly:\n")
    
    # Calculate similarity between first user and others
    base_user = users_data[0]
    print(f"Finding users similar to: {base_user['user_id']}")
    print(f"Their behavior vector: {base_user['vector']}")
    print(f"  [views, purchases, revenue, cart_adds]\n")
    
    similarities = []
    for other_user in users_data[1:]:
        similarity = cosine_similarity(base_user['vector'], other_user['vector'])
        similarities.append((other_user['user_id'], similarity, other_user['vector']))
    
    # Sort by similarity
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    print("Similar users (ranked by cosine similarity):\n")
    for user_id, sim, vec in similarities[:3]:
        print(f"  👤 {user_id}")
        print(f"     Similarity score: {sim:.3f} (0=different, 1=identical)")
        print(f"     Their vector: {vec}")
        print(f"     💡 Recommendation: Show products this user bought!")
        print()

def show_content_based_filtering():
    """Show how content-based filtering finds similar products"""
    print_header("🔍 STEP 5: CONTENT-BASED FILTERING (Product Similarity)")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT product_id, name, category, brand, price 
        FROM product_features 
        LIMIT 5
    """)
    
    products = cur.fetchall()
    
    if len(products) < 2:
        print("Need at least 2 products to show similarity.\n")
        cur.close()
        conn.close()
        return
    
    print("Finding products similar to what user viewed:\n")
    
    base_product = products[0]
    print(f"📱 Base Product: {base_product[1]}")
    print(f"   Category: {base_product[2]}")
    print(f"   Brand:    {base_product[3]}")
    print(f"   Price:    ${base_product[4]}\n")
    
    print("Similar products:\n")
    for prod in products[1:]:
        similarity_score = 0.0
        reasons = []
        
        # Same category = +0.5
        if prod[2] == base_product[2]:
            similarity_score += 0.5
            reasons.append(f"same category ({prod[2]})")
        
        # Same brand = +0.3
        if prod[3] == base_product[3]:
            similarity_score += 0.3
            reasons.append(f"same brand ({prod[3]})")
        
        # Similar price (within $50) = +0.2
        if abs(prod[4] - base_product[4]) < 50:
            similarity_score += 0.2
            reasons.append(f"similar price (${prod[4]})")
        
        print(f"  📦 {prod[1]}")
        print(f"     Similarity: {similarity_score:.2f}/1.0")
        print(f"     Reason: {', '.join(reasons) if reasons else 'different'}")
        print()
    
    cur.close()
    conn.close()

def show_hybrid_recommendations():
    """Show final hybrid recommendation algorithm"""
    print_header("🎯 STEP 6: HYBRID RECOMMENDATIONS (The Final Output)")
    
    print("The system combines 3 algorithms:\n")
    
    print("1️⃣  COLLABORATIVE FILTERING (50% weight)")
    print("   'Users like you also bought...'")
    print("   → Find similar users")
    print("   → Recommend what they purchased\n")
    
    print("2️⃣  CONTENT-BASED FILTERING (30% weight)")
    print("   'Similar to what you viewed...'")
    print("   → Find similar products (category, brand, price)")
    print("   → Recommend those products\n")
    
    print("3️⃣  POPULARITY-BASED (20% weight)")
    print("   'Trending now...'")
    print("   → Show hot/popular products")
    print("   → Solves 'cold start' for new users\n")
    
    print("Final Score = (collaborative × 0.5) + (content × 0.3) + (popular × 0.2)\n")

def show_ml_code():
    """Show the actual ML code"""
    print_header("💻 WHERE THE ML CODE LIVES")
    
    print("The recommendation engine is in:")
    print("📁 services/stream-processor/app/ml/recommender.py (351 lines)\n")
    
    print("Key functions:\n")
    
    print("1. load_features() - Load user/product data from database")
    print("   → Builds feature vectors for ML\n")
    
    print("2. _calculate_user_similarity() - Cosine similarity")
    print("   → Finds similar users using numpy")
    print("   → Formula: cos(θ) = (A·B) / (||A|| × ||B||)\n")
    
    print("3. _collaborative_recommendations()")
    print("   → Gets products from similar users")
    print("   → Ranks by purchase frequency\n")
    
    print("4. _content_based_recommendations()")
    print("   → Calculates product similarity")
    print("   → Same category (+0.5), brand (+0.3), price (+0.2)\n")
    
    print("5. recommend_for_user() - Main function")
    print("   → Combines all algorithms")
    print("   → Returns top N recommendations with explanations\n")

def main():
    """Run the ML magic visualizer"""
    print("\n" + "🌟" * 35)
    print("        ML RECOMMENDATION ENGINE VISUALIZER")
    print("🌟" * 35)
    
    try:
        # Step 1: Show raw events
        has_events = get_events_summary()
        if not has_events:
            return
        
        # Step 2: Show user features
        users_data = show_user_features()
        
        # Step 3: Show product features
        show_product_features()
        
        # Step 4: Show collaborative filtering
        if users_data and len(users_data) >= 2:
            show_collaborative_filtering(users_data)
        
        # Step 5: Show content-based filtering
        show_content_based_filtering()
        
        # Step 6: Show hybrid approach
        show_hybrid_recommendations()
        
        # Show where code lives
        show_ml_code()
        
        # Final instructions
        print_header("🚀 NEXT STEPS")
        print("1. Stream Processor needs to be running to process events")
        print("2. Generate more data by using the demo site")
        print("3. Check recommendations table:")
        print("   docker exec postgres psql -U postgres -d ad_recommendation \\")
        print("     -c 'SELECT * FROM recommendations LIMIT 10;'")
        print("\n4. View real-time logs from Stream Processor to see ML in action!\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  • PostgreSQL is running (docker ps)")
        print("  • Database 'ad_recommendation' exists")
        print("  • Port 5433 is accessible\n")

if __name__ == "__main__":
    main()
