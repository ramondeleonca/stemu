export type PywebviewAPI = {[functionName: string]: <T = unknown>(...args: unknown[]) => Promise<T>};
export type Pywebview<API extends PywebviewAPI = PywebviewAPI> = {
    api: API;
    domJSON: {
        toDOM: unknown;
        toJSON: unknown;
    };
    platform: "gtk" | "qt" | "edgechromium" | "cef" | "mshtml";
    stringify: unknown;
    token: string;
}

declare global {
    interface WindowEventMap {
        _pywebviewready: Event;
    }

    interface Window {
        pywebview: Pywebview;
    }
}
