# Ad Recommendation Model - Algorithm Breakdown

## System Architecture Overview

The Ad Recommendation Model is a **real-time event tracking and ML-based recommendation system** for e-commerce. It works by collecting user behavior events and using machine learning to suggest products users are likely to purchase.

---

## 1. EVENT TRACKING SYSTEM

### What Gets Tracked

Every user interaction on the shopping page is captured:

```
- Page Views (when user visits the site)
- Product Views (when user looks at a product)  
- Add to Cart (when user adds a product)
- Purchases (when user buys a product)
- Search Events (when user searches for products)
- Category Browsing (when user browses categories)
```

### How Events Flow

```
Browser (User Action)
        ↓
JavaScript Tracker (demo.html)
        ↓
Event Batch Queue (collected every 5 seconds)
        ↓
HTTP POST to FastAPI (port 8002)
        ↓
Event Collector Service
        ↓
Kafka Topic (Real-time Stream)
        ↓
Kafka Topic → Stream Processor
        ↓
PostgreSQL Database (Stored)
        ↓
Redis Cache (Quick Lookup)
```

### Example Event Data

When you click "Add to Cart" on a gaming laptop:

```json
{
  "event_type": "add_to_cart",
  "user_id": "user-abc123xyz",
  "product_id": "prod-001",
  "product_name": "Gaming Laptop Pro X1",
  "category": "gaming",
  "price": 15999,
  "timestamp": "2026-02-24T14:30:45Z",
  "session_id": "session-abc123"
}
```

---

## 2. THE RECOMMENDATION ALGORITHM

### Core Logic: Collaborative Filtering + Content-Based

The system uses **hybrid recommendation** combining two approaches:

#### A. Collaborative Filtering
- **Idea**: "Users who viewed X also viewed Y"
- **How**: Find users with similar viewing patterns
- **Example**: If User A viewed gaming chairs & keyboards, and User B viewed gaming chairs, recommend keyboards to User B

#### B. Content-Based Filtering  
- **Idea**: "If you like X category, you'll like similar products"
- **How**: Match product attributes (brand, category, price range)
- **Example**: If you viewed 144Hz gaming monitors, recommend other 144Hz monitors

#### C. Scoring Algorithm

```
Match Score = (0.4 × Category Match) + (0.3 × Brand Match) + (0.2 × Price Range) + (0.1 × Trend)

Category Match: Does product match user's browsing history?
Brand Match: Is it from brands the user preferred?
Price Range: Is it in a similar price tier?
Trend: Is this product currently popular?
```

---

## 3. PRODUCT CATEGORIES & DATA

### Current Product Inventory (34 Products)

**Gaming (5 products)**
- Gaming Laptop Pro X1 (15,999 ZAR)
- Ergonomic Gaming Chair (3,999 ZAR)
- Ultrawide 34" Monitor (8,999 ZAR)
- Gaming Desk XL (4,999 ZAR)
- VR Headset Pro (6,999 ZAR)

**Peripherals (5 products)**
- RGB Mechanical Keyboard (1,299 ZAR)
- Pro Gaming Mouse X1 (799 ZAR)
- Graphics Drawing Tablet (2,499 ZAR)
- Wireless Mouse Pad RGB (599 ZAR)
- Mechanical Numpad (449 ZAR)

**Accessories (11 products)**
- Wireless Gaming Headset (899 ZAR)
- USB-C Hub Pro (499 ZAR)
- Aluminum Laptop Stand (299 ZAR)
- 4K Webcam Pro (1,499 ZAR)
- Portable SSD 1TB (1,899 ZAR)
- Studio Monitor Speakers (3,499 ZAR)
- Smart LED Light Strip (399 ZAR)
- Capture Card 4K (1,999 ZAR)
- Premium Laptop Backpack (899 ZAR)
- Thunderbolt Dock (2,999 ZAR)
- Studio Microphone (1,799 ZAR)
- Cable Management Kit (199 ZAR)

**Laptops & Displays (2 products)**
- Business Ultrabook (11,999 ZAR)
- Portable Monitor 15.6" (2,499 ZAR)

**Smartphones (2 products)**
- iPhone 15 Pro Max (12,999 ZAR)
- Samsung Galaxy S24 (11,999 ZAR)

**Tablets (2 products)**
- iPad Pro 12.9" (9,999 ZAR)
- Samsung Galaxy Tab S9 (8,999 ZAR)

**Displays (2 products)**
- UltraHD 4K Monitor (6,999 ZAR)
- Curved Gaming Monitor (5,999 ZAR)

**Networking (2 products)**
- Wireless Router WiFi 7 (3,499 ZAR)
- USB-C Hub 15 Ports (1,999 ZAR)

**Storage (2 products)**
- NAS Storage 12TB (4,999 ZAR)
- SSD External 4TB (2,799 ZAR)

---

## 4. DATA FLOW & PROCESSING

