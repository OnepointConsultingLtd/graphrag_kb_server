import { Engine } from "../types/types";

export const ENGINES = {
  LIGHTRAG: "lightrag" as Engine,
  GRAPHRAG: "graphrag" as Engine,
};

export const ENGINE_OPTIONS = [
  { value: ENGINES.LIGHTRAG, label: "LightRAG" },
  { value: ENGINES.GRAPHRAG, label: "GraphRAG" },
];
