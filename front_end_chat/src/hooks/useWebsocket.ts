import { useEffect } from "react";
import useChatStore from "../context/chatStore";
import { ErrorMessage } from "../model/error";
import { WebsocketServerEventOptions } from "../model/websocket";
import { useShallow } from "zustand/react/shallow";
import { createChatMessage } from "../factory/chatMessageFactory";

export default function useWebsocket() {
  const {
    socket,
    conversationId,
    appendToLastChatMessage,
    addChatMessage,
    setIsThinking,
    scrollToBottom,
  } = useChatStore(
    useShallow((state) => ({
      socket: state.socket,
      conversationId: state.conversationId,
      appendToLastChatMessage: state.appendToLastChatMessage,
      addChatMessage: state.addChatMessage,
      setIsThinking: state.setIsThinking,
      scrollToBottom: state.scrollToBottom,
    })),
  );
  useEffect(() => {
    function onConnect() {
      console.info("Connected to websocket");
    }

    function onDisconnect() {
      console.info("Disconnected from websocket");
    }

    function onStreamStart() {
      setIsThinking(true);
    }

    function onStreamToken(token: string) {
      appendToLastChatMessage(token);
    }

    function onStreamEnd(data: string) {
      console.info(`Stream ended: ${data}`);
      scrollToBottom();
    }

    function onError(error: ErrorMessage) {
      console.error(`Error: ${error.message}`);
      addChatMessage(
        createChatMessage(`Error: ${error.message}`, conversationId),
      );
    }

    socket?.on(WebsocketServerEventOptions.CONNECT, onConnect);
    socket?.on(WebsocketServerEventOptions.DISCONNECT, onDisconnect);
    socket?.on(WebsocketServerEventOptions.STREAM_START, onStreamStart);
    socket?.on(WebsocketServerEventOptions.STREAM_TOKEN, onStreamToken);
    socket?.on(WebsocketServerEventOptions.STREAM_END, onStreamEnd);
    socket?.on(WebsocketServerEventOptions.ERROR, onError);

    return () => {
      socket?.off(WebsocketServerEventOptions.CONNECT, onConnect);
      socket?.off(WebsocketServerEventOptions.DISCONNECT, onDisconnect);
      socket?.off(WebsocketServerEventOptions.STREAM_START, onStreamStart);
      socket?.off(WebsocketServerEventOptions.STREAM_TOKEN, onStreamToken);
      socket?.off(WebsocketServerEventOptions.STREAM_END, onStreamEnd);
      socket?.off(WebsocketServerEventOptions.ERROR, onError);
    };
  }, [socket, conversationId, appendToLastChatMessage, addChatMessage]);
}
