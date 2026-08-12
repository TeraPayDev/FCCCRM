import { describe, expect, it } from "vitest";
import { previewCsv } from "../src/utils/csvPreview";

describe("CSV preview", () => {
  it("infers headers, numeric types and strings", () => {
    const preview = previewCsv(
      "Temperature,Humidity,Pressure,Rain\n28.5,80,1012.4,rain\n29.1,78,1011.8,no rain\n",
    );

    expect(preview.rowCount).toBe(2);
    expect(preview.fields).toEqual([
      expect.objectContaining({ name: "Temperature", data_type: "number", is_required: true }),
      expect.objectContaining({ name: "Humidity", data_type: "integer", is_required: true }),
      expect.objectContaining({ name: "Pressure", data_type: "number", is_required: true }),
      expect.objectContaining({ name: "Rain", data_type: "string", is_required: true }),
    ]);
  });

  it("handles quoted commas", () => {
    const preview = previewCsv('Station,Note\nFCC,"Heavy rain, road flooded"\n');
    expect(preview.sampleRows[0].Note).toBe("Heavy rain, road flooded");
  });
});
