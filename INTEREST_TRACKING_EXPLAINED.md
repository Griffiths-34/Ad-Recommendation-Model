# Interest Tracking & Recommendation System - Complete Breakdown

## **Overview**
The system measures user interest through behavioral tracking and recommends compatible products using a hybrid ML algorithm. Every action signals intent, which feeds into personalized recommendations.

---

## **PART 1: HOW WE MEASURE USER INTEREST**

### **1.1 The Interest Signals**

Every user action generates an event that records their interest level:

```
EVENT: Product View
├─ Weight: +10 points
├─ What it means: User browsed, spent time looking
├─ Data captured:
│  ├─ productId: "prod-001"
│  ├─ productName: "Gaming Laptop Pro X1"
│  ├─ category: "gaming"
│  ├─ price: 15999
│  ├─ brand: "TechPro"
│  ├─ timeSpent: 3.5 seconds
│  └─ timestamp: 1708867234

EVENT: Add to Cart
├─ Weight: +25 points
├─ What it means: User showed strong intent
├─ Data captured: [same as above]

EVENT: Purchase (Checkout Complete)
├─ Weight: +50 points
├─ What it means: Highest interest - conversion!
├─ Data captured: [same as above]

EVENT: Ad Impression (Complementary Product Shown)
├─ Weight: +5 points
├─ What it means: User saw recommendation
├─ Data captured:
│  ├─ adType: "complementary_product"
│  ├─ recommendedProductId: "prod-007"
│  ├─ triggeredBy: "prod-001"
│  └─ acceptanceRate: yes/no
```

### **1.2 Building User Interest Profile**

As user browses, system builds a profile:

```
User: user_12345

Session Events:
1. Views "Gaming Laptop Pro X1" (prod-001)
   → Category interest: gaming +10
   → Brand interest: TechPro +10
   → Price range: 15,000+ +10
   
2. Views "Ultrawide Monitor" (prod-007)
   → Category interest: gaming +10
   → Brand interest: ViewMax +10
   
3. ADDS TO CART: "Ergonomic Gaming Chair" (prod-006)
   → Category interest: gaming +25 (weighted heavily)
   → Brand interest: ComfortZone +25
   → Strong signal this user is a GAMER

Interest Profile Built:
{
  primaryCategories: ['gaming', 'peripherals'],
  primaryBrands: ['TechPro', 'ViewMax', 'ComfortZone'],
  priceRange: 'premium' (15,000+ ZAR),
  conversionLikelihood: 'HIGH',
  lastActivityTime: '2026-02-24 14:35:22',
  behaviorPattern: 'Quick browser → High intent buyer'
}
```

---

## **PART 2: HOW RECOMMENDATIONS ARE GENERATED**

### **2.1 The Hybrid Algorithm**

When user adds a product, system recommends compatible items using:

**A. Collaborative Filtering (45%)**
```
Logic: "Who else bought what this user is buying?"

User buys "Gaming Laptop" → 
Who else bought laptops? → 
  User #2542 → Also bought: Monitor, Chair, Mechanical Keyboard
  User #7834 → Also bought: Mouse, Headset, Laptop Stand
  User #9102 → Also bought: Monitor, RGB Lighting, SSD

Pattern: These products appear 80%+ of the time with gaming laptops
Recommendation: Suggest Monitor (highest co-purchase rate)
```

**B. Content-Based Filtering (35%)**
```
Logic: "What products are similar to what user is viewing?"

Gaming Laptop has:
├─ Category: gaming
├─ Price: 15,999 ZAR
├─ Performance tier: high-end
└─ Target user: gamers/professionals

Similar products:
├─ Gaming Chair (same category, complementary)
├─ Monitor (gaming category, common combo)
├─ GPU Dock (accessories for laptop)
└─ Mechanical Keyboard (peripherals for laptop)

Similarity Score:
- Monitor: 85% (same category, gaming focus, high-end)
- Chair: 82% (complementary, premium tier)
- Keyboard: 78% (common accessory, gaming-focused)
```

