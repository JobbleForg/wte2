#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT_DIR = Path(__file__).resolve().parent
REPO_DIR = ROOT_DIR.parent
STATIC_DIR = ROOT_DIR / "static"
DOCS_DIR = REPO_DIR / "docs"
XML_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
EXCEL_EPOCH = datetime(1899, 12, 30, tzinfo=timezone.utc)


def excel_serial_to_unix_ms(value: float) -> int:
    dt = EXCEL_EPOCH + timedelta(days=float(value))
    return int(dt.timestamp() * 1000)


def slugify(value: str) -> str:
    cleaned = []
    for char in value.lower():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "-":
            cleaned.append("-")
    slug = "".join(cleaned).strip("-")
    return slug or f"workbook-{uuid.uuid4().hex[:8]}"


def column_ref_to_index(cell_ref: str) -> int:
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char.upper())
        else:
            break
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return max(index - 1, 0)


def decode_shared_text(item: ET.Element) -> str:
    return "".join(node.text or "" for node in item.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))


def parse_cell_value(cell: ET.Element, shared_strings: list[str]) -> object | None:
    value_node = cell.find("a:v", XML_NS)
    inline_node = cell.find("a:is", XML_NS)
    cell_type = cell.attrib.get("t")

    if cell_type == "s" and value_node is not None:
        try:
            return shared_strings[int(value_node.text or "0")]
        except Exception:
            return ""

    if cell_type == "b" and value_node is not None:
        return value_node.text == "1"

    if inline_node is not None:
        return decode_shared_text(inline_node)

    if value_node is None:
        return None

    raw = value_node.text or ""
    if raw == "":
        return None
    if raw in {"#N/A", "#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NUM!"}:
        return raw

    try:
        numeric = float(raw)
        if math.isfinite(numeric):
            return numeric
    except ValueError:
        pass
    return raw


def is_numeric_column(values: list[object | None]) -> bool:
    non_null = [value for value in values if value not in (None, "")]
    if not non_null:
        return False
    numeric = [value for value in non_null if isinstance(value, (int, float)) and math.isfinite(value)]
    return len(numeric) / len(non_null) >= 0.7


def detect_time_column(headers: list[str], columns: list[list[object | None]]) -> int:
    for index, header in enumerate(headers):
        label = header.strip().lower()
        if label in {"time", "timestamp", "date", "datetime"}:
            return index

    for index, values in enumerate(columns):
        numeric = [value for value in values if isinstance(value, (int, float)) and 20000 <= value <= 70000]
        if len(numeric) < min(10, len(values) or 1):
            continue
        monotonic_pairs = 0
        comparisons = 0
        previous = None
        for value in numeric[:200]:
            if previous is not None:
                comparisons += 1
                if value >= previous:
                    monotonic_pairs += 1
            previous = value
        if comparisons and monotonic_pairs / comparisons >= 0.9:
            return index
    return 0


def format_default_header(index: int, existing: str, is_time_column: bool) -> str:
    if existing:
        return existing
    if is_time_column:
        return "Time"
    return f"Column {index + 1}"


@dataclass
class ColumnSummary:
    index: int
    name: str
    numeric: bool
    min_value: float | None
    max_value: float | None
    non_null_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "name": self.name,
            "numeric": self.numeric,
            "minValue": self.min_value,
            "maxValue": self.max_value,
            "nonNullCount": self.non_null_count,
        }


@dataclass
class SheetData:
    index: int
    name: str
    headers: list[str]
    columns: list[list[object | None]]
    time_column: int
    time_values: list[int | None]
    summaries: list[ColumnSummary]
    default_columns: list[int]

    @property
    def row_count(self) -> int:
        if not self.columns:
            return 0
        return len(self.columns[0])

    def to_summary(self) -> dict[str, object]:
        start = next((value for value in self.time_values if value is not None), None)
        end = next((value for value in reversed(self.time_values) if value is not None), None)
        return {
            "index": self.index,
            "name": self.name,
            "rowCount": self.row_count,
            "columnCount": len(self.columns),
            "timeColumn": self.time_column,
            "defaultColumns": self.default_columns,
            "timeStart": start,
            "timeEnd": end,
            "columns": [summary.to_dict() for summary in self.summaries],
        }


@dataclass
class WorkbookData:
    workbook_id: str
    name: str
    source: str
    sheets: list[SheetData]

    def to_summary(self) -> dict[str, object]:
        largest_sheet = max(self.sheets, key=lambda sheet: sheet.row_count, default=None)
        default_sheet = largest_sheet.index if largest_sheet else 0
        return {
            "id": self.workbook_id,
            "name": self.name,
            "source": self.source,
            "defaultSheet": default_sheet,
            "sheets": [sheet.to_summary() for sheet in self.sheets],
        }


@dataclass
class WorkbookEntry:
    workbook_id: str
    name: str
    source: str
    path: Path | None = None
    payload: bytes | None = None
    workbook: WorkbookData | None = None


