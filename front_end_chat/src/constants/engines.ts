import { Engine } from "../types/types";

export const ENGINES = {
	GRAPHRAG: "graphrag" as Engine,
	LIGHTRAG: "lightrag" as Engine,
};

export const ENGINE_OPTIONS = [
	{ value: ENGINES.GRAPHRAG, label: "GraphRAG" },
	{ value: ENGINES.LIGHTRAG, label: "LightRAG" },
]; 