import useChatStore from "../../context/chatStore";
import { ChatType } from "../../lib/chatTypes";
import { Topics } from "../../model/topics";
import { useShallow } from "zustand/react/shallow";
import { MdExpandLess, MdExpandMore } from "react-icons/md";

function splitDescription(description: string): string[] {
  if (!description) {
    return [];
  }
  return description.split("<SEP>");
}

function simplifyDescription(description: string) {
  if (!description) {
    return "";
  }
  return splitDescription(description)[0].split(".")[0].substring(0, 100) + " ...";
}

function DescriptionViewer({ descriptionParts }: { descriptionParts: string[] }) {
  return (
    <div className="w-full text-white text-sm">
      {descriptionParts.map((part, index) => <div key={`${index}-${part}`}>{part}</div>)}
    </div>
  )
}

export default function TopicButtons({
  topics,
  related,
}: {
  topics: Topics | null;
  related: boolean;
}) {
  const { chatType, selectedTopic, setSelectedTopic, injectTopicDescription } = useChatStore(
    useShallow((state) => ({
      chatType: state.chatType,
      selectedTopic: state.selectedTopic,
      setSelectedTopic: state.setSelectedTopic,
      injectTopicDescription: state.injectTopicDescription,
    })),
  );
  const isFloating = chatType === ChatType.FLOATING;
  return (
    <>
      {topics?.topics
        ?.filter((topic) => topic.type)
        .map((topic, index) => {
          const isDescription = topic.showDescription;
          return (
            <div
              className={`flex flex-col items-left justify-top text-left 
                hover:bg-[var(--color-secondary)] focus:bg-[var(--color-secondary)] 
                active:bg-[var(--color-secondary)] p-2 rounded-lg 
                ${selectedTopic?.name === topic.name ? "bg-[var(--color-secondary)]" : related ? "bg-[var(--color-info-content)]" : "bg-[var(--color-primary)]"}`}
              key={`topic-${topic.name}-${topic.type}`}
              title={isFloating ? topic.description : ""}
            >
                <div className="cursor-pointer flex-1" onClick={() => setSelectedTopic(topic)}>
                  <div className="flex flex-row justify-between gap-2">
                    <div className="text-white font-bold">{topic.name}</div>
                    {!isFloating && <div className="text-white">{topic.type}</div>}
                  </div>
                  <div className="w-full text-white text-sm">
                    {isDescription ? <DescriptionViewer descriptionParts={splitDescription(topic.description)} /> : simplifyDescription(topic.description)}
                  </div>
                </div>
                <div className="flex flex-row justify-between mt-1">
                  {isDescription ? <MdExpandLess className="cursor-pointer" fill="white" color="white" onClick={() => injectTopicDescription(index, related)} title="Hide description" /> : 
                    <MdExpandMore className="cursor-pointer" fill="white" color="white" onClick={() => injectTopicDescription(index, related)} title="Show description" />}
                </div>
            </div>

          )
        })}
    </>
  );
}
