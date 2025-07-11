import useChatStore from "../../context/chatStore";
import { ChatType } from "../../lib/chatTypes";
import { Topics } from "../../model/topics";
import { useShallow } from "zustand/react/shallow";


function simplifyDescription(description: string) {
    if (!description) {
        return "";
    }
    return description.split("<SEP>")[0].split(".")[0].substring(0, 100) + " ...";
}

export default function TopicButtons({ topics, related }: { topics: Topics | null, related: boolean }) {
    const {
        chatType,
        selectedTopic,
        setSelectedTopic,
    } = useChatStore(
        useShallow((state) => ({
            chatType: state.chatType,
            selectedTopic: state.selectedTopic,
            setSelectedTopic: state.setSelectedTopic,
        }))
    );
    const isFloating = chatType === ChatType.FLOATING;
    return (
        <>
            {topics?.topics?.filter((topic) => topic.type).map((topic) => (
                <div
                    className={`flex flex-col items-left justify-top text-left cursor-pointer hover:bg-[var(--color-accent-content)] focus:bg-[var(--color-secondary)] p-2 rounded-lg ${selectedTopic?.name === topic.name ? "bg-[var(--color-secondary)]" : related ? "bg-[var(--color-info-content)]" : "bg-[var(--color-primary)]"}`}
                    key={`topic-${topic.name}-${topic.type}`}
                    onClick={() => setSelectedTopic(topic)}
                    title={isFloating ? topic.description : ""}
                >
                    <div className="flex flex-row justify-between gap-2">
                        <div className="text-white font-bold">{topic.name}</div>
                        {!isFloating && <div className="text-white">{topic.type}</div>}
                    </div>
                    <div className="w-full text-white text-sm">{simplifyDescription(topic.description)}</div>
                </div>
            ))}
        </>
    )
}