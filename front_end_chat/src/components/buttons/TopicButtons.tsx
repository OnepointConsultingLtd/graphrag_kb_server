import useChatStore from "../../context/chatStore";
import { ChatType } from "../../lib/chatTypes";
import { Topics, Topic } from "../../model/topics";
import { useShallow } from "zustand/react/shallow";
import {
  MdExpandLess,
  MdExpandMore,
  MdOutlineQuestionMark,
  MdHourglassEmpty 
} from "react-icons/md";

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
  return (
    splitDescription(description)[0].split(".")[0].substring(0, 100) + " ..."
  );
}

function DescriptionViewer({
  descriptionParts,
}: {
  descriptionParts: string[];
}) {
  return (
    <div className="w-full text-white text-sm">
      {descriptionParts.map((part, index) => (
        <div key={`${index}-${part}`}>{part}</div>
      ))}
    </div>
  );
}

function TopicDescription({
  isDescription,
  topic,
}: {
  isDescription: boolean | undefined;
  topic: Topic;
}) {
  return (
    <div className="w-full text-white text-sm">
      {isDescription ? (
        <DescriptionViewer
          descriptionParts={splitDescription(topic.description)}
        />
      ) : (
        simplifyDescription(topic.description)
      )}
    </div>
  );
}

function TopicQuestions({topic}: {topic: Topic}) {
  const {
    selectTopicQuestion,
  } = useChatStore(
    useShallow((state) => ({
      selectTopicQuestion: state.selectTopicQuestion,
    })),
  );
  return (
    <div className="w-full text-white text-sm mt-2">
      <ul>
        {topic.questions?.map((question, index) => (
          <li className="dash-marker ml-2.5 cursor-pointer hover:underline" key={`${index}-${question}`} 
          onClick={(e) => {
            e.stopPropagation();
            selectTopicQuestion(question)
          }}>{question}</li>
        ))}
      </ul>
    </div>
  );
}

export default function TopicButtons({
  topics,
  related,
}: {
  topics: Topics | null;
  related: boolean;
}) {
  const {
    chatType,
    selectedTopic,
    topicQuestionsLoading,
    setSelectedTopic,
    injectTopicDescription,
    injectTopicQuestions,
    removeTopicQuestions,
  } = useChatStore(
    useShallow((state) => ({
      chatType: state.chatType,
      selectedTopic: state.selectedTopic,
      setSelectedTopic: state.setSelectedTopic,
      injectTopicDescription: state.injectTopicDescription,
      topicQuestionsLoading: state.topicQuestionsLoading,
      injectTopicQuestions: state.injectTopicQuestions,
      removeTopicQuestions: state.removeTopicQuestions,
    })),
  );
  const isFloating = chatType === ChatType.FLOATING;
  return (
    <>
      {topics?.topics
        ?.filter((topic) => topic.type)
        .map((topic, index) => {
          const isDescription = topic.showDescription;
          const hasQuestions = (topic.questions && topic.questions.length > 0)
          return (
            <div
              className={`flex flex-col items-left justify-top text-left 
                hover:bg-[var(--color-secondary)] focus:bg-[var(--color-secondary)] 
                active:bg-[var(--color-secondary)] p-2 rounded-lg 
                ${selectedTopic?.name === topic.name ? "bg-[var(--color-secondary)]" : related ? "bg-[var(--color-info-content)]" : "bg-[var(--color-primary)]"}`}
              key={`topic-${topic.name}-${topic.type}`}
              title={isFloating ? topic.description : ""}
            >
              <div
                className="cursor-pointer flex-1"
                onClick={() => setSelectedTopic(topic)}
              >
                <div className="flex flex-row justify-between gap-2">
                  <div className="text-white font-bold">{topic.name}</div>
                  {!isFloating && (
                    <div className="text-white">{topic.type}</div>
                  )}
                </div>
                <TopicDescription isDescription={isDescription} topic={topic} />
                <TopicQuestions topic={topic} />
              </div>
              <div className="flex flex-row justify-between mt-1">
                <div>
                  {isDescription ? (
                    <MdExpandLess
                      className="cursor-pointer"
                      fill="white"
                      color="white"
                      onClick={() => injectTopicDescription(index, related)}
                      title="Hide description"
                    />
                  ) : (
                    <MdExpandMore
                      className="cursor-pointer"
                      fill="white"
                      color="white"
                      onClick={() => injectTopicDescription(index, related)}
                      title="Show description"
                    />
                  )}
                </div>
                <div>
                  {(!hasQuestions && topicQuestionsLoading !== index) && (
                    <MdOutlineQuestionMark
                      className="cursor-pointer w-3 h-3"
                      fill="white"
                      color="white"
                      onClick={() => injectTopicQuestions(index, related)}
                      title="Show questions"
                    />
                  )}
                  {(hasQuestions && topicQuestionsLoading !== index) && (
                    <MdOutlineQuestionMark
                      className="inline-block rotate-180 cursor-pointer w-3 h-3"
                      fill="white"
                      color="white"
                      onClick={() => removeTopicQuestions(index, related)}
                      title="Show questions"
                    />
                  )}
                  {topicQuestionsLoading === index && <MdHourglassEmpty className="w-5 h-5" fill="white" color="white" title="Generating questions" />}
                </div>
              </div>
            </div>
          );
        })}
    </>
  );
}
