export function getParameterFromUrl(name: string) {
  if (typeof window === "undefined") {
    return undefined;
  }
  const urlParams = new URLSearchParams(window.location.search);
  const value = urlParams.get(name);
  if (value) {
    return value;
  }
  return undefined;
}

export function getParameter(name: string): string {
  // Try to extract from location first
  console.info("AI Engine: getParameter", name);
  let value = getParameterFromUrl(name);
  if (value) {
    return value;
  }
  if (typeof window === "undefined") {
    return "";
  }
  if (window.chatConfig?.[name as keyof typeof window.chatConfig]) {
    return window.chatConfig?.[
      name as keyof typeof window.chatConfig
    ] as string;
  }
  // Try to extract from localStorage
  const chatStore = localStorage.getItem("chat-store");
  if (!chatStore) {
    return "";
  }
  value = JSON.parse(chatStore).state[name];
  if (value) {
    return value;
  }
  return "";
}

export function getDisplayFloatingChatIntro() {
  if (typeof window === "undefined") {
    return false;
  }
  return window.chatConfig?.displayFloatingChatIntro ?? false;
}

export function getOrganisationName() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.chatConfig?.organisation_name ?? "";
}
