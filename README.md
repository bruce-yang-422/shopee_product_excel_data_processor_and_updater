# 蝦皮 GTIN 批次處理器

自動讀取蝦皮商品批次更新 Excel，依 SKU 規則填入空白的 GTIN（國際條碼）欄位，輸出可直接上傳蝦皮的 CSV 檔案。

---

## 功能概述

- 批次處理 `data/input/` 下所有符合命名規則的 Excel 檔案
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

## 檔案命名規則

輸入檔案需符合以下命名格式，否則會被略過：

```text
SH????_*商品資料*_??.xlsx
```

範例：`SH0005_有才寵物商店_商品資料_01.xlsx`

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
