# 📊 Data Flow & Usage Guide

## Where Your Data Gets Saved

### 1. **Real-Time Event Flow**
```
Demo Website → Tracker SDK → Event Collector API → Kafka → PostgreSQL
```

### 2. **Storage Locations**

#### A. **Kafka (Event Streaming)**
- **Location**: `localhost:9092`
- **Topic**: `user_events`
- **Purpose**: Real-time event streaming buffer
- **Data Retention**: 7 days
- **Access**: Kafka UI at `http://localhost:8081`

**What's stored here:**
- Every click, view, add-to-cart, purchase event
- User identification data
- Session information
- Timestamps and metadata

#### B. **PostgreSQL (Persistent Storage)**
- **Location**: `localhost:5433`
- **Databases**:
  - `event_db` - All user events
  - `user_db` - User profiles
  - `ad_db` - Ad campaigns and performance

**Current Status**: Events go to Kafka, but Stream Processor (not built yet) will move them to PostgreSQL

#### C. **Redis (Caching & Rate Limiting)**
- **Location**: `localhost:6379`
- **Purpose**: 
  - Rate limiting
  - Session caching
  - Hot data storage

---

## 🔍 How to View Your Data

### Option 1: Kafka UI (Easiest)

1. **Open Kafka UI**:
   ```
   http://localhost:8081
   ```

2. **Navigate to Topics** → `user_events`

3. **View Messages** to see all tracked events

**What you'll see:**
```json
{
  "eventName": "product_view",
  "properties": {
    "productId": "prod-001",
    "productName": "Gaming Laptop Pro X1",
    "price": 15999,
    "currency": "ZAR"
  },
  "timestamp": 1699876543210,
  "userId": "user-abc123",
  "sessionId": "session-xyz789"
}
```

### Option 2: Command Line (Kafka Consumer)

```powershell
# Connect to Kafka container
docker exec -it kafka-server bash

# Read messages from topic
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic user_events \
  --from-beginning
```

### Option 3: PostgreSQL Database (Once Stream Processor is built)

```powershell
# Connect to database
docker exec -it postgres-db psql -U postgres -d event_db

# Query events
SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;

# Query user activity
SELECT user_id, COUNT(*) as event_count 
FROM events 
GROUP BY user_id;

# Query purchases
SELECT * FROM events WHERE event_name = 'purchase';
```

---

## 📈 How to Use the Data

### 1. **User Behavior Analysis**

**Questions you can answer:**
- Which products are viewed most?
- What's the conversion rate (views → purchases)?
- Where do users drop off?
- What categories are popular?

**Example Query (PostgreSQL - future)**:
```sql
-- Top viewed products
SELECT 
  properties->>'productName' as product,
  COUNT(*) as views
FROM events
WHERE event_name = 'product_view'
GROUP BY properties->>'productName'
ORDER BY views DESC
LIMIT 10;
```

### 2. **Purchase Tracking**

**What you track:**
```javascript
{
  orderId: 'order-1699876543210',
  revenue: 18398.85,  // Total with tax
  currency: 'ZAR',
  products: [
    {
      productId: 'prod-001',
      productName: 'Gaming Laptop Pro X1',
      price: 15999,
      quantity: 1
    }
  ],
  tax: 2399.85,
  shipping: 0
}
```

**Use cases:**
- Calculate total revenue
- Identify best-selling products
- Track average order value
- Monitor conversion funnel

### 3. **Ad Performance**

**Tracked events:**
- `ad_impression` - When ad is shown
- `ad_click` - When ad is clicked
- Conversions from ad campaigns

**Metrics:**
```javascript
CTR (Click-Through Rate) = (ad_clicks / ad_impressions) × 100
Conversion Rate = (purchases_from_ad / ad_clicks) × 100
ROAS (Return on Ad Spend) = revenue_from_ad / ad_spend
```

### 4. **User Segmentation**

**Data collected:**
```javascript
{
  userId: 'user-abc123',
  email: 'user@demo.com',
  sessionId: 'session-xyz789',
  userAgent: 'Mozilla/5.0...',
  screenWidth: 1920,
  screenHeight: 1080
}
```

**Segments you can create:**
- High-value customers (>R50,000 purchases)
- Cart abandoners (add_to_cart but no purchase)
- Window shoppers (many views, no adds to cart)
- Mobile vs Desktop users

