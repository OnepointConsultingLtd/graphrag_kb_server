import { useShallow } from "zustand/react/shallow";
import useChatStore from "../context/chatStore";
import { useState } from "react";
import { fetchProjects } from "../lib/apiClient";
import type { Message } from "../model/message";
import { MessageType } from "../model/message";
import MessageAlert from "./MessageAlert";
import CenteredLayout from "./CenteredLayout";

export default function Login() {
    const [localJwt, setLocalJwt] = useState("");
    const [message, setMessage] = useState<Message | null>(null);

    const { setJwt, setProjects } = useChatStore(useShallow((state) => ({
        setJwt: state.setJwt,
        setProjects: state.setProjects,
    })));

    function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        if (localJwt) {
            fetchProjects(localJwt)
                .then((projects) => {
                    setJwt(localJwt);
                    setProjects(projects);
                })
                .catch((error) => {
                    setLocalJwt((_) => {
                        setJwt("");
                        setMessage({
                            messageType: MessageType.ERROR,
                            content: error.message,
                        });
                        return "";
                    });
                    console.error(error);
                });
        }
    }

    return (
        <CenteredLayout title="Login">
            <MessageAlert message={message} />
            <form className="w-full" onSubmit={handleSubmit}>
                <fieldset className="fieldset">
                    <legend className="fieldset-legend">Enter your token</legend>
                    <input type="text" className="input w-full" placeholder="Type here" name="token"
                        value={localJwt} onChange={(e) => setLocalJwt(e.target.value)} />
                    <p className="label">Enter your token with the permission to access the chat</p>
                </fieldset>
                <div className="w-full flex justify-end">
                    <button className="btn btn-primary w-[200px]" type="submit" disabled={!localJwt}>Login</button>
                </div>
            </form>
        </CenteredLayout>
    );
}