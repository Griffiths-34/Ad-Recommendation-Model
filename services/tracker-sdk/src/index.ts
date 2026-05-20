/**
 * Ad Platform Tracker SDK
 * 
 * Production-ready client-side tracking library for capturing user behavior
 * and events for the ad recommendation platform.
 * 
 * Features:
 * - Automatic page view tracking
 * - User identification and session management
 * - Privacy-compliant (GDPR, CCPA)
 * - Configurable event batching
 * - Retry logic with exponential backoff
 * - TypeScript support
 */

export interface TrackerConfig {
  apiEndpoint: string;
  apiKey?: string;
  batchSize?: number;
  batchInterval?: number;
  debug?: boolean;
  autoTrack?: boolean;
  respectDoNotTrack?: boolean;
  sessionTimeout?: number;
  cookieDomain?: string;
  cookieExpiry?: number;
  useLocalStorage?: boolean;
}

export interface UserProperties {
  userId?: string;
  email?: string;
  name?: string;
  customProperties?: Record<string, any>;
}

export interface EventProperties {
  eventName: string;
  properties?: Record<string, any>;
  timestamp?: number;
  userId?: string;
  sessionId?: string;
}

export interface PageViewEvent {
  url: string;
  title: string;
  referrer: string;
  path: string;
}

export interface ProductEvent {
  productId: string;
  productName: string;
  category?: string;
  price?: number;
  currency?: string;
  brand?: string;
  variant?: string;
  quantity?: number;
}

export interface SearchEvent {
  searchTerm: string;
  resultsCount?: number;
  filters?: Record<string, any>;
}

export interface EcommerceEvent {
  orderId: string;
  revenue: number;
  currency: string;
  products: ProductEvent[];
  coupon?: string;
  shipping?: number;
  tax?: number;
}

export class AdTracker {
  private config: Required<TrackerConfig>;
  private eventQueue: EventProperties[] = [];
  private userId: string | null = null;
  private sessionId: string;
  private batchTimer: number | null = null;
  private isInitialized: boolean = false;
  private retryCount: number = 0;
  private maxRetries: number = 3;

  constructor(config: TrackerConfig) {
    this.config = {
      apiEndpoint: config.apiEndpoint,
      apiKey: config.apiKey || '',
      batchSize: config.batchSize || 10,
      batchInterval: config.batchInterval || 5000,
      debug: config.debug || false,
      autoTrack: config.autoTrack !== false,
      respectDoNotTrack: config.respectDoNotTrack !== false,
      sessionTimeout: config.sessionTimeout || 30 * 60 * 1000, // 30 minutes
      cookieDomain: config.cookieDomain || window.location.hostname,
      cookieExpiry: config.cookieExpiry || 365, // days
      useLocalStorage: config.useLocalStorage !== false,
    };

    this.sessionId = this.getOrCreateSessionId();
    this.userId = this.loadUserId();

    this.initialize();
  }

  /**
   * Initialize the tracker
   */
  private initialize(): void {
    if (this.isInitialized) {
      return;
    }

    // Check Do Not Track
    if (this.config.respectDoNotTrack && this.isDoNotTrackEnabled()) {
      this.log('Do Not Track is enabled. Tracking disabled.');
      return;
    }

    // Auto-track page views
    if (this.config.autoTrack) {
      this.trackPageView();
      
      // Track page views on history changes (SPA support)
      this.setupHistoryTracking();
    }

    // Set up visibility change tracking
    this.setupVisibilityTracking();

    // Set up beforeunload to flush events
    window.addEventListener('beforeunload', () => {
      this.flush(true);
    });

    // Start batch timer
    this.startBatchTimer();

    this.isInitialized = true;
    this.log('Tracker initialized', this.config);
  }

  /**
   * Identify a user
   */
  public identify(userId: string, properties?: UserProperties): void {
    this.userId = userId;
    this.saveUserId(userId);

    this.track('user_identify', {
      userId,
      ...properties,
    });

    this.log('User identified', { userId, properties });
  }

  /**
   * Track a generic event
   */
  public track(eventName: string, properties?: Record<string, any>): void {
    const event: EventProperties = {
      eventName,
      properties: properties || {},
      timestamp: Date.now(),
      userId: this.userId || undefined,
      sessionId: this.sessionId,
    };

    this.addEventToQueue(event);
    this.log('Event tracked', event);
  }

