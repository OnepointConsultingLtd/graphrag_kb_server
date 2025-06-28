// Enumeration with the supported components of the chat app
export const AppComponent = {
    // The chat component
    CHAT: "chat",
    // The settings component
    FLOATING_CHAT: "FLOATING_CHAT",
    DASHBOARD: "DASHBOARD"
} as const;

export type AppComponentType = typeof AppComponent[keyof typeof AppComponent];