// The base URL. Change this to reflect the domain you are operating on.
const BASE_HOST = "localhost:9999"
const BASE_SERVER = `http://${BASE_HOST}`;
const WEBSOCKET_SERVER = `ws://${BASE_HOST}`;

export function getBaseServer() {
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
