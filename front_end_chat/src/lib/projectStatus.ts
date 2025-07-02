import { SimpleProject } from "../model/projectCategory";

export function isProjectNotReady(project: SimpleProject) {
    return project.indexing_status === "in_progress" || project.indexing_status === "preparing";
}