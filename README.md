# jaxa-earth-mcp

JAXA Earthの衛星データを調べるMCPサーバーです。指定した範囲の植生指数（NDVI）の月別推移を調べたり、平年値との差を画像で見たりできます。衛星データのコレクションと収録バンドも検索できます。読み取り専用で、APIキーの設定は不要です。[uv](https://docs.astral.sh/uv/) と Git が必要です。Python 3.12以上に対応しています。

[MCP登録](#mcpクライアントに登録する) · [CLI](#cliで使う) · [Pythonライブラリ](#pythonライブラリとして使う)

## MCPクライアントに登録する

[uv](https://docs.astral.sh/uv/) と Git を用意し、リポジトリをクローンします。Python 3.12以上が必要です。

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

| やりたいこと | MCPツール | 主な入力 |
| --- | --- | --- |
| 指定月の植生指数を平年値と比較する | `get_ndvi_anomaly` | `month`、`bbox` |
| 植生指数の実測値が月ごとにどう変わったかを調べる | `get_ndvi_time_series` | `start_month`、`end_month`、`bbox` |
| 利用可能な衛星データとバンド名を調べる | `search_collections` | `query`、任意で `limit` と `offset` |

月は `YYYY-MM` 形式です。範囲 `bbox` は WGS84 の経緯度を西・南・東・北の順で指定します。縦・横とも0.2〜5度で、日付変更線をまたぐ範囲には対応していません。

### 植生指数の平年差

たとえば `{"month":"2021-08","bbox":[138.5,36,139.5,37]}` と指定します。JAXA Earth API for Pythonで、MODISの月別NDVIから同月の2012〜2021年平年値を引き、差の地図（PNG）と範囲内の要約統計を返します。画像はMCPの標準画像コンテンツで返し、表示はクライアントの画像対応に依存します。

### 植生指数の月別推移

たとえば `{"start_month":"2021-07","end_month":"2021-08","bbox":[138.5,36,139.5,37]}` と指定します。指定期間の各月について、観測値の範囲内平均・標準偏差・最小値・最大値・中央値を返します。期間は開始月と終了月を含む最大12か月です。

結果の `observations` は月順です。観測値を得られた月の `status` は `observed` です。欠損月の `statistics` は `null` になります。

| 欠損時の `status` | 意味 |
| --- | --- |
| `not_available` | 指定月のデータがカタログにない |
| `no_coverage` | 指定範囲と重なる画像タイルがない |
| `no_valid_pixels` | 指定範囲内に有効な画素がない |

### コレクションとバンドの検索

たとえば `{"query":"NDVI monthly","limit":5}` と指定します。大文字・小文字を区別せず、空白で区切った検索語をすべて含むコレクションIDを探し、バンド名とコレクションの公式カタログURLを返します。1ページは最大10件（既定5件）です。次のページは返却された `next_offset` を `offset` に指定し、`next_offset` が `null` なら最終ページです。

## CLIで使う

上の登録手順でクローンしたディレクトリで実行します。

```sh
uv run jaxa-earth-mcp get-ndvi-anomaly --month 2021-08 --bbox 138.5 36 139.5 37 --output anomaly.png
uv run jaxa-earth-mcp get-ndvi-time-series --start-month 2021-07 --end-month 2021-08 --bbox 138.5 36 139.5 37
uv run jaxa-earth-mcp search-collections --query "NDVI monthly" --limit 5
```

結果は標準出力にUTF-8のJSONで出力します。各コマンドの引数は `--help` で確認できます。平年差の地図は `--output` で新規ファイルに保存できます。

## Pythonライブラリとして使う

自分のPythonプロジェクト（`pyproject.toml` があるディレクトリ）で依存関係に追加します。

```sh
uv add "git+https://github.com/koizumikento/jaxa-earth-mcp.git@main"
```

次のコードを `example.py` に保存し、同じディレクトリで `uv run python example.py` を実行します。

```python
import asyncio

from jaxa_earth_mcp import get_ndvi_anomaly, get_ndvi_time_series, search_collections

bbox = [138.5, 36, 139.5, 37]
anomaly = asyncio.run(get_ndvi_anomaly(month="2021-08", bbox=bbox))
print(anomaly.metadata)
png_bytes = anomaly.png

series = asyncio.run(get_ndvi_time_series("2021-07", "2021-08", bbox))
print(series["observations"])

catalog = asyncio.run(search_collections("NDVI monthly", limit=5))
print(catalog["collections"])
```

イベントループがある環境では、関数を直接 `await` します。

## 出典と利用条件

このソフトウェアは JAXA Earth API for Python のモジュールを利用しています。衛星データは実行時に取得し、このリポジトリには同梱していません。コードは MIT License です。取得したデータは、データセットごとの STAC に記載された利用条件に従ってください。結果を公表する場合は、JAXA Earth API を利用したことを明記してください。[公式仕様](https://data.earth.jaxa.jp/api/python/v0.1.6/ja/tutorials/python/) · [利用条件](https://data.earth.jaxa.jp/ja/)

## 開発

```sh
uv sync --locked
uv run ruff check .
uv run ty check
uv run pytest
uv build
```
