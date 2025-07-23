import RenderLabel from "./RenderLabel";
import SelectSearchEngine from "../SelectSearchEngine";

export default function FieldSearchType() {
  return (
    <div>
      <RenderLabel label="Search Type" />
      <SelectSearchEngine />
    </div>
  );
}
