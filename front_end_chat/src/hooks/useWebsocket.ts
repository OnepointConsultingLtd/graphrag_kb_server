import { useEffect } from "react";
import useChatStore from "../context/chatStore";
import { ChatMessageType } from "../model/message";
import { WebsocketServerEventOptions } from "../model/websocket";


function createChatMessage(text: string, conversationId: string | null) {
    return {
        id: crypto.randomUUID(),
        text,
        type: ChatMessageType.AGENT,
        timestamp: new Date(),
        ...(conversationId ? {conversationId: conversationId} : {}),
        references: [],
    }
}

export default function useWebsocket() {
    const { socket, conversationId, appendToLastChatMessage, addChatMessage } = useChatStore();
    useEffect(() => {
        function onConnect() {
            console.info("Connected to websocket");
        }

        function onDisconnect() {
            console.info("Disconnected from websocket");
        }

        function onStreamStart(data: string) {
            console.info(`Stream started: ${data}`);
            addChatMessage(createChatMessage("Thinking...", conversationId));
        }

        function onStreamToken(token: string) {
            appendToLastChatMessage(token);
        }

        function onStreamEnd(data: string) {
            console.info(`Stream ended: ${data}`);
        }

        function onError(error: string) {
            console.error(`Error: ${error}`);
            addChatMessage(createChatMessage(`Error: ${error}`, conversationId));
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
        }
    }, [socket, conversationId, appendToLastChatMessage, addChatMessage]);
}