class WorkbookStore:
    def __init__(self, docs_dir: Path) -> None:
        self.docs_dir = docs_dir
        self.entries: dict[str, WorkbookEntry] = {}
        self.lock = threading.Lock()
        self._load_bundled_entries()

    def _load_bundled_entries(self) -> None:
        if not self.docs_dir.exists():
            return
        for path in sorted(self.docs_dir.glob("*.xlsx")):
            workbook_id = slugify(path.stem)
            suffix = 1
            while workbook_id in self.entries:
                suffix += 1
                workbook_id = f"{slugify(path.stem)}-{suffix}"
            self.entries[workbook_id] = WorkbookEntry(workbook_id=workbook_id, name=path.name, source="bundled", path=path)

    def list_workbooks(self) -> list[dict[str, object]]:
        return [{"id": entry.workbook_id, "name": entry.name, "source": entry.source} for entry in self.entries.values()]

    def add_uploaded(self, name: str, payload: bytes) -> dict[str, object]:
        workbook_id = f"upload-{uuid.uuid4().hex[:8]}"
        entry = WorkbookEntry(workbook_id=workbook_id, name=name, source="upload", payload=payload)
        with self.lock:
            self.entries[workbook_id] = entry
        workbook = self._ensure_loaded(workbook_id)
        return workbook.to_summary()

    def get_summary(self, workbook_id: str) -> dict[str, object]:
        return self._ensure_loaded(workbook_id).to_summary()

    def get_series(self, workbook_id: str, sheet_index: int, column_indices: list[int]) -> dict[str, object]:
        workbook = self._ensure_loaded(workbook_id)
        if sheet_index < 0 or sheet_index >= len(workbook.sheets):
            raise KeyError("Unknown sheet")
        sheet = workbook.sheets[sheet_index]
        valid_columns = [index for index in column_indices if 0 <= index < len(sheet.columns) and index != sheet.time_column]

        rows = sheet.row_count
        start = 0
        end = rows
        time_values = sheet.time_values[start:end]
        series = []
        for index in valid_columns:
            summary = sheet.summaries[index]
            series.append(
                {
                    "index": index,
                    "name": summary.name,
                    "values": [value if isinstance(value, (int, float)) and math.isfinite(value) else None for value in sheet.columns[index][start:end]],
                }
            )

        return {
            "workbookId": workbook_id,
            "sheetIndex": sheet.index,
            "sheetName": sheet.name,
            "timeColumn": sheet.time_column,
            "timeName": sheet.headers[sheet.time_column],
            "times": time_values,
            "series": series,
        }

    def _ensure_loaded(self, workbook_id: str) -> WorkbookData:
        with self.lock:
            entry = self.entries.get(workbook_id)
            if entry is None:
                raise KeyError("Unknown workbook")
            if entry.workbook is not None:
                return entry.workbook

        payload: bytes
        if entry.payload is not None:
            payload = entry.payload
        elif entry.path is not None:
            payload = entry.path.read_bytes()
        else:
            raise KeyError("Workbook has no data")

        workbook = parse_workbook_bytes(workbook_id, entry.name, entry.source, payload)
        with self.lock:
            entry.workbook = workbook
            return workbook


def parse_workbook_bytes(workbook_id: str, name: str, source: str, payload: bytes) -> WorkbookData:
    with ZipFileBytes(payload) as archive:
        shared_strings = archive.shared_strings()
        workbook_xml = ET.fromstring(archive.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_xml}
        sheets_xml = workbook_xml.find("a:sheets", XML_NS)

        sheets: list[SheetData] = []
        for index, sheet in enumerate(sheets_xml if sheets_xml is not None else []):
            sheet_name = sheet.attrib.get("name", f"Sheet {index + 1}")
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rel_id)
            if not target:
                continue
            sheet_xml = ET.fromstring(archive.read(f"xl/{target}"))
            parsed_sheet = parse_sheet(index, sheet_name, sheet_xml, shared_strings)
            sheets.append(parsed_sheet)

    return WorkbookData(workbook_id=workbook_id, name=name, source=source, sheets=sheets)


class ZipFileBytes:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.archive: ZipFile | None = None

    def __enter__(self) -> "ZipFileBytes":
        import io

        self.archive = ZipFile(io.BytesIO(self.payload))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.archive is not None:
            self.archive.close()

    def read(self, name: str) -> bytes:
        assert self.archive is not None
        return self.archive.read(name)

    def shared_strings(self) -> list[str]:
        assert self.archive is not None
        if "xl/sharedStrings.xml" not in self.archive.namelist():
            return []
        shared_xml = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        return [decode_shared_text(item) for item in shared_xml]