  /**
   * Track a page view
   */
  public trackPageView(customProperties?: Record<string, any>): void {
    const pageView: PageViewEvent = {
      url: window.location.href,
      title: document.title,
      referrer: document.referrer,
      path: window.location.pathname,
    };

    this.track('page_view', {
      ...pageView,
      ...customProperties,
      screenWidth: window.screen.width,
      screenHeight: window.screen.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      userAgent: navigator.userAgent,
    });
  }

  /**
   * Track product view
   */
  public trackProductView(product: ProductEvent): void {
    this.track('product_view', product);
  }

  /**
   * Track add to cart
   */
  public trackAddToCart(product: ProductEvent): void {
    this.track('add_to_cart', product);
  }

  /**
   * Track remove from cart
   */
  public trackRemoveFromCart(product: ProductEvent): void {
    this.track('remove_from_cart', product);
  }

  /**
   * Track search
   */
  public trackSearch(searchEvent: SearchEvent): void {
    this.track('search', searchEvent);
  }

  /**
   * Track purchase/order
   */
  public trackPurchase(ecommerceEvent: EcommerceEvent): void {
    this.track('purchase', ecommerceEvent);
  }

  /**
   * Track checkout started
   */
  public trackCheckoutStarted(products: ProductEvent[]): void {
    this.track('checkout_started', { products });
  }

  /**
   * Track custom conversion event
   */
  public trackConversion(conversionName: string, value?: number, properties?: Record<string, any>): void {
    this.track('conversion', {
      conversionName,
      value,
      ...properties,
    });
  }

  /**
   * Track ad click
   */
  public trackAdClick(adId: string, campaignId: string, properties?: Record<string, any>): void {
    this.track('ad_click', {
      adId,
      campaignId,
      ...properties,
    });
  }

  /**
   * Track ad impression
   */
  public trackAdImpression(adId: string, campaignId: string, properties?: Record<string, any>): void {
    this.track('ad_impression', {
      adId,
      campaignId,
      ...properties,
    });
  }

  /**
   * Add event to queue and flush if needed
   */
  private addEventToQueue(event: EventProperties): void {
    this.eventQueue.push(event);

    if (this.eventQueue.length >= this.config.batchSize) {
      this.flush();
    }
  }

  /**
   * Flush all events in queue
   */
  public flush(sync: boolean = false): void {
    if (this.eventQueue.length === 0) {
      return;
    }

    const events = [...this.eventQueue];
    this.eventQueue = [];

    const payload = {
      events,
      metadata: {
        sdkVersion: '1.0.0',
        timestamp: Date.now(),
        sessionId: this.sessionId,
      },
    };

    if (sync) {
      // Use sendBeacon for synchronous sending (e.g., on page unload)
      this.sendBeacon(payload);
    } else {
      // Use fetch for async sending
      this.sendAsync(payload);
    }
  }

