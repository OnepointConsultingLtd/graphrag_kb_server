import RenderLabel from "./RenderLabel";
import { useShallow } from "zustand/shallow";
import { useDashboardStore } from "../../../context/dashboardStore";

export default function FieldWidgetType() {
  const { widgetType, setWidgetType } = useDashboardStore(
    useShallow((state) => ({
      widgetType: state.widgetType,
      setWidgetType: state.setWidgetType,
    })),
  );

  return (
    <div>
      <RenderLabel label="Widget Type" />
      <select
        value={widgetType}
        onChange={(e) => setWidgetType(e.target.value)}
        className="select select-primary  w-full bg-gray-700"
      >
        <option>FLOATING_CHAT</option>
        <option>CHAT</option>
      </select>
    </div>
  );
}
