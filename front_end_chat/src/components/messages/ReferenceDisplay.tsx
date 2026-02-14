import React from "react";
import type { Reference } from "../../model/references";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { downloadFile } from "../../lib/apiClient";
import { IoDocumentTextOutline, IoGlobeOutline } from "react-icons/io5";

export default function ReferenceDisplay({
  reference,
}: {
  reference: Reference;
}) {
  const [jwt, project, setMarkdownDialogueContent] = useChatStore(
    useShallow((state) => [
      state.jwt,
      state.selectedProject,
      state.setMarkdownDialogueContent,
    ]),
  );

  function openReference(e: React.MouseEvent<HTMLAnchorElement>) {
    e.preventDefault();
    if (project) {
      downloadFile(jwt, project, reference, false)
        .then((response) => response.text())
        .then((content) => {
          setMarkdownDialogueContent(content);
        })
        .catch((error) => {
          setMarkdownDialogueContent(
            `An error occurred while downloading the file: ${error.message}`,
          );
          console.error(error);
        });
    }
  }

  function openOriginal(e: React.MouseEvent<HTMLAnchorElement>) {
    e.preventDefault();
    if (project) {
      downloadFile(jwt, project, reference, true)
        .then((response) => Promise.all([response, response.blob()]))
        .then(([response, blob]) => {
          const contentDisposition = response.headers.get(
            "Content-Disposition",
          );
          let filename = "downloaded_file";
          if (contentDisposition) {
            const filenameMatch =
              contentDisposition.match(/filename="([^"]+)"/);
            if (filenameMatch && filenameMatch[1]) {
              filename = filenameMatch[1];
            }
          }
          // Create a Blob URL
          const blobUrl = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = blobUrl;
          a.download = filename; // Set the download attribute to suggest a filename

          // Append the anchor to the body (it doesn't need to be visible)
          document.body.appendChild(a);

          // Programmatically click the anchor to trigger the download
          a.click();

          // Clean up: revoke the Blob URL after a short delay
          // This is important to free up memory
          setTimeout(() => {
            URL.revokeObjectURL(blobUrl);
            document.body.removeChild(a);
          }, 100);
        })
        .catch((error) => {
          setMarkdownDialogueContent(
            `An error occurred while downloading the original file: ${error.message}`,
          );
          console.error(error);
        });
    }
  }

  const hasLinks = reference.links && reference.links.length > 0;

  return (
    <li className="break-words flex flex-col mb-3 last:mb-0">
      <div className="flex items-center gap-2 flex-wrap">
        <a
          href={reference.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={openReference}
          className="text-blue-600 hover:text-blue-800 hover:underline font-medium"
        >
          {reference.file}
        </a>
        <a
          href={reference.url}
          className="shrink-0 text-slate-400 hover:text-slate-600"
          target="_blank"
          rel="noopener noreferrer"
          onClick={openOriginal}
          title="Download original file"
        >
          <IoDocumentTextOutline className="w-4 h-4" />
        </a>
      </div>
      {hasLinks && (
        <ul className="list-none pl-4 mt-1.5 flex flex-col gap-1 border-l-2 border-slate-200 ml-0.5">
          {reference.links!.map((link, i) => (
            <li key={i} className="flex items-start gap-2 min-w-0">
              <IoGlobeOutline
                className="shrink-0 w-4 h-4 mt-0.5 text-blue-500"
                aria-hidden
              />
              <a
                href={link}
                target="_blank"
                rel="noopener noreferrer"
                className="break-all text-sm text-blue-500 hover:underline min-w-0"
              >
                {link}
              </a>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
