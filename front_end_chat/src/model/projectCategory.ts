import { ENGINES } from "../constants/engines";

export const Platform = {
  GRAPHRAG: ENGINES.GRAPHRAG,
  LIGHTRAG: ENGINES.LIGHTRAG,
} as const;

export const SearchType = {
  LOCAL: "local",
  GLOBAL: "global",
  DRIFT: "drift",
  ALL: "all",
  NAIVE: "naive",
} as const;

export type Platform = (typeof Platform)[keyof typeof Platform];

export type Projects = {
  projects: SimpleProject[];
};

export type Project = {
  name: string;
  updated_timestamp: Date;
  input_files: string[];
  search_type: SearchType;
  platform: Platform;
  additional_prompt_instructions: string;
};

export type SimpleProject = {
  name: string;
  updated_timestamp: Date;
  input_files: string[];
  indexing_status: string;
};

export type ProjectCategories = {
  graphrag_projects: Projects;
  lightrag_projects: Projects;
};

export type SearchType = (typeof SearchType)[keyof typeof SearchType];
