from pathlib import Path
import shutil


def zip_input(path: Path) -> Path:
    parent_folder = path.parent
    base_name = f"{parent_folder.stem}"
    file = shutil.make_archive(
        parent_folder / base_name, format="zip", root_dir=path, base_dir=None
    )
    return Path(file)
