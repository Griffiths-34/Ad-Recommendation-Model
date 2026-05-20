# Quick Reference: Interest Tracking & Recommendations

## **One-Sentence Summary**
Every user action signals interest → feeds into an ML algorithm that predicts what complementary products they'll want → pops up as a dismissible notification → learns from their response.

---

## **The Three Pillars**

### 🎯 **Interest Measurement**
- **Product View**: +10 points (they looked at it)
- **Add to Cart**: +25 points (they want it)
- **Purchase**: +50 points (they bought it!)
- **System learns**: What categories/brands/prices this user loves

### 🧠 **Recommendation Algorithm**
- **40% Collaborative**: "Users like you also buy X"
- **30% Content-Based**: "X is similar to what you liked"
- **20% Price Compatibility**: "X matches your budget tier"
- **10% Trend**: "X is hot this week"
- **Result**: Match score (0-100%)

### 🔔 **Complementary Product Pop-Up**
- Shows when user adds item to cart
- Displays 1 related product with match reason
- User can: Add to Cart, Dismiss, or auto-dismiss in 8 seconds
- All responses tracked for learning

---

## **Real Example: Gaming Laptop**

**User Action**: Clicks Add to Cart on Gaming Laptop (R15,999)

**System Thinks**:
```
Collaborative: 45% of laptop buyers also buy monitors → +45 points
Content-Based: Monitors are gaming category → +30 points
Price Compatibility: Ultrawide monitors in same tier → +20 points
Trend: Monitors popular this week → +10 points
───────────────────────────────────────
TOTAL: 105 → Normalized to 86% Match Score
```

**What Happens**:
```
1. Product added to cart ✓
2. Pop-up slides in from bottom-left
3. Shows: Ultrawide Monitor image, "Frequently Bought Together", R8,999
4. Options: [Add to Cart] [Not Now] (or wait 8 seconds)
5. Tracks user choice for future recommendations
```

---

## **Complementary Product Logic**

| If User Adds... | Recommend... | Why |
|---|---|---|
| Gaming Laptop | Ultrawide Monitor | Same gaming category + 80% co-purchase rate |
| Mechanical Keyboard | Pro Mouse | Peripherals used together |
| Webcam | Capture Card | Common for streamers/creators |
| Laptop | USB Dock | Expansion for connectivity |
| Gaming Chair | Desk | Complete gaming setup |
| Headset | Mechanical Keyboard | Gamer bundle |

---

## **Data Flow (Simplified)**

```
Browser Event → Tracker SDK → API → Kafka → Stream Processor → Redis Cache → Recommendations
├─ User clicks
├─ Add to Cart
└─ Badge +1
   └─ Enriched with
      metadata
      └─ Sent in batch
         (5 events or 5s)
         └─ Queued for
            processing
            └─ Calculates
               match scores
               └─ Stores in
                  cache for
                  instant lookup
                  └─ User sees
                     personalized
                     results
```

---

## **Key Metrics Tracked**

| Metric | What It Shows |
|--------|---------------|
| **View Count** | How many users looked at product |
| **Add-to-Cart Rate** | % of viewers who wanted it |
| **Recommendation Acceptance** | % who bought recommended item |
| **Match Score Accuracy** | Are recommendations actually relevant? |
| **Session Duration** | How engaged is this user? |
| **Conversion Rate** | % of browsers who become buyers |

---

## **Example Events Logged**

```javascript
// Event 1: User browses product
{
  type: "product_view",
  productId: "prod-001",
  timeSpent: 4.2, // seconds
  timestamp: 1708867234
}

// Event 2: User adds to cart
{
  type: "add_to_cart",
  productId: "prod-001",
  triggeredRecommendation: "prod-007",
  timestamp: 1708867255
}

// Event 3: User accepts recommendation
{
  type: "recommendation_accepted",
  recommendedProductId: "prod-007",
  source: "add_to_cart_notification",
  timeUntilAccept: 2.1, // seconds after pop-up
  timestamp: 1708867257
}

// Event 4: User makes purchase
{
  type: "purchase",
  itemIds: ["prod-001", "prod-007"],
  totalValue: 24998,
  timestamp: 1708867890
}
```

---

## **Why This System is Smart**

✅ **Real-Time**: Kafka + Redis = instant responses (<100ms)
✅ **Adaptive**: Learns from every single user interaction
✅ **Accurate**: Multiple data signals per recommendation
✅ **Non-Intrusive**: Dismissible notifications, auto-hide after 8s
✅ **Measurable**: Track acceptance rate, optimize continuously
✅ **Scalable**: Handles millions of users & events/day

---

## **The Virtuous Cycle**

```
Better Recommendations
         ↑
         └── More Purchases
                 ↑
                 └── More Training Data
                         ↑
                         └── Algorithm Gets Smarter
                                 ↑
                                 └── Back to Better Recommendations
```

Each purchase teaches the system what recommendations actually convert, making next user's experience even better! 📈
