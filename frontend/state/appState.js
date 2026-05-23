/**
 * Lightweight Frontend State Container
 * Replaces global scattered mutations with a centralized store and Pub/Sub model.
 */

const listeners = new Set();

export const state = {
    marketSnapshot: null,
    portfolio: null,
    explainability: null,
    confidence: null,
    previousSnapshot: null
};

export function updateState(newState) {
    Object.assign(state, newState);
    notifyListeners();
}

export function subscribe(callback) {
    listeners.add(callback);
    return () => listeners.delete(callback); // Returns unsubscribe function
}

function notifyListeners() {
    for (const callback of listeners) {
        try {
            callback(state);
        } catch (e) {
            console.error("Error in state subscriber:", e);
        }
    }
}
