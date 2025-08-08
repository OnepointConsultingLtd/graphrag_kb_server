export type Topic = {
  name: string;
  description: string;
  type: string;
  questions: string[];
  showDescription?: boolean;
};

export type Topics = {
  topics: Topic[];
};
