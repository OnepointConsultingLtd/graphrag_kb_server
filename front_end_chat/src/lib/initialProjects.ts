import { Project } from "../types/types";
import { ENGINES } from "../constants/engines";

const initialProjects: Project[] = [
	{
		id: '1',
		name: 'Onepoint',
		createdAt: '2024-01-15',
		fileCount: 24,
		status: 'active',
		engine: ENGINES.GRAPHRAG,
	},
	{
		id: '2',
		name: 'Cluster',
		createdAt: '2024-01-10',
		fileCount: 18,
		status: 'active',
		engine: ENGINES.LIGHTRAG,
	},
	{
		id: '3',
		name: 'Azizi Bank',
		createdAt: '2024-01-05',
		fileCount: 32,
		status: 'archived',
		engine: ENGINES.GRAPHRAG,
	},
];

export default initialProjects;
