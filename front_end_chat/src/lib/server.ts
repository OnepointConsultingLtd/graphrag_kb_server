// The base URL. Change this to reflect the domain you are operating on.
const BASE_SERVER = "http://localhost:9999";

export function getBaseServer() {
  if (window.chatConfig?.baseServer) {
    return window.chatConfig.baseServer;
  }
  return BASE_SERVER;
}
