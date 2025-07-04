import { Platform } from "../model/projectCategory";

export function supportsStreaming(platform: Platform) {
    return platform === Platform.CAG || platform === Platform.GRAPHRAG;
}