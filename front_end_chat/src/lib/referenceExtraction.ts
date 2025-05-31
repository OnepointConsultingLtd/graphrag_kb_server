import type { Reference } from "../model/references"
import { BASE_SERVER } from "./server"

const referenceRegex = /\*\s*(\[.*?\])\s*(.+)\/(.+)/

export function extractReferences(text: string): Reference[] {
    return text.split("\n").map(l => {
        const match = l.match(referenceRegex)
        if(match) {
            return {
                file: match[3],
                path: match[2] + "/" + match[3],
                url: `${BASE_SERVER}/protected/project/download/single_file?file=${encodeURI(match[2] + "/" + match[3])}`,
                type: match[1]
            }
        }
        return null
    }).filter(Boolean) as Reference[]
}

export function removeReferencesFromText(text: string): string {
    return text.split("\n").filter(l => {
        const match = l.match(referenceRegex)
        return !match
    }).join("\n")
}