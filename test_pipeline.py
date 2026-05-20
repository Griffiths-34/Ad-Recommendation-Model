"""
Test script to verify the complete event processing pipeline:
Event Collector → Kafka → Stream Processor → PostgreSQL → Recommendations

Run this after starting:
1. Docker services (docker-compose up -d)
2. Event Collector (cd services/event-collector && npm start)
3. Stream Processor (cd services/stream-processor && poetry run python -m app.main)
"""

import requests
import json
import time
import psycopg2

# Test configuration
EVENT_COLLECTOR_URL = "http://localhost:8001/events/track"
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "ad_recommendation",
    "user": "postgres",
    "password": "postgres"
}

def send_test_events():
    """Send sample events to Event Collector"""
    
    print("📤 Sending test events to Event Collector...")
    
    # Sample products
    products = [
        {"id": "prod-1", "name": "Nike Air Max", "category": "Shoes", "brand": "Nike", "price": 120},
        {"id": "prod-2", "name": "Adidas Ultraboost", "category": "Shoes", "brand": "Adidas", "price": 180},
        {"id": "prod-3", "name": "Apple iPhone 15", "category": "Electronics", "brand": "Apple", "price": 999},
        {"id": "prod-4", "name": "Sony Headphones", "category": "Electronics", "brand": "Sony", "price": 299},
        {"id": "prod-5", "name": "Levi's Jeans", "category": "Clothing", "brand": "Levi's", "price": 89}
    ]
    
    # Sample users
    users = ["user-alice", "user-bob", "user-charlie"]
    
    # Generate events
    events_sent = 0
    
    for user in users:
        session = f"session-{user}-{int(time.time())}"
        
        # User views products
        for product in products[:3]:  # View first 3 products
            event = {
                "eventName": "product_view",
                "properties": {
                    "productId": product["id"],
                    "productName": product["name"],
                    "category": product["category"],
                    "brand": product["brand"],
                    "price": product["price"]
                },
                "userId": user,
                "sessionId": session,
                "timestamp": int(time.time() * 1000)
            }
            
            response = requests.post(EVENT_COLLECTOR_URL, json=event)
            if response.status_code in (200, 201):
                events_sent += 1
                print(f"  ✅ {user} viewed {product['name']}")
            else:
                print(f"  ❌ Failed: {response.status_code}")
            
            time.sleep(0.1)  # Small delay
        
        # User adds to cart
        cart_product = products[1]
        event = {
            "eventName": "add_to_cart",
            "properties": {
                "productId": cart_product["id"],
                "productName": cart_product["name"],
                "category": cart_product["category"],
                "price": cart_product["price"]
            },
            "userId": user,
            "sessionId": session,
            "timestamp": int(time.time() * 1000)
        }
        
        response = requests.post(EVENT_COLLECTOR_URL, json=event)
        if response.status_code in (200, 201):
            events_sent += 1
            print(f"  ✅ {user} added {cart_product['name']} to cart")
        
        time.sleep(0.1)
        
        # User purchases (only Alice and Bob)
        if user in ["user-alice", "user-bob"]:
            event = {
                "eventName": "purchase",
                "properties": {
                    "productId": cart_product["id"],
                    "productName": cart_product["name"],
                    "price": cart_product["price"],
                    "quantity": 1,
                    "totalAmount": cart_product["price"]
                },
                "userId": user,
                "sessionId": session,
                "timestamp": int(time.time() * 1000)
            }
            
            response = requests.post(EVENT_COLLECTOR_URL, json=event)
            if response.status_code in (200, 201):
                events_sent += 1
                print(f"  ✅ {user} purchased {cart_product['name']}")
            
            time.sleep(0.1)
    
    print(f"\n📊 Total events sent: {events_sent}")
    return events_sent


