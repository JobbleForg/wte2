from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
import polars as pl
from tsdownsample import MinMaxLTTBDownsampler


EXCEL_EPOCH = datetime(1899, 12, 30)
COMMON_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S%.f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S%.f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
)
COMMON_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)
TIMESTAMP_COLUMN_CANDIDATES = (
    "timestamp",
    "time stamp",
    "datetime",
    "date time",
    "date_time",
    "time",
    "date",
)
DEFAULT_MINMAX_RATIO = 4


@dataclass(frozen=True)
class DownsampledSeries:
    timestamps: np.ndarray
    values: np.ndarray
    indices: np.ndarray


class DataManager:
    """Load sparse SCADA exports and serve normalized time-window slices."""

    def __init__(self) -> None:
        self._dataframe: pl.DataFrame | None = None
        self._timestamp_column: str | None = None
        self._tag_columns: list[str] = []
        self._source_path: Path | None = None
        self._downsampler = MinMaxLTTBDownsampler()

    @property
    def dataframe(self) -> pl.DataFrame:
        if self._dataframe is None:
            raise RuntimeError("No Excel data is loaded. Call load_excel() first.")
        return self._dataframe

    @property
    def timestamp_column(self) -> str:
        if self._timestamp_column is None:
            raise RuntimeError("No Excel data is loaded. Call load_excel() first.")
        return self._timestamp_column

    @property
    def available_tags(self) -> tuple[str, ...]:
        return tuple(self._tag_columns)

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    def load_excel(
        self,
        source: str | Path,
        *,
        timestamp_column: str | None = None,
        tag_columns: Sequence[str] | None = None,
        sheet_name: str | None = None,
        infer_schema_length: int | None = 1_000,
    ) -> pl.DataFrame:
        selected_columns = [timestamp_column, *tag_columns] if timestamp_column and tag_columns else None
        frame = pl.read_excel(
            source,
            sheet_name=sheet_name,
            engine="calamine",
            columns=selected_columns,
            infer_schema_length=infer_schema_length,
        )

        if not isinstance(frame, pl.DataFrame):
            raise TypeError("Expected a single worksheet to be loaded as a Polars DataFrame.")

        resolved_timestamp_column = timestamp_column or self._infer_timestamp_column(frame)
        self._source_path = Path(source)
        return self.load_frame(
            frame,
            timestamp_column=resolved_timestamp_column,
            tag_columns=tag_columns,
        )

    def load_frame(
        self,
        frame: pl.DataFrame,
        *,
        timestamp_column: str,
        tag_columns: Sequence[str] | None = None,
    ) -> pl.DataFrame:
        resolved_tag_columns = self._resolve_tag_columns(
            frame,
            timestamp_column=timestamp_column,
            tag_columns=tag_columns,
        )
        prepared = self._prepare_frame(
            frame,
            timestamp_column=timestamp_column,
            tag_columns=resolved_tag_columns,
        )

        self._timestamp_column = timestamp_column
        self._tag_columns = resolved_tag_columns
        self._dataframe = prepared
        return prepared

    def normalize_time_index(
        self,
        frame: pl.DataFrame,
        *,
        timestamp_column: str,
        tag_columns: Sequence[str],
    ) -> pl.DataFrame:
        normalized_input = self._parse_timestamp_column(frame, timestamp_column)
        normalized_input = normalized_input.filter(pl.col(timestamp_column).is_not_null())

        master_timeline = (
            normalized_input
            .select(pl.col(timestamp_column))
            .unique()
            .sort(timestamp_column)
        )

        aggregated = (
            normalized_input
            .group_by(timestamp_column, maintain_order=True)
            .agg(
                [
                    pl.col(column_name).drop_nulls().last().alias(column_name)
                    for column_name in tag_columns
                ]
            )
            .sort(timestamp_column)
        )

        return (
            master_timeline
            .join(aggregated, on=timestamp_column, how="left")
            .with_columns(
                [pl.col(column_name).fill_null(strategy="forward") for column_name in tag_columns]
            )
            .rechunk()
        )

    def get_window(
        self,
        *,
        start: datetime | date | str | None,
        end: datetime | date | str | None,
        tags: Sequence[str] | None = None,
        as_numpy: bool = False,
    ) -> pl.DataFrame | np.ndarray:
        if self._dataframe is None:
            raise RuntimeError("No Excel data is loaded. Call load_excel() first.")

        start_value = self._coerce_boundary(start, is_end=False)
        end_value = self._coerce_boundary(end, is_end=True)
        if start_value and end_value and start_value > end_value:
            raise ValueError("The start timestamp must be less than or equal to the end timestamp.")

        selected_tags = list(tags) if tags is not None else list(self._tag_columns)
        self._validate_tags(selected_tags)

        query = self._dataframe
        if start_value is not None:
            query = query.filter(pl.col(self.timestamp_column) >= start_value)
        if end_value is not None:
            query = query.filter(pl.col(self.timestamp_column) <= end_value)

        subset = query.select([self.timestamp_column, *selected_tags])
        return subset.to_numpy() if as_numpy else subset

    def get_window_numpy(
        self,
        *,
        start: datetime | date | str | None,
        end: datetime | date | str | None,
        tags: Sequence[str] | None = None,
    ) -> np.ndarray:
        result = self.get_window(start=start, end=end, tags=tags, as_numpy=True)
        assert isinstance(result, np.ndarray)
        return result

    def get_tag_window_arrays(
        self,
        *,
        start: datetime | date | str | None,
        end: datetime | date | str | None,
        tag: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        self._validate_tags([tag])
        window = self.get_window(start=start, end=end, tags=[tag])
        assert isinstance(window, pl.DataFrame)

        timestamps = self._coerce_timestamp_array(window.get_column(self.timestamp_column).to_numpy())
        values = self._coerce_value_array(window.get_column(tag).to_numpy())
        return timestamps, values

    def downsample_series(
        self,
        timestamps: np.ndarray,
        values: np.ndarray,
        pixel_width: int,
        *,
        minmax_ratio: int = DEFAULT_MINMAX_RATIO,
        parallel: bool = False,
    ) -> DownsampledSeries:
        if pixel_width <= 0:
            raise ValueError("pixel_width must be greater than 0.")
        if minmax_ratio <= 0:
            raise ValueError("minmax_ratio must be greater than 0.")

        x_values = self._coerce_timestamp_array(timestamps)
        y_values = self._coerce_value_array(values)
        if x_values.ndim != 1 or y_values.ndim != 1:
            raise ValueError("timestamps and values must both be 1D arrays.")
        if x_values.size != y_values.size:
            raise ValueError("timestamps and values must contain the same number of points.")
        if x_values.size == 0:
            return DownsampledSeries(
                timestamps=x_values,
                values=y_values,
                indices=np.array([], dtype=np.uint64),
            )

        # MinMaxLTTB requires at least three output points when actual downsampling occurs.
        target_points = min(max(int(pixel_width), 3), x_values.size)
        if x_values.size <= target_points:
            indices = np.arange(x_values.size, dtype=np.uint64)
            return DownsampledSeries(timestamps=x_values, values=y_values, indices=indices)

        selected_indices = np.asarray(
            self._downsampler.downsample(
                x_values,
                y_values,
                n_out=target_points,
                minmax_ratio=minmax_ratio,
                parallel=parallel,
            ),
            dtype=np.uint64,
        )
        return DownsampledSeries(
            timestamps=x_values[selected_indices],
            values=y_values[selected_indices],
            indices=selected_indices,
        )

    def get_downsampled_window(
        self,
        *,
        start: datetime | date | str | None,
        end: datetime | date | str | None,
        tag: str,
        pixel_width: int,
        minmax_ratio: int = DEFAULT_MINMAX_RATIO,
        parallel: bool = False,
    ) -> DownsampledSeries:
        timestamps, values = self.get_tag_window_arrays(start=start, end=end, tag=tag)
        return self.downsample_series(
            timestamps,
            values,
            pixel_width,
            minmax_ratio=minmax_ratio,
            parallel=parallel,
        )

    def time_range(self) -> tuple[datetime, datetime] | None:
        if self._dataframe is None or self._dataframe.is_empty():
            return None

        start_value, end_value = (
            self._dataframe
            .select(
                pl.col(self.timestamp_column).min().alias("start"),
                pl.col(self.timestamp_column).max().alias("end"),
            )
            .row(0)
        )
        return start_value, end_value

    def _prepare_frame(
        self,
        frame: pl.DataFrame,
        *,
        timestamp_column: str,
        tag_columns: Sequence[str],
    ) -> pl.DataFrame:
        selected_frame = frame.select([timestamp_column, *tag_columns])
        normalized = self.normalize_time_index(
            selected_frame,
            timestamp_column=timestamp_column,
            tag_columns=tag_columns,
        )
        return normalized.sort(timestamp_column)

    def _parse_timestamp_column(self, frame: pl.DataFrame, timestamp_column: str) -> pl.DataFrame:
        if timestamp_column not in frame.columns:
            raise KeyError(f"Missing timestamp column: {timestamp_column}")

        dtype = frame.schema[timestamp_column]
        timestamp_expr = pl.col(timestamp_column)

        if dtype.is_temporal():
            parsed = timestamp_expr.cast(pl.Datetime)
        elif dtype == pl.String or dtype == pl.Categorical:
            string_expr = timestamp_expr.cast(pl.String)
            parsed = pl.coalesce(
                [string_expr.str.strptime(pl.Datetime, fmt, strict=False) for fmt in COMMON_DATETIME_FORMATS]
                + [
                    string_expr.str.strptime(pl.Date, fmt, strict=False).cast(pl.Datetime)
                    for fmt in COMMON_DATE_FORMATS
                ]
            )
        elif dtype.is_numeric():
            parsed = timestamp_expr.map_elements(
                self._excel_serial_to_datetime,
                return_dtype=pl.Datetime,
            )
        else:
            raise TypeError(
                f"Unsupported timestamp dtype {dtype!s} for column {timestamp_column!r}."
            )

        parsed_frame = frame.with_columns(parsed.alias(timestamp_column))
        if parsed_frame.select(pl.col(timestamp_column).is_null().all()).item():
            raise ValueError(
                f"Unable to parse any timestamp values from column {timestamp_column!r}."
            )

        return parsed_frame

    def _resolve_tag_columns(
        self,
        frame: pl.DataFrame,
        *,
        timestamp_column: str,
        tag_columns: Sequence[str] | None,
    ) -> list[str]:
        if timestamp_column not in frame.columns:
            raise KeyError(f"Missing timestamp column: {timestamp_column}")

        resolved = list(tag_columns) if tag_columns is not None else [
            column_name for column_name in frame.columns if column_name != timestamp_column
        ]
        if not resolved:
            raise ValueError("At least one tag column must be provided or present in the workbook.")

        missing = sorted(set(resolved) - set(frame.columns))
        if missing:
            missing_list = ", ".join(missing)
            raise KeyError(f"Missing tag columns: {missing_list}")

        return resolved

    def _infer_timestamp_column(self, frame: pl.DataFrame) -> str:
        normalized_names = {
            column_name: column_name.strip().lower().replace("_", " ")
            for column_name in frame.columns
        }
        for candidate in TIMESTAMP_COLUMN_CANDIDATES:
            for original_name, normalized_name in normalized_names.items():
                if candidate == normalized_name or candidate in normalized_name:
                    return original_name

        for column_name, dtype in frame.schema.items():
            if dtype.is_temporal():
                return column_name

        return frame.columns[0]

    def _validate_tags(self, tags: Sequence[str]) -> None:
        missing = sorted(set(tags) - set(self._tag_columns))
        if missing:
            missing_list = ", ".join(missing)
            raise KeyError(f"Unknown tag columns requested: {missing_list}")

    def _coerce_boundary(
        self,
        value: datetime | date | str | None,
        *,
        is_end: bool,
    ) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return self._strip_timezone(value)
        if isinstance(value, date):
            boundary_time = time.max if is_end else time.min
            return datetime.combine(value, boundary_time)
        if isinstance(value, str):
            parsed = self._parse_iso_datetime(value)
            return self._strip_timezone(parsed)
        raise TypeError("Time bounds must be datetime, date, ISO-8601 string, or None.")

    def _parse_iso_datetime(self, value: str) -> datetime:
        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO-8601 timestamp boundary: {value!r}") from exc

    def _coerce_timestamp_array(self, values: np.ndarray | Sequence[object]) -> np.ndarray:
        array = np.asarray(values)
        if array.ndim != 1:
            raise ValueError("timestamps must be a 1D array.")
        if array.dtype == object:
            try:
                array = array.astype("datetime64[us]")
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    "timestamps must be numeric, numpy datetime64, or datetime-like values."
                ) from exc
        return np.ascontiguousarray(array)

    def _coerce_value_array(self, values: np.ndarray | Sequence[object]) -> np.ndarray:
        array = np.asarray(values)
        if array.ndim != 1:
            raise ValueError("values must be a 1D array.")
        if array.dtype == object:
            try:
                array = array.astype(np.float64)
            except (TypeError, ValueError) as exc:
                raise TypeError("values must be numeric or coercible to float64.") from exc
        return np.ascontiguousarray(array)

    def _strip_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def _excel_serial_to_datetime(self, value: int | float | None) -> datetime | None:
        if value is None:
            return None
        return EXCEL_EPOCH + timedelta(days=float(value))
