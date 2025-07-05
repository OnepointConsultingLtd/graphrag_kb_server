import React from "react";
import type { Reference } from "../../model/references";
import { useShallow } from "zustand/shallow";
import useChatStore from "../../context/chatStore";
import { downloadFile } from "../../lib/apiClient";
import { IoDocumentTextOutline } from "react-icons/io5";

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

  return (
    <li className="break-all flex">
      <span className="whitespace-nowrap mr-1">{reference.type} </span>
      <a
        href={reference.url}
        target="_blank"
        rel="noopener noreferrer"
        onClick={openReference}
      >
        {reference.file}
      </a>
      <a
        href={reference.url}
        className="mt-1.5 ml-1 document-icon"
        target="_blank"
        rel="noopener noreferrer"
        onClick={openOriginal}
      >
        <IoDocumentTextOutline className="w-4 h-4" />
      </a>
    </li>
  );
}
