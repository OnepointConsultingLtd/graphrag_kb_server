import type { QueryResponse, StructuredQueryResponse } from "../model/message"
import type { Reference } from "../model/references"
import { getBaseServer } from "./server"

const referenceRegex = /\*\s*(\[.*?\])\s*(.+)\/(.+)/

export function extractReferences(text: string): Reference[] {
    return text.split("\n").map(l => {
        const match = l.match(referenceRegex)
        if (match) {
            return {
                file: match[3],
                path: match[2] + "/" + match[3],
                url: `${getBaseServer()}/protected/project/download/single_file?file=${encodeURI(match[2] + "/" + match[3])}`,
                type: match[1]
            }
        }
        return null
    }).filter(Boolean) as Reference[]
}

export function removeReferencesFromText(text: string): string {
    return text.split("\n").filter(l => l.trim() !== "References:").filter(l => {
        const match = l.match(referenceRegex)
        return !match
    }).join("\n")
}

export function extractEntityContext(response: QueryResponse, limit: number = 10): Reference[] {
    const references: Reference[] = []
    let i = 0
    while (references.length < limit && i < response.entities_context.length) {
        const entry = response.entities_context[i++]
        if (entry) {
            const files = entry.file_path.split("<SEP>")
            for (const f of files) {
                const reference: Reference = {
                    file: f.split("/").pop() || "",
                    path: f,
                    url: `${getBaseServer()}/protected/project/download/single_file?file=${encodeURI(f)}`,
                    type: "[KG]"
                }
                references.push(reference)
                if (references.length >= limit) {
                    break
                }
            }
        }
        if (references.length >= limit) {
            break
        }
    }
    return references
}

export function extractSimpleReferences(response: StructuredQueryResponse): Reference[] {
    const references = response.references
    if(!references) {
        return []
    }
    return references.map(r => {
        return {
            file: r.file.split("/").pop() || "",
            path: r.file,
            url: `${getBaseServer()}/protected/project/download/single_file?file=${encodeURI(r.file)}`,
            type: `[${r.type}]`
        }
    })
}