import { Engine } from "../model/types";

export const ENGINES = {
  LIGHTRAG: "lightrag" as Engine,
  CAG: "cag" as Engine,
};

export const ENGINE_OPTIONS = [
  { value: ENGINES.LIGHTRAG, label: "LightRAG" },
  { value: ENGINES.CAG, label: "CAG" },
];