  /**
   * Send events asynchronously with retry logic
   */
  private async sendAsync(payload: any): Promise<void> {
    try {
      const response = await fetch(`${this.config.apiEndpoint}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(this.config.apiKey && { 'X-API-Key': this.config.apiKey }),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      this.retryCount = 0;
      this.log('Events sent successfully', payload);
    } catch (error) {
      this.handleSendError(payload, error);
    }
  }

  /**
   * Send events using sendBeacon (for page unload)
   */
  private sendBeacon(payload: any): void {
    const blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
    const sent = navigator.sendBeacon(`${this.config.apiEndpoint}/events`, blob);
    
    if (sent) {
      this.log('Events sent via beacon', payload);
    } else {
      this.log('Failed to send events via beacon', payload);
    }
  }

  /**
   * Handle send errors with exponential backoff retry
   */
  private handleSendError(payload: any, error: any): void {
    this.log('Error sending events', error);

    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      const backoffTime = Math.pow(2, this.retryCount) * 1000;
      
      this.log(`Retrying in ${backoffTime}ms (attempt ${this.retryCount}/${this.maxRetries})`);
      
      setTimeout(() => {
        this.sendAsync(payload);
      }, backoffTime);
    } else {
      this.log('Max retries reached. Events lost.', payload);
      this.retryCount = 0;
    }
  }

  /**
   * Start batch timer
   */
  private startBatchTimer(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }

    this.batchTimer = window.setInterval(() => {
      this.flush();
    }, this.config.batchInterval);
  }

  /**
   * Setup history tracking for SPAs
   */
  private setupHistoryTracking(): void {
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = (...args) => {
      originalPushState.apply(history, args);
      this.trackPageView();
    };

    history.replaceState = (...args) => {
      originalReplaceState.apply(history, args);
      this.trackPageView();
    };

    window.addEventListener('popstate', () => {
      this.trackPageView();
    });
  }

  /**
   * Setup visibility tracking
   */
  private setupVisibilityTracking(): void {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.track('page_hidden', { timestamp: Date.now() });
        this.flush(true);
      } else {
        this.track('page_visible', { timestamp: Date.now() });
      }
    });
  }

  /**
   * Get or create session ID
   */
  private getOrCreateSessionId(): string {
    const stored = this.getFromStorage('ad_session_id');
    const storedTime = this.getFromStorage('ad_session_time');

    if (stored && storedTime) {
      const elapsed = Date.now() - parseInt(storedTime);
      if (elapsed < this.config.sessionTimeout) {
        this.saveToStorage('ad_session_time', Date.now().toString());
        return stored;
      }
    }

    const newSessionId = this.generateId();
    this.saveToStorage('ad_session_id', newSessionId);
    this.saveToStorage('ad_session_time', Date.now().toString());
    return newSessionId;
  }

  /**
   * Load user ID from storage
   */
  private loadUserId(): string | null {
    return this.getFromStorage('ad_user_id');
  }

  /**
   * Save user ID to storage
   */
  private saveUserId(userId: string): void {
    this.saveToStorage('ad_user_id', userId);
  }

  /**
   * Generate unique ID
   */
  private generateId(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  /**
   * Check if Do Not Track is enabled
   */
  private isDoNotTrackEnabled(): boolean {
    return (
      navigator.doNotTrack === '1' ||
      (window as any).doNotTrack === '1' ||
      (navigator as any).msDoNotTrack === '1'
    );
  }

  /**
   * Save to storage (localStorage or cookie)
   */
  private saveToStorage(key: string, value: string): void {
    if (this.config.useLocalStorage && this.isLocalStorageAvailable()) {
      localStorage.setItem(key, value);
    } else {
      this.setCookie(key, value, this.config.cookieExpiry);
    }
  }

  /**
   * Get from storage (localStorage or cookie)
   */
  private getFromStorage(key: string): string | null {
    if (this.config.useLocalStorage && this.isLocalStorageAvailable()) {
      return localStorage.getItem(key);
    } else {
      return this.getCookie(key);
    }
  }

  /**
   * Check if localStorage is available
   */
  private isLocalStorageAvailable(): boolean {
    try {
      const test = '__storage_test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Set cookie
   */
  private setCookie(name: string, value: string, days: number): void {
    const expires = new Date(Date.now() + days * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; domain=${this.config.cookieDomain}; SameSite=Lax`;
  }

  /**
   * Get cookie
   */
  private getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return decodeURIComponent(parts.pop()!.split(';').shift()!);
    }
    return null;
  }

  /**
   * Debug logging
   */
  private log(message: string, data?: any): void {
    if (this.config.debug) {
      console.log(`[AdTracker] ${message}`, data || '');
    }
  }

  /**
   * Reset tracker (clear user ID and session)
   */
  public reset(): void {
    this.userId = null;
    this.sessionId = this.generateId();
    this.saveToStorage('ad_session_id', this.sessionId);
    if (this.config.useLocalStorage && this.isLocalStorageAvailable()) {
      localStorage.removeItem('ad_user_id');
    }
    this.log('Tracker reset');
  }

  /**
   * Destroy tracker (cleanup)
   */
  public destroy(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }
    this.flush(true);
    this.isInitialized = false;
    this.log('Tracker destroyed');
  }
}

// Export factory function
export function createTracker(config: TrackerConfig): AdTracker {
  return new AdTracker(config);
}

// Default export
export default AdTracker;
