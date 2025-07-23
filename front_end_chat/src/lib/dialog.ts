export function showCloseModal(open: boolean, id: string) {
  if (open) {
    (document.getElementById(id) as HTMLDialogElement)?.showModal();
  } else {
    (document.getElementById(id) as HTMLDialogElement)?.close();
  }
}