def check_database():
    """Check if events were processed and stored in PostgreSQL"""
    
    print("\n🔍 Checking database...")
    print("Waiting 10 seconds for Stream Processor to consume and process events...")
    time.sleep(10)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Check events table
        cur.execute("SELECT COUNT(*) FROM events")
        event_count = cur.fetchone()[0]
        print(f"\n📦 Events stored: {event_count}")
        
        if event_count > 0:
            cur.execute("""
                SELECT event_name, COUNT(*) as count 
                FROM events 
                GROUP BY event_name 
                ORDER BY count DESC
            """)
            print("\n  Event breakdown:")
            for row in cur.fetchall():
                print(f"    - {row[0]}: {row[1]}")
        
        # Check user features
        cur.execute("SELECT COUNT(*) FROM user_features")
        user_count = cur.fetchone()[0]
        print(f"\n👥 Users in feature store: {user_count}")
        
        if user_count > 0:
            cur.execute("""
                SELECT user_id, total_views, purchase_count, total_revenue 
                FROM user_features 
                ORDER BY total_revenue DESC 
                LIMIT 5
            """)
            print("\n  Top users:")
            for row in cur.fetchall():
                print(f"    - {row[0]}: {row[1]} views, {row[2]} purchases, ${row[3]}")
        
        # Check product features
        cur.execute("SELECT COUNT(*) FROM product_features")
        product_count = cur.fetchone()[0]
        print(f"\n📦 Products in feature store: {product_count}")
        
        if product_count > 0:
            cur.execute("""
                SELECT product_id, name, view_count, purchase_count, conversion_rate 
                FROM product_features 
                ORDER BY view_count DESC 
                LIMIT 5
            """)
            print("\n  Top products:")
            for row in cur.fetchall():
                print(f"    - {row[1]}: {row[2]} views, {row[3]} purchases, {float(row[4]):.2%} conversion")
        
        # Check recommendations
        cur.execute("SELECT COUNT(*) FROM recommendations")
        rec_count = cur.fetchone()[0]
        print(f"\n🎯 Recommendations generated: {rec_count}")
        
        if rec_count > 0:
            cur.execute("""
                SELECT user_id, COUNT(*) as rec_count 
                FROM recommendations 
                GROUP BY user_id
            """)
            print("\n  Recommendations per user:")
            for row in cur.fetchall():
                print(f"    - {row[0]}: {row[1]} recommendations")
        
        cur.close()
        conn.close()
        
        # Summary
        print("\n" + "="*60)
        if event_count > 0 and user_count > 0 and product_count > 0:
            print("✅ SUCCESS! Pipeline is working correctly:")
            print("   - Events sent to Event Collector")
            print("   - Events consumed from Kafka")
            print("   - Events stored in PostgreSQL")
            print("   - User features calculated")
            print("   - Product features calculated")
            if rec_count > 0:
                print("   - Recommendations generated")
            else:
                print("   - Recommendations pending (ML model needs more data)")
        else:
            print("⚠️  WARNING: Some data is missing")
            if event_count == 0:
                print("   - No events in database (check Stream Processor logs)")
            if user_count == 0:
                print("   - No user features (check event processing)")
            if product_count == 0:
                print("   - No product features (check event processing)")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running: docker ps | grep postgres")
        print("2. Check if ad_recommendation database exists")
        print("3. Verify port 5433 is accessible")


def main():
    """Run the complete test"""
    
    print("="*60)
    print("  AD RECOMMENDATION PLATFORM - PIPELINE TEST")
    print("="*60)
    
    # Check if Event Collector is running
    try:
        response = requests.get("http://localhost:8001/health", timeout=2)
        print("✅ Event Collector is running\n")
    except:
        print("❌ Event Collector is NOT running!")
        print("   Start it with: cd services/event-collector && npm start")
        return
    
    # Send test events
    events_sent = send_test_events()
    
    if events_sent == 0:
        print("❌ No events were sent successfully")
        return
    
    # Check database
    check_database()
    
    print("\n📖 Next steps:")
    print("1. View Stream Processor logs to see event processing")
    print("2. Check Kafka UI: http://localhost:8081")
    print("3. View Jaeger traces: http://localhost:16686")
    print("4. Open demo site: http://localhost:3000/demo.html")
    print("\n💡 To generate more data, visit the demo site and click around!")


if __name__ == "__main__":
    main()
