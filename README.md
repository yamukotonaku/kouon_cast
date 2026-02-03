# 香音キャスト（kouon_cast）

AI が生成する仏教説話を VOICEVOX で音声化し、Podcast として配信するシステムです。

---

## 必要な環境

- **Python 3.10+**
- **Google Gemini API キー**（[Google AI Studio](https://aistudio.google.com/apikey) で取得）
- **VOICEVOX**（[公式](https://voicevox.hiroshiba.jp/)）を起動し、Engine API が `http://localhost:50021` で動いていること
- **ffmpeg**（MP3 出力用。`pydub` が使用）

---

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/yamukotonaku/kouon_cast.git
cd kouon_cast

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定（.env.example をコピーして編集）
cp .env.example .env
# .env に GEMINI_API_KEY を記入
```

VOICEVOX を起動した状態で、以下を実行すると説話が 1 本生成され、`output/` にテキスト・MP3・feed.xml が出力されます。

---

## 使い方

### 基本：説話を 1 本生成する

```bash
# テーマをランダムに選んで 1 本生成（説話 → 音声化 → BGM 付き → feed 更新）
python main.py

# テーマを指定して生成
python main.py --theme "慈悲"
python main.py --theme "忍辱 — 雨の日、誰かに傘を差す／差される"
```

- 出力先: `output/`（日付付きの `.txt` と `.mp3`、および `feed.xml`）
- デフォルトで **MusicGen** による BGM 付き。`--no-bgm` で BGM なし、`--bgm-style procedural` で軽量な手続き BGM に変更可能

### よく使うオプション

| オプション | 説明 |
|-----------|------|
| `--theme "テーマ"` | 説話のテーマを指定（未指定時はランダム） |
| `--no-bgm` | BGM を付けない |
| `--bgm-style procedural` | BGM を手続き生成に（MusicGen 不要・軽量） |
| `--speaker 9` | VOICEVOX のスピーカー ID（デフォルト: 9） |
| `--voicevox-url URL` | VOICEVOX Engine の URL（デフォルト: http://localhost:50021） |
| `--voicevox-user-dict CSV` | ユーザー辞書用 CSV のパス（未指定時は `voicevox_user_dict.csv` があれば使用） |
| `--update-feed` | 説話生成は行わず、`output/` の内容で feed.xml のみ再生成 |
| `--list-speakers` | 利用可能な VOICEVOX スピーカー一覧を表示して終了 |

### ユーザー辞書（読みの調整）

`voicevox_user_dict.csv` に「表記,読み,アクセント型[,優先度]」の形式で行を追加すると、音声化の直前に VOICEVOX のユーザー辞書へ自動登録されます。サンプルは `voicevox_user_dict.csv.example` を参照してください。

### feed.xml だけ更新したいとき

音声ファイルの URL を変更した場合（例: GitHub Pages 用に `PODCAST_BASE_URL` を設定したあと）は、次で feed のみ再生成します。

```bash
python main.py --update-feed
```

---

## Podcast として聴く

本番の feed は GitHub Pages で配信しています。Podcast アプリで次の URL を登録すると、エピソード一覧と音声を取得できます。

- **RSS（feed）URL**:  
  **https://yamukotonaku.github.io/kouon_cast/feed.xml**

### 登録手順の例

1. Podcast アプリ（Apple Podcasts、Spotify、Overcast、Pocket Casts など）を開く
2. 「番組を追加」「URL で追加」「Add by URL」など、RSS を追加する機能を選ぶ
3. 上記の **feed.xml** の URL を入力して追加

追加後は、新しいエピソードが配信されるとアプリに表示され、ストリーミングやダウンロードで聴けます。

---

## ディレクトリ構成（概要）

| パス | 説明 |
|------|------|
| `main.py` | 説話生成・音声化・feed 更新のメインスクリプト |
| `output/` | 生成された説話の .txt / .mp3 と feed.xml |
| `knowledge/` | 説話生成時に参照する仏教知識（Markdown） |
| `voicevox_user_dict.csv` | VOICEVOX ユーザー辞書用 CSV（任意） |
| `docs/` | [GitHub Pages でのホスティング手順](docs/GitHub_Pagesでホスティングする手順.md)、[iPhone で聴く手順](docs/iPhoneで聴く手順.md)、[BGM について](docs/BGMについて.md) |

---

## 詳細ドキュメント

- **GitHub Pages にデプロイする**: [docs/GitHub_Pagesでホスティングする手順.md](docs/GitHub_Pagesでホスティングする手順.md)
- **iPhone で聴く**: [docs/iPhoneで聴く手順.md](docs/iPhoneで聴く手順.md)
- **BGM の種類とオプション**: [docs/BGMについて.md](docs/BGMについて.md)
