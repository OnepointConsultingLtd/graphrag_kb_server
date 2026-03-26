import { describe, it, expect } from "vitest";
import partialJsonExtractor from "./partialJsonExtractor";

describe("partialJsonExtractor", () => {
  it("extracts the response text from complete JSON", () => {
    const json = '{"response": "text to extract"}';
    expect(partialJsonExtractor(json)).toBe("text to extract");
  });

  it("extracts the response text from incomplete JSON (no closing quote)", () => {
    const json = '{"response": "text to';
    const res = partialJsonExtractor(json);
    expect(res).toBe("text to");
  });

  it("extracts the response text from incomplete JSON (no closing brace)", () => {
    const json = '{"response": "text to extract"';
    expect(partialJsonExtractor(json)).toBe("text to extract");
  });

  it("returns empty string when no response key is present", () => {
    expect(partialJsonExtractor("")).toBe("");
    expect(partialJsonExtractor("some random text")).toBe("");
    expect(partialJsonExtractor('{"other": "value"}')).toBe("");
  });

  it("returns empty string when response key exists but no colon follows", () => {
    expect(partialJsonExtractor('"response"')).toBe("");
  });

  it("returns empty string when colon exists but no value quote follows", () => {
    expect(partialJsonExtractor('"response":')).toBe("");
  });

  it("returns empty string when colon exists but only non-quote characters follow", () => {
    expect(partialJsonExtractor('"response":{')).toBe("");
  });

  it("handles escaped quotes inside the response value", () => {
    const json = '{"response": "text with \\"escaped\\" quotes"}';
    expect(partialJsonExtractor(json)).toBe('text with "escaped" quotes');
  });

  it("handles newlines and special characters in the response", () => {
    const json = '{"response": "line one\\nline two"}';
    expect(partialJsonExtractor(json)).toBe("line one\nline two");
  });

  it("handles JSON with additional fields after response", () => {
    const json = '{"response": "the answer", "references": [{"type": "DC"}]}';
    expect(partialJsonExtractor(json)).toBe("the answer");
  });

  it("handles progressively growing streaming input", () => {
    const chunks = [
      '{"res',
      '{"response',
      '{"response"',
      '{"response":',
      '{"response": ',
      '{"response": "',
      '{"response": "Hello',
      '{"response": "Hello world',
      '{"response": "Hello world"',
      '{"response": "Hello world"}',
    ];

    const expected = [
      "", // no "response" key yet
      "", // "response" without closing quote
      "", // "response" found but no colon
      "", // colon found but no value quote follows yet
      "", // same — space after colon but no quote
      "", // opening quote found, but nothing after
      "Hello",
      "Hello world",
      "Hello world",
      "Hello world",
    ];

    chunks.forEach((chunk, i) => {
      expect(partialJsonExtractor(chunk)).toBe(expected[i]);
    });
  });

  it("handles markdown content with headings and formatting", () => {
    const json =
      '{"response": "### Heading\\nSome **bold** text and a [link](http://example.com)"}';
    expect(partialJsonExtractor(json)).toBe(
      "### Heading\nSome **bold** text and a [link](http://example.com)",
    );
  });

  it("unescapes partial/incomplete streaming content (best-effort)", () => {
    const json = '{"response": "line one\\nline two';
    expect(partialJsonExtractor(json)).toBe("line one\nline two");
  });

  it("handles double backslash before closing quote", () => {
    const json = '{"response": "path C:\\\\"}';
    expect(partialJsonExtractor(json)).toBe("path C:\\");
  });

  it("handles empty response value", () => {
    const json = '{"response": ""}';
    expect(partialJsonExtractor(json)).toBe("");
  });
});