---

## 🛠️ Building the Stream Processor (Next Step)

Currently, events go to Kafka but aren't being consumed. Here's what the Stream Processor will do:

### Stream Processor Architecture

```python
# services/stream-processor/processor.py

from kafka import KafkaConsumer
import asyncpg
import json

async def process_events():
    # Connect to Kafka
    consumer = KafkaConsumer(
        'user_events',
        bootstrap_servers='localhost:9092',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host='localhost',
        port=5433,
        database='event_db',
        user='postgres',
        password='postgres'
    )
    
    # Process events
    for message in consumer:
        event = message.value
        
        # Save to database
        await conn.execute('''
            INSERT INTO events (
                event_name, user_id, session_id, 
                properties, timestamp
            ) VALUES ($1, $2, $3, $4, $5)
        ''', 
            event['eventName'],
            event.get('userId'),
            event.get('sessionId'),
            json.dumps(event.get('properties')),
            event['timestamp']
        )
        
        # Update user profile
        if event['eventName'] == 'purchase':
            await update_user_ltv(conn, event)
        
        # Trigger ML model updates
        if event['eventName'] in ['product_view', 'purchase']:
            await queue_ml_update(event)
```

---

## 📊 Data Visualization (Grafana)

### Access Grafana Dashboard
```
http://localhost:3000
Default: admin / admin
```

### Create Dashboards For:
1. **Real-Time Metrics**
   - Events per second
   - Active users
   - Error rates

2. **Business Metrics**
   - Revenue over time
   - Conversion funnel
   - Top products

3. **Ad Performance**
   - Impressions vs Clicks
   - Campaign ROI
   - Cost per acquisition

---

## 🔐 Data Privacy & Compliance

### GDPR Compliance
```javascript
// User can opt out
tracker.respectDoNotTrack = true;

// Reset user data
tracker.reset();
```

### Data You Track:
- ✅ User interactions (clicks, views)
- ✅ Purchase history
- ✅ Session data
- ❌ Personal identifying info (unless provided)
- ❌ Passwords
- ❌ Payment details

---

## 🚀 Next Steps

### 1. Build Stream Processor
Create service to consume from Kafka and write to PostgreSQL

### 2. Implement ML Recommendations
- Collaborative filtering
- Product similarity
- User preference learning

### 3. Create Analytics Dashboard
- Real-time metrics
- Business intelligence
- A/B test results

### 4. Add Data Export
- CSV exports
- API endpoints for data access
- Scheduled reports

---

## 💡 Quick Commands Reference

### Check Kafka Events
```powershell
# View latest events
docker exec -it kafka-server kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic user_events \
  --from-beginning --max-messages 10
```

### Check PostgreSQL (future)
```powershell
docker exec -it postgres-db psql -U postgres -d event_db -c \
  "SELECT COUNT(*) FROM events;"
```

### Monitor API Logs
```powershell
# In event-collector directory
cd "c:\Users\griff\Downloads\Ad Recommendation Model\services\event-collector"
python -m poetry run uvicorn app.main:app --reload --port 8001
```

### View Real-Time Events
Open the demo and watch the console at the bottom:
```
http://localhost:3000/demo.html
```

---

## 📧 Event Types Reference

| Event | When Triggered | Key Data |
|-------|---------------|----------|
| `page_view` | Page loads | url, title, referrer |
| `product_view` | Click product | productId, name, price |
| `add_to_cart` | Add to cart | productId, quantity |
| `remove_from_cart` | Remove from cart | productId |
| `checkout_started` | Click checkout | products[] |
| `purchase` | Complete order | orderId, revenue, products[] |
| `search` | Search products | query, results_count |
| `ad_impression` | Ad shown | adId, campaignId |
| `ad_click` | Ad clicked | adId, campaignId |
| `user_identify` | User logs in | userId, email |

---

## 🎯 Success Metrics

Track these KPIs:
- **Conversion Rate**: 2-5% typical for e-commerce
- **Cart Abandonment**: 70% average (aim to reduce)
- **Average Order Value**: Track trends
- **Customer Lifetime Value**: Sum of all purchases
- **Return Customer Rate**: % making 2+ purchases