**C. Trend Factor (20%)**
```
Logic: "What's popular among similar users?"

Gaming Laptop users in last 30 days also viewed:
- 4K Monitors: +35% trend
- RGB Mechanical Keyboards: +28% trend
- VR Headsets: +22% trend
- Gaming Chairs: +40% trend

If trend is hot, boost recommendation score
```

### **2.2 Match Score Formula**

```
MATCH_SCORE = (0.40 × Category_Match) + 
              (0.30 × Brand_Affinity) + 
              (0.20 × Price_Compatibility) + 
              (0.10 × Trend_Signal)

Example Calculation for "Ultrawide Monitor" when user adds "Gaming Laptop":

Category Match: Gaming Laptop (gaming) → Monitor (gaming)
  Score: 95% (exact category match) × 0.40 = 38%

Brand Affinity: TechPro (laptop) → ViewMax (monitor)
  Score: 70% (different brands but both premium) × 0.30 = 21%

Price Compatibility: 15,999 → 8,999
  Score: 85% (matching premium tier) × 0.20 = 17%

Trend Signal: Monitors have +35% purchase trend this week
  Score: 100% (hot product) × 0.10 = 10%

TOTAL MATCH_SCORE = 38 + 21 + 17 + 10 = 86%

Display: "86% Match - Frequently Bought Together"
```

---

## **PART 3: THE COMPLEMENTARY PRODUCT FEATURE (NEW!)**

### **3.1 How It Works**

When user clicks "Add to Cart":

```
Flow:
1. addToCart(productId) is called
   ↓
2. Product added to cart
   ↓
3. Tracker records event (ad_impression)
   ↓
4. showComplementaryRecommendation() triggered
   ↓
5. Lookup: complementaryMap[productId]
   ├─ prod-001 (Gaming Laptop) → [prod-007, prod-006]
   ├─ (Monitor, Chair - most compatible)
   └─ Pick random one
   ↓
6. Pop-up notification slides in (bottom-left)
   ├─ Shows recommended product image
   ├─ Shows match reason (e.g., "Frequently Bought Together")
   ├─ Shows price
   └─ Two buttons: "Add to Cart" or "Not Now" (or auto-dismiss in 8s)
   ↓
7. User decision tracked:
   ├─ If "Add to Cart": addToCartQuiet() called (no double notification)
   ├─ If "Not Now": Recorded as recommendation rejection
   └─ Either way: trackAdImpression() logs interaction
```

### **3.2 Complementary Products Map**

```javascript
const complementaryMap = {
    'prod-001': ['prod-007', 'prod-006'],  // Gaming Laptop → Monitor, Chair
    'prod-002': ['prod-003', 'prod-013'],  // Keyboard → Mouse, Mousepad
    'prod-003': ['prod-002', 'prod-013'],  // Mouse → Keyboard, Mousepad
    'prod-004': ['prod-002', 'prod-007'],  // Headset → Keyboard, Monitor
    'prod-005': ['prod-001', 'prod-021'],  // USB Hub → Laptop, Dock
    'prod-006': ['prod-001', 'prod-007'],  // Chair → Laptop, Monitor
    'prod-007': ['prod-001', 'prod-006'],  // Monitor → Laptop, Chair
    'prod-008': ['prod-001', 'prod-021'],  // Laptop Stand → Laptop, Dock
    'prod-009': ['prod-002', 'prod-007'],  // Drawing Tablet → Keyboard, Monitor
    'prod-010': ['prod-004', 'prod-019'],  // Webcam → Headset, Capture Card
    'prod-012': ['prod-001', 'prod-021'],  // SSD → Laptop, Dock
    'prod-013': ['prod-002', 'prod-003'],  // Mousepad → Keyboard, Mouse
    'prod-014': ['prod-004', 'prod-010'],  // Speakers → Headset, Webcam
    'prod-015': ['prod-001', 'prod-002'],  // Numpad → Laptop, Keyboard
    'prod-016': ['prod-001', 'prod-007'],  // Desk → Laptop, Monitor
    'prod-017': ['prod-001', 'prod-006'],  // VR Headset → Laptop, Chair
    'prod-018': ['prod-001', 'prod-016'],  // LED Light → Laptop, Desk
    'prod-019': ['prod-010', 'prod-004'],  // Capture Card → Webcam, Headset
    'prod-020': ['prod-001', 'prod-012'],  // Backpack → Laptop, SSD
    'prod-021': ['prod-001', 'prod-012'],  // Dock → Laptop, SSD
};
```

