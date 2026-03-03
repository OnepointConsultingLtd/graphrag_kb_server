export default function partialJsonExtractor(text: string): string {
  const initialText = '"response"';
  const initialTextIndex = text.indexOf(initialText);
  if (initialTextIndex === -1) {
    return "";
  }
  const colonIndex = text.indexOf(":", initialTextIndex);
  if (colonIndex === -1) {
    return "";
  }
  const initialQuoteIndex = text.indexOf('"', colonIndex);
  if (initialQuoteIndex === -1) {
    return "";
  }
  let quoteIndex = initialQuoteIndex;
  while (true) {
    quoteIndex = text.indexOf('"', quoteIndex + 1);
    if (quoteIndex === -1) {
      return unescapeJsonBestEffort(text.substring(initialQuoteIndex + 1));
    }
    if (!isEscapedQuote(text, quoteIndex)) {
      return unescapeJsonComplete(
        text.substring(initialQuoteIndex + 1, quoteIndex),
      );
    }
  }
}

function isEscapedQuote(text: string, quoteIndex: number): boolean {
  let backslashCount = 0;
  let i = quoteIndex - 1;
  while (i >= 0 && text.charAt(i) === "\\") {
    backslashCount++;
    i--;
  }
  return backslashCount % 2 === 1;
}

function unescapeJsonComplete(raw: string): string {
  try {
    return JSON.parse('"' + raw + '"');
  } catch {
    return unescapeJsonBestEffort(raw);
  }
}

function unescapeJsonBestEffort(raw: string): string {
  return raw
    .replace(/\\n/g, "\n")
    .replace(/\\r/g, "\r")
    .replace(/\\t/g, "\t")
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, "\\");
}