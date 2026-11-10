# jaxa-earth-mcp

指定範囲・月の植生指数（NDVI）が平年値とどれだけ違うかを、画像と数値で確認できます。読み取り専用で、APIキーの設定は不要です。[uv](https://docs.astral.sh/uv/) と Git が必要です。Python 3.12以上に対応しています。

## MCPクライアントに登録する

このリポジトリへのアクセス権がある環境でクローンします。

```sh
git clone https://github.com/koizumikento/jaxa-earth-mcp.git
cd jaxa-earth-mcp
uv sync --locked
```

以下の `/absolute/path/to/jaxa-earth-mcp` は、クローン先の絶対パスに置き換えてください。Windowsでも `C:/projects/jaxa-earth-mcp` のようにスラッシュで指定できます。

### Codex

```sh
codex mcp add jaxa-earth-mcp -- uv --directory "/absolute/path/to/jaxa-earth-mcp" run --locked jaxa-earth-mcp
codex mcp list
```

`codex mcp list` で登録を確認し、Codexの新しいセッションで `/mcp` を開くと、接続状態を確認できます。[Codexの公式設定ガイド](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)

Codexのデスクトップアプリでは、設定の「MCP servers」でSTDIOサーバーを追加し、下のJSON例と同じコマンド・引数を指定する方法もあります。

### Claude Desktop / Cursor

次のファイルに設定します。

- Claude Desktop（Windows） `%APPDATA%/Claude/claude_desktop_config.json`
- Claude Desktop（macOS） `~/Library/Application Support/Claude/claude_desktop_config.json`
- Cursor `.cursor/mcp.json`（プロジェクト内）

既に `mcpServers` がある場合は、その中にサーバーの項目を追加してください。保存後にクライアントを再起動し、ツールが表示されるか確認します。[設定ファイルの場所と接続手順](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)

```json
{
  "mcpServers": {
    "jaxa-earth-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/jaxa-earth-mcp",
        "run",
        "--locked",
        "jaxa-earth-mcp"
      ]
    }
  }
}
```

`uv` が見つからない場合は、設定のコマンドに実行ファイルの絶対パスを指定してください。

登録後は、チャットで次のように聞けます。

> 北緯36〜37度、東経138.5〜139.5度の2021年8月の植生指数を平年と比べて。

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
