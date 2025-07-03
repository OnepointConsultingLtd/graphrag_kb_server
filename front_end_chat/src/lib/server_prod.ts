// The base URL. Change this to reflect the domain you are operating on.
const BASE_SERVER = `//${location.host}`;
const WEBSOCKET_SERVER = `//${location.host}`;

export function getBaseServer() {
  console.log("window.chatConfig?.baseServer", window.chatConfig?.baseServer);
  if (window.chatConfig?.baseServer) {
    return window.chatConfig.baseServer;
  }
  return BASE_SERVER;
}

export function getWebsocketServer() {
  if (window.chatConfig?.websocketServer) {
    return window.chatConfig.websocketServer;
  }
  return WEBSOCKET_SERVER;
}