### Step 1: Event Collection (Real-Time)
```
User browsing → JavaScript captures action → Batched (every 5 seconds)
```

### Step 2: Event Validation (FastAPI)
```
Check if:
- User ID is valid
- Product ID exists in catalog
- Event type is recognized
- Timestamp is recent
```

### Step 3: Stream Processing (Kafka)
```
Raw events → Kafka topic → Stream processor enriches data:
- Add user profile
- Add product details
- Calculate relevance scores
```

### Step 4: Database Storage (PostgreSQL)
```
Events stored in tables:
- user_events (raw events)
- user_profiles (user info)
- product_views (aggregated view counts)
- user_preferences (derived interests)
```

### Step 5: Caching (Redis)
```
Frequently accessed data cached:
- Top 10 recommended products
- User preferences
- Category popularity
- Product view counts
```

---

## 5. REAL-TIME EVENT TRACKING CONSOLE

### Visual Feedback System

The **Event Drawer** (blue button, bottom-right) shows:

```
┌─────────────────────────────────────┐
│ Real-time Events        ✕           │ ← Close button
├─────────────────────────────────────┤
│ [13] events              ← Counter   │
├─────────────────────────────────────┤
│ PRODUCT VIEW (14:30:45)              │
│ productId: prod-001                  │
│ productName: Gaming Laptop Pro X1    │
├─────────────────────────────────────┤
│ ADD TO CART (14:30:52)               │
│ quantity: 1                          │
│ price: 15999                         │
├─────────────────────────────────────┤
│ AD IMPRESSION (14:31:02)             │
│ adId: ad-gaming-001                  │
│ score: 87%                           │
└─────────────────────────────────────┘
```

**Color Coding:**
- 🟣 PRODUCT_VIEW = Purple
- 🔴 ADD_TO_CART = Red  
- 🟠 AD_IMPRESSION = Orange

---

## 6. RECOMMENDATION GENERATION PIPELINE

### Request Flow

```
User clicks "Recommendations" 
        ↓
Browser sends GET /recommendations/{userId}
        ↓
FastAPI calls ML model
        ↓
Model queries user history from PostgreSQL
        ↓
Model queries Redis cache (precomputed scores)
        ↓
Hybrid algorithm scores all 34 products
        ↓
Top 6-10 products ranked by score
        ↓
Return with "% Match" badges (73%, 65%, 58%, etc.)
        ↓
Display in recommendations.html page
```

### Match Score Interpretation

- **90%+ Match**: High confidence recommendation
- **70-89% Match**: Good recommendation
- **50-69% Match**: Possible interest
- **<50% Match**: Low priority

---

## 7. KEY METRICS TRACKED

### Per User:
- Total products viewed
- Time spent on each product
- Categories browsed
- Purchase history
- Average price range preferred
- Favorite brands

### Per Product:
- Total views
- Add to cart rate
- Purchase rate
- Avg time to purchase
- Popular with which user segments

### System:
- Total events processed
- Event latency (ms)
- Cache hit rate
- Database query time
- Recommendation accuracy

---

## 8. TECHNOLOGY STACK

| Component | Technology | Port |
|-----------|-----------|------|
| Frontend | HTML/CSS/JavaScript | Browser |
| API | FastAPI (Python) | 8002 |
| Stream | Kafka + Zookeeper | 9092 |
| Database | PostgreSQL (TimescaleDB) | 5433 |
| Cache | Redis | 6379 |
| ML Model | Scikit-learn / NumPy | Internal |

---

## 9. HOW TO USE THE SYSTEM

### For Shopping:
1. Browse products by category
2. Click on products to view details
3. Add items to cart
4. Watch real-time events in the drawer (blue button)
5. Get personalized recommendations based on your behavior

### For Analytics:
1. Check event tracking console for real-time data
2. Event drawer shows timestamp, product, category, price
3. Counter increases with each interaction
4. Click header to expand/collapse

### For ML Insights:
1. Visit "Recommendations" page
2. See personalized products with match scores
3. Higher % = higher confidence recommendation
4. Based on your browsing history

---

## 10. ALGORITHM OPTIMIZATION

The system continuously improves through:

1. **Real-time Learning**: Model updates as new events arrive
2. **A/B Testing**: Tests different algorithms against each other
3. **Cold Start Problem**: For new users, uses content-based recommendations
4. **Serendipity**: Occasionally recommends new categories to prevent filter bubbles
5. **Decay Function**: Older events weighted less than recent ones

```
Recent Event Weight = Initial Weight × e^(-decay_rate × days_old)
```

This ensures current interests matter more than old browsing history.

---

## Summary

The **Ad Recommendation Model** is a sophisticated system that:
- ✅ Captures every user action in real-time
- ✅ Processes events through Kafka streams
- ✅ Applies hybrid ML algorithms
- ✅ Provides personalized recommendations
- ✅ Displays real-time tracking feedback
- ✅ Continuously learns and optimizes

All while maintaining sub-second response times and caching strategies for optimal performance.
