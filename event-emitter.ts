/**
 * Event Emitter FSA - Pub/Sub with wildcards & error handling
 */
type Listener = (...args: any[]) => void | Promise<void>;
type ErrorHandler = (error: Error, event: string) => void;
interface ListenerMeta { fn: Listener; once: boolean; pattern: string; }

export class EventEmitter {
  private listeners = new Map<string, ListenerMeta[]>();
  private wildcardListeners: ListenerMeta[] = [];
  private errorHandler?: ErrorHandler;
  private maxListeners = 100;

  on(event: string, listener: Listener): this {
    if (typeof listener !== "function") throw new TypeError("Listener must be a function");
    this.addListener(event, listener, false);
    return this;
  }

  once(event: string, listener: Listener): this {
    if (typeof listener !== "function") throw new TypeError("Listener must be a function");
    this.addListener(event, listener, true);
    return this;
  }

  off(event: string, listener?: Listener): this {
    if (!listener) {
      event ? this.removeAllListeners(event) : this.removeAllListeners();
      return this;
    }
    if (this.isWildcard(event)) {
      this.wildcardListeners = this.wildcardListeners.filter(
        (m) => m.pattern !== event || m.fn !== listener
      );
    } else {
      const list = this.listeners.get(event);
      if (list) {
        const filtered = list.filter((m) => m.fn !== listener);
        filtered.length ? this.listeners.set(event, filtered) : this.listeners.delete(event);
      }
    }
    return this;
  }

  async emit(event: string, ...args: any[]): Promise<boolean> {
    const listeners = this.getMatchingListeners(event);
    if (!listeners.length) return false;
    const toRemove: Array<{ event: string; meta: ListenerMeta }> = [];
    for (const { event: matchedEvent, meta } of listeners) {
      try {
        await meta.fn(...args);
        if (meta.once) toRemove.push({ event: matchedEvent, meta });
      } catch (error) {
        this.handleError(error as Error, event);
      }
    }
    toRemove.forEach(({ event: evt, meta }) => this.off(evt, meta.fn));
    return true;
  }

  onError(handler: ErrorHandler): this {
    this.errorHandler = handler;
    return this;
  }

  setMaxListeners(n: number): this {
    if (n < 0 || !Number.isInteger(n)) throw new Error("Max listeners must be non-negative integer");
    this.maxListeners = n;
    return this;
  }

  listenerCount(event: string): number {
    return this.getMatchingListeners(event).length;
  }

  removeAllListeners(event?: string): this {
    if (!event) {
      this.listeners.clear();
      this.wildcardListeners = [];
    } else if (this.isWildcard(event)) {
      this.wildcardListeners = this.wildcardListeners.filter((m) => m.pattern !== event);
    } else {
      this.listeners.delete(event);
    }
    return this;
  }

  private addListener(event: string, listener: Listener, once: boolean): void {
    const meta: ListenerMeta = { fn: listener, once, pattern: event };
    if (this.isWildcard(event)) {
      this.checkMaxListeners(this.wildcardListeners.length);
      this.wildcardListeners.push(meta);
    } else {
      const list = this.listeners.get(event) || [];
      this.checkMaxListeners(list.length);
      list.push(meta);
      this.listeners.set(event, list);
    }
  }

  private getMatchingListeners(event: string): Array<{ event: string; meta: ListenerMeta }> {
    const result: Array<{ event: string; meta: ListenerMeta }> = [];
    const exact = this.listeners.get(event);
    if (exact) exact.forEach((meta) => result.push({ event, meta }));
    this.wildcardListeners.forEach((meta) => {
      if (this.matchesPattern(event, meta.pattern)) {
        result.push({ event: meta.pattern, meta });
      }
    });
    return result;
  }

  private isWildcard(pattern: string): boolean {
    return pattern.includes("*");
  }

  private matchesPattern(event: string, pattern: string): boolean {
    if (pattern === "*") return true;
    if (pattern === event) return true;
    const regex = new RegExp("^" + pattern.replace(/\./g, "\\.").replace(/\*/g, ".*") + "$");
    return regex.test(event);
  }

  private checkMaxListeners(count: number): void {
    if (this.maxListeners > 0 && count >= this.maxListeners) {
      console.warn(`Max listeners (${this.maxListeners}) exceeded. Possible memory leak.`);
    }
  }

  private handleError(error: Error, event: string): void {
    if (this.errorHandler) {
      try {
        this.errorHandler(error, event);
      } catch (err) {
        console.error("Error in error handler:", err);
      }
    } else {
      console.error(`Error in event '${event}':`, error);
    }
  }
}
