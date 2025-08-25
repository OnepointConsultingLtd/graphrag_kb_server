export function downloadBlob(blob: Blob, filename: string) {
  // 3. Create a temporary object URL from the Blob
  const url = URL.createObjectURL(blob);

  // 4. Create a temporary <a> element
  const a = document.createElement("a");
  a.href = url;
  a.download = filename; // desired filename
  a.style.display = "none";
  a.setAttribute("aria-hidden", "true");
  document.body.appendChild(a);

  // 5. Programmatically trigger the download
  a.click();

  // 6. Clean up
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