def parse_sheet(index: int, name: str, sheet_xml: ET.Element, shared_strings: list[str]) -> SheetData:
    sheet_data = sheet_xml.find("a:sheetData", XML_NS)
    row_maps: list[dict[int, object | None]] = []
    max_column = -1
    if sheet_data is not None:
        for row in sheet_data:
            row_map: dict[int, object | None] = {}
            for cell in row:
                ref = cell.attrib.get("r", "A1")
                column_index = column_ref_to_index(ref)
                max_column = max(max_column, column_index)
                row_map[column_index] = parse_cell_value(cell, shared_strings)
            if row_map:
                row_maps.append(row_map)

    if max_column < 0:
        return SheetData(index=index, name=name, headers=["Time"], columns=[[]], time_column=0, time_values=[], summaries=[ColumnSummary(0, "Time", True, None, None, 0)], default_columns=[])

    header_map = row_maps[0] if row_maps else {}
    columns = [[] for _ in range(max_column + 1)]
    for row_map in row_maps[1:]:
        for column_index in range(max_column + 1):
            columns[column_index].append(row_map.get(column_index))

    provisional_headers = [str(header_map.get(column_index) or "").strip() for column_index in range(max_column + 1)]
    time_column = detect_time_column(provisional_headers, columns)
    headers = [format_default_header(i, provisional_headers[i], i == time_column) for i in range(max_column + 1)]

    time_values: list[int | None] = []
    for value in columns[time_column]:
        if isinstance(value, (int, float)) and math.isfinite(value):
            time_values.append(excel_serial_to_unix_ms(value))
        else:
            time_values.append(None)

    summaries: list[ColumnSummary] = []
    numeric_indices: list[int] = []
    for column_index, values in enumerate(columns):
        numeric = is_numeric_column(values)
        clean_values = [float(value) for value in values if isinstance(value, (int, float)) and math.isfinite(value)]
        if numeric and column_index != time_column:
            numeric_indices.append(column_index)
        summaries.append(
            ColumnSummary(
                index=column_index,
                name=headers[column_index],
                numeric=numeric,
                min_value=min(clean_values) if numeric and clean_values else None,
                max_value=max(clean_values) if numeric and clean_values else None,
                non_null_count=sum(1 for value in values if value not in (None, "")),
            )
        )

    default_columns = numeric_indices[: min(4, len(numeric_indices))]
    return SheetData(index=index, name=name, headers=headers, columns=columns, time_column=time_column, time_values=time_values, summaries=summaries, default_columns=default_columns)


class TrendRequestHandler(BaseHTTPRequestHandler):
    server_version = "SCADATrendViewer/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/workbooks":
            self._send_json({"workbooks": self.server.store.list_workbooks()})
            return

        if parsed.path.startswith("/api/workbooks/"):
            workbook_id = parsed.path.split("/")[3]
            try:
                self._send_json(self.server.store.get_summary(workbook_id))
            except KeyError:
                self._send_error(HTTPStatus.NOT_FOUND, "Workbook not found")
            return

        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            self._handle_upload()
            return
        if parsed.path == "/api/series":
            self._handle_series_request()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

    def _handle_upload(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            self._send_error(HTTPStatus.BAD_REQUEST, "Empty upload")
            return
        payload = self.rfile.read(length)
        filename = self.headers.get("X-Filename", "uploaded.xlsx")
        try:
            summary = self.server.store.add_uploaded(filename, payload)
        except Exception as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, f"Unable to load workbook: {exc}")
            return
        self._send_json(summary, status=HTTPStatus.CREATED)

    def _handle_series_request(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
            workbook_id = str(payload["workbookId"])
            sheet_index = int(payload["sheetIndex"])
            column_indices = [int(value) for value in payload.get("columnIndices", [])]
            data = self.server.store.get_series(workbook_id, sheet_index, column_indices)
        except KeyError as exc:
            self._send_error(HTTPStatus.NOT_FOUND, f"Unknown resource: {exc}")
            return
        except Exception as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, f"Bad request: {exc}")
            return
        self._send_json(data)

    def _serve_static(self, path: str) -> None:
        normalized = "/" if path in {"", "/"} else path
        if normalized == "/":
            file_path = STATIC_DIR / "index.html"
        else:
            file_path = STATIC_DIR / normalized.lstrip("/")
        resolved = file_path.resolve()
        static_root = STATIC_DIR.resolve()
        if not resolved.is_file() or (resolved != static_root / "index.html" and static_root not in resolved.parents):
            self._send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        content_type = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".json": "application/json; charset=utf-8",
        }.get(resolved.suffix, "application/octet-stream")
        content = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        content = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self.send_response(status)
        payload = json.dumps({"error": message}).encode("utf-8")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: object) -> None:
        return


class TrendHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], store: WorkbookStore) -> None:
        super().__init__(server_address, handler_class)
        self.store = store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local SCADA-style trend viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8123, type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = WorkbookStore(DOCS_DIR)
    server = TrendHTTPServer((args.host, args.port), TrendRequestHandler, store)
    print(f"SCADA trend viewer running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
