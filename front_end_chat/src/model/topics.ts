export type Topic = {
  name: string;
  description: string;
  type: string;
  questions: string[];
};

export type Topics = {
  topics: Topic[];
};
