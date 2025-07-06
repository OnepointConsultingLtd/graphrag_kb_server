import { Platform } from "../model/projectCategory";

export function supportsStreaming(platform: Platform | undefined) {
  return platform === Platform.CAG || platform === Platform.GRAPHRAG;
}
