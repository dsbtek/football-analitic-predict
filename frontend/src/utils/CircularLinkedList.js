/**
 * Circular Linked List implementation for news items
 * Provides seamless cycling through news items with smooth transitions
 */

class NewsNode {
    constructor(data) {
        this.data = data;
        this.next = null;
        this.prev = null;
    }
}

class CircularLinkedList {
    constructor() {
        this.head = null;
        this.current = null;
        this.size = 0;
    }

    /**
     * Add a news item to the circular list
     * @param {Object} newsItem - The news item to add
     */
    add(newsItem) {
        const newNode = new NewsNode(newsItem);
        
        if (!this.head) {
            // First node - points to itself
            this.head = newNode;
            this.current = newNode;
            newNode.next = newNode;
            newNode.prev = newNode;
        } else {
            // Insert at the end (before head)
            const tail = this.head.prev;
            
            newNode.next = this.head;
            newNode.prev = tail;
            tail.next = newNode;
            this.head.prev = newNode;
        }
        
        this.size++;
    }

    /**
     * Remove all items and rebuild the list
     * @param {Array} newsItems - Array of news items
     */
    rebuild(newsItems) {
        this.clear();
        newsItems.forEach(item => this.add(item));
    }

    /**
     * Clear all items from the list
     */
    clear() {
        this.head = null;
        this.current = null;
        this.size = 0;
    }

    /**
     * Move to the next news item
     * @returns {Object|null} The next news item
     */
    next() {
        if (!this.current) return null;
        
        this.current = this.current.next;
        return this.current.data;
    }

    /**
     * Move to the previous news item
     * @returns {Object|null} The previous news item
     */
    previous() {
        if (!this.current) return null;
        
        this.current = this.current.prev;
        return this.current.data;
    }

    /**
     * Get the current news item without moving
     * @returns {Object|null} The current news item
     */
    getCurrent() {
        return this.current ? this.current.data : null;
    }

    /**
     * Jump to a specific index in the list
     * @param {number} index - The index to jump to
     * @returns {Object|null} The news item at the index
     */
    jumpTo(index) {
        if (!this.head || index < 0 || index >= this.size) return null;
        
        // Start from head and move to the desired index
        this.current = this.head;
        for (let i = 0; i < index; i++) {
            this.current = this.current.next;
        }
        
        return this.current.data;
    }

    /**
     * Get the current index
     * @returns {number} The current index
     */
    getCurrentIndex() {
        if (!this.current || !this.head) return -1;
        
        let index = 0;
        let node = this.head;
        
        while (node !== this.current && index < this.size) {
            node = node.next;
            index++;
        }
        
        return index;
    }

    /**
     * Get all items as an array (for display purposes)
     * @returns {Array} Array of all news items
     */
    toArray() {
        if (!this.head) return [];
        
        const items = [];
        let node = this.head;
        
        do {
            items.push(node.data);
            node = node.next;
        } while (node !== this.head);
        
        return items;
    }

    /**
     * Get the size of the list
     * @returns {number} Number of items in the list
     */
    getSize() {
        return this.size;
    }

    /**
     * Check if the list is empty
     * @returns {boolean} True if empty, false otherwise
     */
    isEmpty() {
        return this.size === 0;
    }

    /**
     * Get a preview of upcoming items (for UI indicators)
     * @param {number} count - Number of upcoming items to preview
     * @returns {Array} Array of upcoming news items
     */
    getUpcoming(count = 3) {
        if (!this.current || count <= 0) return [];
        
        const upcoming = [];
        let node = this.current.next;
        
        for (let i = 0; i < count && i < this.size - 1; i++) {
            upcoming.push(node.data);
            node = node.next;
        }
        
        return upcoming;
    }

    /**
     * Get a preview of previous items
     * @param {number} count - Number of previous items to preview
     * @returns {Array} Array of previous news items
     */
    getPrevious(count = 3) {
        if (!this.current || count <= 0) return [];
        
        const previous = [];
        let node = this.current.prev;
        
        for (let i = 0; i < count && i < this.size - 1; i++) {
            previous.unshift(node.data); // Add to beginning to maintain order
            node = node.prev;
        }
        
        return previous;
    }

    /**
     * Auto-advance to next item (for automatic cycling)
     * @returns {Object|null} The next news item
     */
    autoAdvance() {
        return this.next();
    }

    /**
     * Get items in a sliding window around current item
     * @param {number} windowSize - Size of the window (should be odd)
     * @returns {Array} Array of items in the window
     */
    getWindow(windowSize = 5) {
        if (!this.current || windowSize <= 0) return [];
        
        const window = [];
        const halfWindow = Math.floor(windowSize / 2);
        
        // Start from current - halfWindow
        let node = this.current;
        for (let i = 0; i < halfWindow; i++) {
            node = node.prev;
        }
        
        // Collect window items
        for (let i = 0; i < windowSize && i < this.size; i++) {
            window.push({
                item: node.data,
                isCurrent: node === this.current,
                index: i
            });
            node = node.next;
        }
        
        return window;
    }
}

export default CircularLinkedList;
