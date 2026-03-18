#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""蝦皮 GTIN 批次處理器

每個檔案的處理流程（共 2 步驟）：
  步驟一  data/input/<檔名>.xlsx
            → scripts/convert_input_to_csv.convert_excel_to_csv()
            → temp/<檔名>.csv          （原始 CSV，所有欄位為字串）

  步驟二  temp/<檔名>.csv
            → 套用 GTIN 邏輯於記憶體中
            → temp/<檔名>.csv          （覆寫為處理後的 CSV，可直接上傳蝦皮）

GTIN 處理邏輯：
  - GTIN 已有值                 → 跳過，保留原值
  - SKU 為空                    → GTIN = "00"
  - SKU 為合法條碼              → GTIN = SKU
  - 其他（含 02 開頭的內部碼） → GTIN = "00"

合法條碼長度：8（EAN-8）、12（UPC）、13（EAN-13）、14（ITF-14）
注意：以 "02" 開頭的號碼為店內內部條碼，非國際流通條碼，一律設為 "00"

使用方式：
    python main.py
    python main.py --input data/input --temp temp
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 路徑常數（相對於本檔案位置 = 專案根目錄）
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "input"
TEMP_DIR = BASE_DIR / "temp"
BACKUP_DIR = BASE_DIR / "data" / "backup"
LOGS_DIR = BASE_DIR / "logs"
SCRIPTS_DIR = BASE_DIR / "scripts"

# scripts/ 加入 sys.path，讓 convert_input_to_csv 可被匯入
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from gtin_processor import GTIN_COL, METADATA_ROW_COUNT, _EMPTY_VALS, process_gtin  # type: ignore[import-not-found]  # noqa: E402

# ---------------------------------------------------------------------------
# 日誌設定
# ---------------------------------------------------------------------------

def setup_logging(logs_dir: Path) -> logging.Logger:
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"gtin_processor_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("gtin_processor")


# ---------------------------------------------------------------------------
# 檔案處理流程
# ---------------------------------------------------------------------------

def process_file(
    xlsx_path: Path,
    temp_dir: Path,
    backup_dir: Path,
    logger: logging.Logger,
    overwrite_temp: bool = True,
) -> bool:
    """對單一 Excel 檔案執行 2 步驟流程。成功回傳 True。

    步驟一：xlsx → temp/<檔名>.csv          （透過 scripts/convert_input_to_csv）
    步驟二：處理 GTIN → 覆寫 temp CSV       （處理後的 CSV 可直接上傳蝦皮）
    """
    stem = xlsx_path.stem

    # ── 備份原始檔（僅備份一次；不覆蓋已存在的備份）────────────────────────
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / xlsx_path.name
    if not backup_path.exists():
        shutil.copy2(xlsx_path, backup_path)
        logger.info(f"  已備份 → backup/{xlsx_path.name}")

    csv_path = temp_dir / f"{stem}.csv"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # ── 步驟一：Excel → 原始 CSV ─────────────────────────────────────────────
    if csv_path.exists() and not overwrite_temp:
        logger.info(f"  [步驟一] 沿用現有 CSV：temp/{csv_path.name}")
    else:
        try:
            from convert_input_to_csv import convert_excel_to_csv  # noqa: PLC0415

            convert_excel_to_csv(xlsx_path, csv_path)
            logger.info(f"  [步驟一] xlsx → CSV：temp/{csv_path.name}")
        except Exception as exc:
            logger.error(f"  [步驟一] 轉換失敗：{exc}")
            return False

    # ── 步驟二：讀取 CSV → 套用 GTIN 邏輯 → 覆寫 CSV（可直接上傳蝦皮）──────
    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_filter=False)
    except Exception as exc:
        logger.error(f"  [步驟二] 讀取 CSV 失敗：{exc}")
        return False

    total_rows = len(df)
    data_rows = max(0, total_rows - METADATA_ROW_COUNT)
    logger.info(f"  [步驟二] 已載入 {total_rows} 列（{data_rows} 筆資料列）")

    if data_rows == 0:
        logger.warning("  [步驟二] 無資料列，略過 GTIN 處理。")

    try:
        stats = process_gtin(df, logger)
    except ValueError as exc:
        logger.error(f"  [步驟二] 欄位錯誤：{exc}")
        return False

    logger.info(
        f"  [步驟二] GTIN 結果：已有值={stats['already_set']}，"
        f"來自SKU={stats['set_from_sku']}，設為00={stats['set_to_00']}"
    )

    try:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"  [步驟二] 處理後 CSV 已儲存 → temp/{csv_path.name}")
    except Exception as exc:
        logger.error(f"  [步驟二] 儲存處理後 CSV 失敗：{exc}")
        return False

    logger.info("  處理完成")
    return True


# ---------------------------------------------------------------------------
# 程式進入點
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="蝦皮 GTIN 批次處理器 — 依 SKU 規則自動填入空白 GTIN 欄位。"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=INPUT_DIR,
        help="包含 Excel 檔案的輸入資料夾（預設：data/input）",
    )
    parser.add_argument(
        "--temp", "-t",
        type=Path,
        default=TEMP_DIR,
        help="處理後 CSV 的輸出資料夾（預設：temp）",
    )
    parser.add_argument(
        "--backup",
        type=Path,
        default=BACKUP_DIR,
        help="原始檔案備份資料夾（預設：data/backup）",
    )
    parser.add_argument(
        "--no-overwrite-temp",
        action="store_true",
        help="沿用現有的 temp CSV，不重新從 xlsx 轉換。",
    )
    args = parser.parse_args(argv)

    logger = setup_logging(LOGS_DIR)
    logger.info("=" * 60)
    logger.info("蝦皮 GTIN 批次處理器 已啟動")
    logger.info("=" * 60)

    input_dir: Path = args.input
    if not input_dir.exists():
        logger.error(f"找不到輸入資料夾：{input_dir}")
        return 1

    matching_files = [
        f for f in sorted(input_dir.iterdir())
        if f.is_file() and f.suffix.lower() == ".xlsx"
    ]

    if not matching_files:
        logger.warning(f"在 {input_dir} 中找不到符合規則的檔案")
        return 0

    logger.info(f"待處理檔案數：{len(matching_files)}")

    success_count = 0
    fail_count = 0

    for xlsx_path in matching_files:
        logger.info(f"--- {xlsx_path.name} ---")
        ok = process_file(
            xlsx_path=xlsx_path,
            temp_dir=args.temp,
            backup_dir=args.backup,
            logger=logger,
            overwrite_temp=not args.no_overwrite_temp,
        )
        if ok:
            success_count += 1
        else:
            fail_count += 1

    logger.info("=" * 60)
    logger.info(f"執行完畢 — 成功 {success_count} 個，失敗 {fail_count} 個")
    logger.info("=" * 60)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
