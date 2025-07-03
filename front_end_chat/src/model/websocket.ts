export const WebsocketEventOptions = {
  CONNECT: "connect",
  START_SESSION: "start_session",
  CHAT_STREAM: "chat_stream",
} as const;

export type WebsocketEvent = "connect" | "start_session" | "chat_stream";

export const WebsocketServerEventOptions = {
  CONNECT: "connect",
  DISCONNECT: "disconnect",
  START_SESSION: "start_session",
  STREAM_START: "stream_start",
  STREAM_TOKEN: "stream_token",
  STREAM_END: "stream_end",
  ERROR: "error",
};

export type WebsocketServerEvent =
  | "connect"
  | "start_session"
  | "stream_token"
  | "stream_end";
