# 蝦皮 GTIN 批次處理器

自動讀取蝦皮商品批次更新 Excel，依 SKU 規則填入空白的 GTIN（國際條碼）欄位，輸出可直接上傳蝦皮的 CSV 檔案。

---

## 背景說明

詳見蝦皮官方公告：[賣家學習中心 — 國際條碼 GTIN 填寫說明](https://seller.shopee.tw/edu/article/18313)

### 蝦皮政策時程

| 時間 | 規定 |
| --- | --- |
| 2025 年 Q1 | 蝦皮商城率先將 GTIN 欄位設為必填 |
| 2026/4/20 | **全站**開啟 GTIN 欄位為必填 |

自 2026/4/20 起：

- 若 GTIN 欄位**空白未填寫**，商品將被限制降低曝光
- 若商品確實無條碼，需勾選「商品無有效的國際條碼」或批次模板填寫 `00`，即不受曝光限制
- 點選「編輯商品」進行修改時，GTIN 欄位將成為必填，不填無法完成上架

> 限制曝光後，填寫完成將於 2 個工作天內審核並恢復商品流量。

### GTIN 格式說明

**GTIN（Global Trade Item Number）** 是 GS1 國際標準的商品條碼體系，涵蓋：

| 格式 | 位數 | 說明 |
| --- | --- | --- |
| EAN-8 | 8 | 小型商品短碼 |
| UPC-A | 12 | 北美通用商品碼 |
| EAN-13 | 13 | 全球最常見的商品條碼 |
| ITF-14 | 14 | 物流箱（整箱）條碼 |

### 本工具的使用情境

蝦皮批次更新模板（Excel）的 H 欄即為 GTIN 欄位。透過「賣家中心 > 我的商品 > 批次工具 > 更新商品資料 > 價格及庫存」下載模板後，可快速確認 H 欄空白的商品即為尚未填寫的品項。

本工具針對 **SKU 即為 GS1 條碼**的情境設計，自動驗證並批次複製至 GTIN 欄位；無條碼或條碼無效的商品則自動填入 `"00"`，符合蝦皮批次上傳格式要求。

---

## 功能概述

- 批次處理 `data/input/` 下所有 `.xlsx` 檔案
- 依 GS1 標準驗證 SKU 是否為合法條碼（含末位校驗碼驗證）
- 自動填入空白 GTIN 欄位；無法辨識的條碼一律填 `"00"`
- 處理後的 CSV 輸出至 `temp/`，可直接上傳蝦皮批次更新
- 原始檔案自動備份至 `data/backup/`
- 完整處理記錄寫入 `logs/`

---

## 專案結構

```text
shopee_product_excel_data_processor_and_updater/
├── main.py                          # 主執行腳本
├── requirements.txt
├── data/
│   ├── input/                       # 放置待處理的 xlsx 檔案
│   └── backup/                      # 原始檔案備份（首次執行時自動建立）
├── temp/                            # 處理後 CSV（可直接上傳蝦皮）
├── logs/                            # 執行記錄（UTF-8）
└── scripts/
    ├── convert_input_to_csv.py      # Excel / CSV 轉換模組
    ├── gtin_processor.py            # GTIN 驗證與批次填入模組
    └── project_tree_structure_generator.py
```

---

## 環境需求

- Python 3.10+
- 依賴套件見 `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## 使用方式

### 基本執行

將待處理的 xlsx 檔案放入 `data/input/`，執行：

```bash
python main.py
```

### 完整參數

```bash
python main.py [--input PATH] [--temp PATH] [--backup PATH] [--no-overwrite-temp]
```

| 參數 | 預設值 | 說明 |
| --- | --- | --- |
| `--input` / `-i` | `data/input` | 輸入 xlsx 資料夾 |
| `--temp` / `-t` | `temp` | 處理後 CSV 的輸出資料夾 |
| `--backup` | `data/backup` | 原始檔案備份資料夾 |
| `--no-overwrite-temp` | — | 沿用現有 temp CSV，跳過步驟一 |

---

## GTIN 填入邏輯

| 條件 | 處理結果 |
| --- | --- |
| GTIN 欄位已有值 | 保留原值，跳過 |
| SKU 為空 | GTIN = `"00"` |
| SKU 為合法 GS1 條碼 | GTIN = SKU |
| 其他（內部碼、校驗碼錯誤等） | GTIN = `"00"` |

**合法 GS1 條碼條件（全部滿足）：**

1. 純數字
2. 長度為 8（EAN-8）、12（UPC-A）、13（EAN-13）或 14（ITF-14）
3. 不以 `02` 開頭（`02` 開頭為店內內部可變量條碼）
4. GS1 末位校驗碼正確

> 以 `04`、`03` 等前綴的 8 位數倉儲內部貨號，雖格式相似但校驗碼不符，會被識別為無效條碼並填入 `"00"`。

---

## 處理流程

```text
步驟一  data/input/<檔名>.xlsx
          → convert_input_to_csv.convert_excel_to_csv()
          → temp/<檔名>.csv            （原始 CSV，所有欄位為字串）

步驟二  temp/<檔名>.csv
          → 套用 GTIN 填入邏輯
          → temp/<檔名>.csv            （覆寫為處理後的 CSV，可直接上傳蝦皮）
```

---

## 模組說明

### `scripts/gtin_processor.py`

GTIN 驗證與批次填入的核心模組，可獨立匯入使用。

```python
from scripts.gtin_processor import is_valid_gtin, process_gtin

is_valid_gtin("4719512002629")  # True（合法 EAN-13）
is_valid_gtin("04114432")       # False（倉儲內部碼，校驗碼不符）
is_valid_gtin("0212345678901")  # False（02 開頭，內部條碼）
```

**公開介面：**

| 名稱 | 類型 | 說明 |
| --- | --- | --- |
| `SKU_COL` | `str` | 商品選項貨號欄位內部名稱 |
| `GTIN_COL` | `str` | GTIN 欄位內部名稱 |
| `METADATA_ROW_COUNT` | `int` | CSV 中非資料標頭列數（= 5） |
| `is_valid_gtin(value)` | `bool` | 判斷是否為合法國際流通條碼 |
| `process_gtin(df, logger)` | `dict` | 批次填入 DataFrame 中空白的 GTIN 欄位 |

### `scripts/convert_input_to_csv.py`

將 Excel（`.xlsx`、`.xlsm`）或 CSV 轉換為統一格式的 CSV，所有欄位值保留為字串。

支援自動修復含有無效 XML pane 值的 Excel 檔案。
