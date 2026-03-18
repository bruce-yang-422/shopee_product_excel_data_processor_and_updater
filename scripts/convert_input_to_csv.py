#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""將 data/input 底下的檔案轉換為 CSV。

- 遞迴讀取 data/input 底下所有 Excel（*.xlsx、*.xlsm）與 CSV 檔案。
- 將輸出 CSV 寫入 temp 資料夾（不存在時自動建立）。
- 所有欄位值一律轉為字串，避免資料型別推斷或數值截斷。

使用方式：
    python scripts/convert_input_to_csv.py
    python scripts/convert_input_to_csv.py --input data/input --output temp

"""

from __future__ import annotations

import argparse
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator, Optional

import openpyxl
import pandas as pd


# pandas >= 2.0 已移除對 .xls 的內建支援（xlrd 不再支援）。
# 若需要 .xls 支援，請安裝舊版 xlrd（例如 <2.0），或先將 .xls 轉換為 .xlsx。
SUPPORTED_XLS_EXTS = {".xlsx", ".xlsm"}
SUPPORTED_CSV_EXTS = {".csv"}
PANE_VALUE_REPLACEMENTS = {
    "bottom_left": "bottomLeft",
    "bottom_right": "bottomRight",
    "top_left": "topLeft",
    "top_right": "topRight",
}


def _to_string_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """將 DataFrame 所有值轉為字串（空值保留為空字串）。"""

    # 將缺失值替換為空字串（而非 NaN）
    df = df.fillna("")

    # 確保所有值皆為字串型別
    return df.astype(str)


def _normalize_worksheet_xml(xml_text: str) -> str:
    """修正已知的無效工作表 pane 值，避免 openpyxl 解析失敗。"""

    normalized = xml_text
    for bad_value, good_value in PANE_VALUE_REPLACEMENTS.items():
        normalized = normalized.replace(
            f'activePane="{bad_value}"',
            f'activePane="{good_value}"',
        )
        normalized = normalized.replace(
            f'pane="{bad_value}"',
            f'pane="{good_value}"',
        )
    return normalized


def _repair_excel_if_needed(src: Path) -> Path:
    """回傳可正常讀取的活頁簿路徑；若有已知 XML 問題則修復後存入暫存檔。"""

    changed_files: dict[str, bytes] = {}

    with zipfile.ZipFile(src) as archive:
        for info in archive.infolist():
            if not (
                info.filename.startswith("xl/worksheets/")
                and info.filename.endswith(".xml")
            ):
                continue

            original_bytes = archive.read(info.filename)
            original_text = original_bytes.decode("utf-8")
            normalized_text = _normalize_worksheet_xml(original_text)
            if normalized_text != original_text:
                changed_files[info.filename] = normalized_text.encode("utf-8")

        if not changed_files:
            return src

        with tempfile.NamedTemporaryFile(
            suffix=src.suffix,
            prefix=f"{src.stem}_repaired_",
            delete=False,
        ) as temp_file:
            repaired_path = Path(temp_file.name)

        with zipfile.ZipFile(src) as source_archive, zipfile.ZipFile(
            repaired_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as repaired_archive:
            for info in source_archive.infolist():
                repaired_archive.writestr(
                    info,
                    changed_files.get(info.filename, source_archive.read(info.filename)),
                )

    return repaired_path


@contextmanager
def _readable_excel_path(src: Path) -> Iterator[Path]:
    """產生可讀取的活頁簿路徑，結束後自動清除任何暫存修復檔。"""

    readable_path = _repair_excel_if_needed(src)
    try:
        yield readable_path
    finally:
        if readable_path != src:
            readable_path.unlink(missing_ok=True)


def convert_excel_to_csv(src: Path, dst: Path, sheet_name: Optional[str] = None) -> Path:
    """將單一 Excel 工作表轉換為 CSV 檔案。

    若未指定 sheet_name，僅轉換第一個工作表。
    回傳寫入的 CSV 檔案路徑。
    """

    # 優先使用 pandas（openpyxl 引擎）；若失敗則改用 openpyxl 直接解析。
    with _readable_excel_path(src) as readable_src:
        try:
            read_kwargs = {
                "dtype": str,
                "keep_default_na": False,
                "na_filter": False,
            }
            if sheet_name is not None:
                read_kwargs["sheet_name"] = sheet_name

            df = pd.read_excel(
                readable_src,
                engine="openpyxl" if readable_src.suffix.lower() in SUPPORTED_XLS_EXTS else None,
                **read_kwargs,
            )
        except Exception:
            # 部分活頁簿含有 pandas 仍無法處理的結構。
            # 此時改以 openpyxl 唯讀模式載入並手動建立 DataFrame。
            wb = openpyxl.load_workbook(readable_src, read_only=True, data_only=True)
            try:
                ws = wb[sheet_name] if sheet_name is not None else wb.active
                data = list(ws.values)

                if not data:
                    df = pd.DataFrame()
                else:
                    headers = ["" if h is None else str(h) for h in data[0]]
                    values = [
                        ["" if v is None else str(v) for v in row]
                        for row in data[1:]
                    ]
                    df = pd.DataFrame(values, columns=headers)
            finally:
                wb.close()

    df = _to_string_dataframe(df)
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst, index=False, encoding="utf-8-sig")
    return dst


def convert_csv_to_csv(src: Path, dst: Path) -> Path:
    """讀取 CSV 並重新寫出，確保所有值皆為字串型別。"""

    df = pd.read_csv(src, dtype=str, keep_default_na=False, na_filter=False)
    df = _to_string_dataframe(df)
    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dst, index=False, encoding="utf-8-sig")
    return dst


def find_input_files(input_dir: Path) -> Iterable[Path]:
    """遞迴列出 input_dir 底下所有支援的檔案。"""

    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() in SUPPORTED_XLS_EXTS.union(SUPPORTED_CSV_EXTS):
            yield path


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="將 data/input 底下所有支援的檔案轉換為 CSV，所有欄位以文字格式儲存。"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "input",
        help="包含 Excel/CSV 檔案的輸入資料夾。",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "temp",
        help="產生的 CSV 檔案輸出資料夾。",
    )
    parser.add_argument(
        "--overwrite",
        "-f",
        action="store_true",
        help="覆蓋已存在的輸出檔案。",
    )
    args = parser.parse_args(argv)

    input_dir = args.input
    output_dir = args.output

    if not input_dir.exists():
        print(f"錯誤：輸入資料夾不存在：{input_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    processed = []
    skipped = []

    for src in find_input_files(input_dir):
        rel_path = src.relative_to(input_dir)
        out_base_dir = output_dir / rel_path.parent
        out_name_base = rel_path.stem

        if src.suffix.lower() in SUPPORTED_CSV_EXTS:
            out_path = out_base_dir / f"{out_name_base}.csv"
            if out_path.exists() and not args.overwrite:
                skipped.append((src, out_path))
                continue
            convert_csv_to_csv(src, out_path)
            processed.append((src, out_path))
            continue

        # Excel 檔案
        try:
            # 若有多個工作表，每個工作表各產生一個 CSV。
            with _readable_excel_path(src) as readable_src:
                with pd.ExcelFile(readable_src, engine="openpyxl") as excel_file:
                    sheet_names = excel_file.sheet_names
            if len(sheet_names) <= 1:
                out_path = out_base_dir / f"{out_name_base}.csv"
                if out_path.exists() and not args.overwrite:
                    skipped.append((src, out_path))
                    continue
                convert_excel_to_csv(src, out_path)
                processed.append((src, out_path))
            else:
                for sheet in sheet_names:
                    out_path = out_base_dir / f"{out_name_base}__{sheet}.csv"
                    if out_path.exists() and not args.overwrite:
                        skipped.append((src, out_path))
                        continue
                    convert_excel_to_csv(src, out_path, sheet_name=sheet)
                    processed.append((src, out_path))
        except Exception as e:
            print(f"錯誤：轉換 {src} 時發生例外：{e}")
            skipped.append((src, None))

    if processed:
        print("已轉換的檔案：")
        for src, out in processed:
            print(f" - {src.name} -> {out.relative_to(output_dir)}")

    if skipped:
        print("\n已略過的檔案（已存在或發生錯誤）：")
        for src, out in skipped:
            if out is None:
                print(f" - {src.name}（錯誤）")
            else:
                print(f" - {src.name} -> {out.relative_to(output_dir)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
