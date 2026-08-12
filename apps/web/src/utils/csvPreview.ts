export type CsvDataType = "string" | "number" | "integer" | "datetime";

export type CsvPreviewField = {
  name: string;
  data_type: CsvDataType;
  is_required: boolean;
  sample_values: string[];
};

export type CsvPreview = {
  fields: CsvPreviewField[];
  rowCount: number;
  sampleRows: Record<string, string>[];
};

function parseCsvRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let value = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];

    if (quoted) {
      if (char === '"' && text[index + 1] === '"') {
        value += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        value += char;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(value);
      value = "";
    } else if (char === "\n") {
      row.push(value.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }

  if (value.length > 0 || row.length > 0) {
    row.push(value.replace(/\r$/, ""));
    rows.push(row);
  }

  return rows.filter((candidate) => candidate.some((cell) => cell.trim() !== ""));
}

function inferType(values: string[]): CsvDataType {
  const populated = values.map((value) => value.trim()).filter(Boolean);
  if (!populated.length) return "string";

  if (populated.every((value) => /^[-+]?\d+$/.test(value))) return "integer";
  if (populated.every((value) => Number.isFinite(Number(value)))) return "number";
  if (
    populated.every((value) => {
      const parsed = Date.parse(value);
      return /[-/:T]/.test(value) && Number.isFinite(parsed);
    })
  ) {
    return "datetime";
  }
  return "string";
}

export function previewCsv(text: string, sampleLimit = 100): CsvPreview {
  const rows = parseCsvRows(text.replace(/^\uFEFF/, ""));
  if (!rows.length) throw new Error("The CSV is empty.");

  const headers = rows[0].map((header) => header.trim());
  if (headers.some((header) => !header)) throw new Error("Every CSV column must have a header.");
  if (new Set(headers).size !== headers.length) throw new Error("CSV headers must be unique.");

  const dataRows = rows.slice(1);
  const sampled = dataRows.slice(0, sampleLimit);
  const sampleRows = sampled
    .slice(0, 5)
    .map((cells) =>
      Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""])),
    );

  const fields = headers.map((name, columnIndex) => {
    const values = sampled.map((cells) => cells[columnIndex] ?? "");
    const sampleValues = [...new Set(values.map((value) => value.trim()).filter(Boolean))].slice(
      0,
      3,
    );
    return {
      name,
      data_type: inferType(values),
      is_required:
        dataRows.length > 0 && dataRows.every((cells) => (cells[columnIndex] ?? "").trim() !== ""),
      sample_values: sampleValues,
    } satisfies CsvPreviewField;
  });

  return { fields, rowCount: dataRows.length, sampleRows };
}
