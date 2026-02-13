import { Reference } from "../model/references";
import { Project } from "../model/projectCategory";
import { downloadFilePath } from "./apiClient";

/**
 * Given a list of references, checks if the reference url exists (returns non-404 status).
 * Returns a Promise that resolves to a filtered reference array with only available references.
 */
export async function filterAvailableReferences(jwt: string, project: Project, references: Reference[]): Promise<Reference[]> {
  const MAX_CONCURRENCY = 6;

  async function checkReference(url: string): Promise<boolean | null> {
    try {
        const response = await downloadFilePath(jwt, project, url, false)
        return response.ok;
    } catch (e) {
      // Ignore error (CORS, timeout, network error), treat as unavailable
      return null;
    }
  }

  // Process references with proper concurrency control
  const results: (Reference | null)[] = new Array(references.length).fill(null);
  
  async function processBatch(batch: Array<{ index: number; ref: Reference }>) {
    const promises = batch.map(async ({ index, ref }) => {
      if (!ref.path) {
        return;
      }
      const res = await checkReference(ref.path);
      if (res) {
        results[index] = ref;
      }
    });
    await Promise.all(promises);
  }

  const fileRefs = references.filter((ref) => ref.type === "[DC]");
  // Process in batches to maintain concurrency limit
  for (let i = 0; i < fileRefs.length; i += MAX_CONCURRENCY) {
    const batch = fileRefs
      .slice(i, i + MAX_CONCURRENCY)
      .map((ref, batchIdx) => ({ index: i + batchIdx, ref }));
    await processBatch(batch);
  }

  // Filter out nulls and return only available references
  return results.filter((ref): ref is Reference => ref !== null);
}