#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GTIN 條碼驗證與批次處理模組

公開介面：
  - SKU_COL            : 商品選項貨號的內部欄位名稱
  - GTIN_COL           : GTIN 欄位的內部名稱
  - METADATA_ROW_COUNT : CSV/Excel 中資料列前的標頭列數
  - is_valid_gtin(value)     -> bool  : 判斷是否為合法國際流通條碼
  - process_gtin(df, logger) -> dict  : 批次填入 DataFrame 中空白的 GTIN 欄位
"""

from __future__ import annotations

import logging

import pandas as pd

# ---------------------------------------------------------------------------
# 欄位常數
# ---------------------------------------------------------------------------

# 商品選項貨號（蝦皮批次更新 Excel 的內部欄位名稱）
SKU_COL = "et_title_variation_sku"

# GTIN / 國際條碼欄位的內部名稱
GTIN_COL = "ps_gtin_code"

# CSV 中資料列前的非資料標頭列數。
# pd.read_csv（header=0）後的結構：
#   df 第 0 列 → sales_info 中繼資料
#   df 第 1 列 → 中文欄位標籤（商品ID、商品名稱…）
#   df 第 2 列 → 必填欄位標記（必填…）
#   df 第 3 列 → 空白列
#   df 第 4 列 → 說明文字
#   df 第 5 列起 → 實際商品資料
METADATA_ROW_COUNT = 5

# pandas 在 dtype=str 時，空白儲存格可能產生的哨兵字串
_EMPTY_VALS: frozenset[str] = frozenset({"", "nan", "NaN", "None"})


# ---------------------------------------------------------------------------
# GS1 校驗碼驗證
# ---------------------------------------------------------------------------

def _gtin_check_digit_valid(v: str) -> bool:
    """GS1 標準校驗碼算法（GTIN-8 / 12 / 13 / 14 通用）。

    做法：左補零至 14 位，奇數位（從左 0-indexed，第 0、2、4… 位）×3、
    偶數位 ×1，加總後 (10 - 總和 % 10) % 10 應等於最末一位校驗碼。
    """
    padded = v.zfill(14)
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(padded[:-1]))
    return (10 - total % 10) % 10 == int(padded[-1])


# ---------------------------------------------------------------------------
# 公開驗證函式
# ---------------------------------------------------------------------------

def is_valid_gtin(value: str) -> bool:
    """若值為合法國際流通條碼則回傳 True。

    條件（全部滿足才算合法）：
    1. 純數字
    2. 長度為 8（EAN-8）、12（UPC）、13（EAN-13）、14（ITF-14）
    3. 不以 "02" 開頭（02 開頭為店內內部可變量條碼）
    4. GS1 末位校驗碼正確（排除倉儲內部貨號如 04XXXXXX、03XXXXXX 等）
    """
    v = value.strip()
    if not v.isdigit():
        return False
    if len(v) not in {8, 12, 13, 14}:
        return False
    if v.startswith("02"):
        return False
    if not _gtin_check_digit_valid(v):
        return False
    return True


# ---------------------------------------------------------------------------
# 批次 GTIN 填入
# ---------------------------------------------------------------------------

def process_gtin(df: pd.DataFrame, logger: logging.Logger) -> dict:
    """依 SKU 規則原地填入 DataFrame 中空白的 GTIN 欄位。

    跳過前 METADATA_ROW_COUNT 列（非資料標頭列），
    僅處理 df 第 METADATA_ROW_COUNT 列起的實際商品資料。

    GTIN 邏輯：
      - GTIN 已有值                 → 保留，跳過
      - SKU 為空                    → GTIN = "00"
      - SKU 為合法條碼（is_valid_gtin）→ GTIN = SKU
      - 其他（含 02 開頭、校驗碼錯誤）→ GTIN = "00"

    回傳統計字典：
      {"already_set": int, "set_from_sku": int, "set_to_00": int}
    """
    if SKU_COL not in df.columns:
        raise ValueError(f"找不到 SKU 欄位 '{SKU_COL}'。")
    if GTIN_COL not in df.columns:
        raise ValueError(f"找不到 GTIN 欄位 '{GTIN_COL}'。")

    stats: dict[str, int] = {"already_set": 0, "set_from_sku": 0, "set_to_00": 0}

    for idx in df.index[METADATA_ROW_COUNT:]:
        gtin = str(df.at[idx, GTIN_COL]).strip()
        sku = str(df.at[idx, SKU_COL]).strip()

        # GTIN 已有值 → 保留，跳過
        if gtin and gtin not in _EMPTY_VALS:
            stats["already_set"] += 1
            continue

        # SKU 為空 → 無條碼可用
        if not sku or sku in _EMPTY_VALS:
            df.at[idx, GTIN_COL] = "00"
            stats["set_to_00"] += 1
            logger.warning(f"  第 {idx} 列：SKU 為空 → GTIN='00'")
            continue

        # SKU 為合法條碼 → 複製至 GTIN；否則設為 "00"
        if is_valid_gtin(sku):
            df.at[idx, GTIN_COL] = sku
            stats["set_from_sku"] += 1
        else:
            df.at[idx, GTIN_COL] = "00"
            stats["set_to_00"] += 1

    return stats
