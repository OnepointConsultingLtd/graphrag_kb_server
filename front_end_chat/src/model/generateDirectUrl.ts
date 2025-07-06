import { Project } from "./projectCategory";

export type GenerateDirectUrlRequest = {
  chat_type: string;
  email: string;
  project: Project;
};