Why these combos?
- **Gaming Laptop + Monitor**: Gamers need wide screens for immersion
- **Keyboard + Mouse**: Essential peripherals used together
- **Headset + Microphone**: Gaming streamers need both
- **Laptop + Dock**: Power users need connectivity expansion
- **Webcam + Capture Card**: Content creators bundle these

---

## **PART 4: EVENT TRACKING DATA FLOW**

### **4.1 Complete Journey**

```
┌─────────────────────────────────────────────────────┐
│ BROWSER: User Action                                │
│ "I want to add Gaming Laptop to cart"               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ JAVASCRIPT: Event Triggered                         │
│ addToCart('prod-001')                               │
│ ├─ Add to cart array                                │
│ ├─ Update cart count badge                          │
│ └─ Show notification "Added to cart!"               │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ TRACKER SDK: Enrich Event                           │
│ {                                                   │
│   event_type: "add_to_cart",                        │
│   productId: "prod-001",                            │
│   productName: "Gaming Laptop Pro X1",              │
│   category: "gaming",                               │
│   price: 15999,                                     │
│   brand: "TechPro",                                 │
│   timestamp: 1708867234123,                         │
│   user_id: "user_12345",                            │
│   session_id: "session_xyz789",                     │
│   device: "desktop"                                 │
│ }                                                   │
└─────────────────────────────────────────────────────┘
                        ↓ (batch with other events)
┌─────────────────────────────────────────────────────┐
│ HTTP: Send to Event Collector API                   │
│ POST http://localhost:8002/api/events               │
│ Body: { events: [...] }                             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ EVENT COLLECTOR (Python FastAPI)                    │
│ ├─ Validate event structure                         │
│ ├─ Enrich with server-side data                     │
│ └─ Publish to Kafka topic: "events"                 │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ KAFKA BROKER (Port 9092)                            │
│ Topic: "events"                                     │
│ Partition 3 (by user_id hash)                       │
│ Event queued for processing                         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ STREAM PROCESSOR                                    │
│ Consumes event from Kafka:                          │
│ ├─ Extract user interest signals                    │
│ ├─ Update user profile                              │
│ ├─ Run recommendation algorithm                     │
│ ├─ Calculate match scores                           │
│ └─ Select top 3-5 recommendations                   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ REDIS CACHE (Port 6379)                             │
│ Store computed recommendations:                     │
│ Key: "recommendations:user_12345"                   │
│ Value: [                                            │
│   {product_id: "prod-007", score: 86},              │
│   {product_id: "prod-006", score: 82},              │
│   {product_id: "prod-002", score: 75}               │
│ ]                                                   │
│ TTL: 24 hours                                       │
└─────────────────────────────────────────────────────┘
                        ↓ (user navigates to recommendations.html)
┌─────────────────────────────────────────────────────┐
│ RECOMMENDATIONS PAGE                                │
│ GET /api/recommendations/user_12345                 │
│ Returns cached results instantly                    │
│ Display match scores: "86% Match", "82% Match"...   │
└─────────────────────────────────────────────────────┘
```

---

## **PART 5: WHY THIS MATTERS**

### **5.1 Benefits**

| Aspect | Benefit |
|--------|---------|
| **Accuracy** | Multiple algorithms = 3+ data signals per recommendation |
| **Relevance** | Complementary products directly address user needs |
| **Speed** | Redis caching = <100ms response time |
| **Scalability** | Kafka + Streaming = handles millions of events/day |
| **Measurable** | Every interaction tracked = optimize over time |

