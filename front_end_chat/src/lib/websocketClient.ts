import { Socket } from "socket.io-client";
import { Query, convertQueryToQueryParameters } from "../model/query";
import { WebsocketEvent, WebsocketEventOptions } from "../model/websocket";

export function sendWebsocketQuery(socket: Socket<any, any> | null, jwt: string, query: Query) {
  safeEmit(
    socket,
    WebsocketEventOptions.CHAT_STREAM,
    jwt,
    query.project.name,
    convertQueryToQueryParameters(query),
  );
}

export function safeEmit(
  socket: Socket<any, any> | null,
  eventName: WebsocketEvent,
  ...args: any[]
) {
  if (!!socket) {
    socket.emit(eventName, ...args);
    console.info(`Sent ${eventName} message!`);
  } else {
    console.warn(`Socket is null, cannot send ${eventName} message.`);
  }
}
