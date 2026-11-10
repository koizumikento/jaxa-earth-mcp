# jaxa-earth-mcp

JAXA Earth 植生指数の平年差の読み取り専用MCPサーバーです。Python 3.12以上とuv（0.13.4で検証）を使います。上流APIキーの設定は不要です。

## MCPクライアント設定

```sh
git clone https://github.com/koizumikento/jaxa-earth-mcp.git
cd jaxa-earth-mcp
uv sync --locked
```

クライアントの設定に、クローン先の絶対パスを指定します。

```json
{
  "mcpServers": {
    "jaxa-earth-mcp": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/jaxa-earth-mcp", "run", "--locked", "jaxa-earth-mcp"]
    }
  }
}
```

## ツール

`get_ndvi_anomaly` で範囲と月を指定し、植生指数の平年差のPNGと要約統計を取得できます。

```json
{
  "month": "2021-08",
  "bbox": [
    138.5,
    36,
    139.5,
    37
  ]
}
```

JAXA Earth API for Pythonを使用。MODIS月別NDVIから同月の2012〜2021年平年値を引きます。範囲はWGS84の西・南・東・北で、日付変更線をまたがない0.2〜5度四方です。画像は標準のMCP画像コンテンツで返し、表示はクライアントの画像対応に依存します。欠損の扱いは公式SDKに従います。

## CLI

```sh
uv run jaxa-earth-mcp get-ndvi-anomaly --month 2021-08 --bbox 138.5 36 139.5 37 --output anomaly.png
```

結果は標準出力にUTF-8のJSONで出力します。コマンドの引数は `uv run jaxa-earth-mcp get-ndvi-anomaly --help` で確認できます。`--output` でPNGを新規ファイルに保存できます。

## Pythonライブラリ

パッケージをインストールしたPython環境で、下記の非同期関数を直接呼び出せます。

```python
import asyncio

from jaxa_earth_mcp import get_ndvi_anomaly

result = asyncio.run(get_ndvi_anomaly(month="2021-08", bbox=[138.5, 36, 139.5, 37]))
print(result.metadata)
png_bytes = result.png
```

公開関数 `get_ndvi_anomaly` を利用できます。イベントループがある環境では、関数を直接 `await` します。

## 出典と利用条件

コードはMIT Licenseです。上流データの権利と利用条件は各提供元の定めに従います。[公式仕様](https://data.earth.jaxa.jp/api/python/v0.1.6/ja/tutorials/python/) · [利用案内](https://data.earth.jaxa.jp/ja/)

## 開発

```sh
uv sync --locked
uv run ruff check .
uv run ty check
uv run pytest
uv build
```