### **5.2 Real-World Scenario**

```
Day 1 - Friday 2:35 PM
User adds "Gaming Laptop" to cart
→ System: "This user is a gamer"
→ Pop-up: "You might want an Ultrawide Monitor - 86% Match"
→ User clicks X (not interested now)
→ Event logged: recommendation_rejected

Day 1 - Friday 3:10 PM
User adds "Mechanical Keyboard" to cart
→ User now has: Laptop, Keyboard
→ System updates profile: "Serious gamer/content creator"
→ Pop-up: "You might want a Pro Gaming Mouse - 85% Match"
→ User clicks "Add to Cart"
→ Event logged: recommendation_accepted
→ Mouse + interest signals cached

Day 2 - Saturday 10:00 AM
User returns to site
→ System recognizes: user_12345
→ Fetches from cache: This user likes gaming peripherals
→ Homepage shows: Gaming monitors, chairs, headsets first
→ Personalization happens instantly

Day 3 - Sunday 6:00 PM
User navigates to Recommendations page
→ API query: "What should user_12345 buy next?"
→ Returns precomputed results from Redis:
  1. "Ultrawide Monitor 34"" - 86% Match (same category + co-purchase pattern)
  2. "Ergonomic Gaming Chair" - 82% Match (Frequently bought with laptops)
  3. "Wireless Gaming Headset" - 75% Match (Gaming bundle)
  4. "RGB Mechanical Numpad" - 68% Match (Keyboard bundle)
→ User buys monitor
→ Purchase event triggers stream processor
→ Recommendations updated for next visit
```

---

## **PART 6: CONTINUOUS IMPROVEMENT**

### **6.1 Learning Over Time**

```
Data Loop:
├─ User 1: Add Laptop → Buys Monitor (Match: 86%)
├─ User 2: Add Laptop → Rejects Monitor (Match: 86% but unsuitable)
├─ User 3: Add Laptop → Buys Chair (Match: 82%)
├─ User 4: Add Laptop → Buys Desk (Match: 79%)
│
System learns:
├─ Monitor is 80% relevant for this segment
├─ Chair is 90% relevant
├─ Desk is 75% relevant
│
Next recommendation for new user with laptop:
├─ Boost Chair recommendation priority
├─ Monitor moves down
├─ Personalize based on user segment
```

### **6.2 A/B Testing Opportunities**

```
Test: Notification timing
├─ Variant A: Show after 2 seconds (current)
├─ Variant B: Show immediately
├─ Variant C: Show after 5 seconds
└─ Measure: Acceptance rate

Test: Product selection strategy
├─ Variant A: Random complementary product (current)
├─ Variant B: Always highest match score
├─ Variant C: Highest margin product
└─ Measure: AOV (Average Order Value)

Test: Notification design
├─ Variant A: Current (slide-up from bottom-left)
├─ Variant B: Slide from right (like drawer)
├─ Variant C: Center modal
└─ Measure: CTR (Click-through Rate)
```

---

## **Summary: The Complete Picture**

```
Interest Measurement
    ↓
User browsing builds interest profile
(category, brand, price preferences)
    ↓
Event Tracking
    ↓
Every action (view, add, purchase) recorded
Sent via Kafka to stream processor
    ↓
ML Algorithm
    ↓
Hybrid approach: Collaborative + Content-Based
    ↓
Recommendation Generation
    ↓
Match scores calculated for all products
Top matches cached in Redis
    ↓
Complementary Product Pop-up
    ↓
When user adds item: Show best complementary product
Auto-dismiss in 8 seconds or user clicks X/Accept
    ↓
User Feedback Loop
    ↓
Acceptance/Rejection tracked
Updates recommendation engine
Improves future suggestions
```

This creates a **feedback loop**: Better recommendations → Higher acceptance → More purchase signals → Even better recommendations.

The system learns from every single user action and gets smarter over time! 🚀
