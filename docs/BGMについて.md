# BGM の追加について

音声に BGM を重ねる方法は次のとおりです。**著作権に触れない**よう、自動生成の BGM を利用しています。

---

## 方法 1: 手続き生成 BGM（軽量・著作権フリー）

**著作権フリー**の BGM をプログラムで自動生成し、音声に重ねます。

- **仕組み**: 低音の正弦波を重ねたパッドに、**scipy** でローパスフィルタ（温かみ）とゆっくりした振幅のうねり（LFO）をかけ、落ち着いたアンビエントにしています。
- **著作権**: コードで生成するため **著作権は発生しません**。個人利用・配信ともに利用可能です。
- **使い方**: デフォルトは MusicGen のため、手続き BGM を使う場合は `--bgm-style procedural` を指定します。
  ```bash
  python main.py --theme "慈悲" --bgm-style procedural
  ```
- **音量**: BGM の音量は `--bgm-volume` で指定（単位は dB）。デフォルトは `-18` dB です。
  ```bash
  python main.py --theme "慈悲" --bgm-volume -24
  ```

---

## 方法 2: AI 音楽生成（MusicGen）【デフォルト】

**デフォルト**で、Meta の MusicGen により「曲らしい」BGM を自動追加します。

- **前提**: NumPy を 1.x に揃え、`transformers` と `torch` をインストールする必要があります（GPU 推奨）。  
  **NumPy 2.x と PyTorch は互換性がないため、MusicGen 利用時は必ず NumPy 1.x にしてください。**

  **MusicGen を有効にする手順**（プロジェクトルートで）:
  ```bash
  # 依存を揃えてインストール（numpy<2 が requirements.txt に含まれています）
  pip install -r requirements.txt

  # すでに NumPy 2.x を入れている場合は、一度ダウングレード
  pip install "numpy>=1.24.0,<2"
  ```
  これで `transformers` / `torch` / `accelerate` と NumPy 1.x が入り、MusicGen が利用可能になります。

- **使い方**（オプション指定なしで BGM 付き）:
  ```bash
  python main.py --theme "慈悲"
  ```
  BGM を付けない場合は `--no-bgm` を指定します。
- **初回**: MusicGen のモデル（facebook/musicgen-small、約 2.4GB）が Hugging Face から自動ダウンロードされます。2 回目以降はキャッシュを使用します。
- **プロンプト**: デフォルトは "soft piano gentle strings meditation" です。
- **テイストの変更**: `--bgm-prompt` で MusicGen のプロンプトを上書きできます。
  ```bash
  python main.py --theme "慈悲"  # デフォルト: soft piano gentle strings
  python main.py --theme "慈悲" --bgm-prompt "zen temple bell ambient drone"
  ```
  英語のキーワード（calm, ambient, piano, strings, meditation, drone, no drums など）を並べると雰囲気を変えられます。
- **音量**: BGM の音量は `--bgm-volume` で指定（単位は dB）。デフォルトは `-18` dB です。
- **ライセンス**: **CC-BY-NC（非商用）**。個人用ポッドキャストであれば利用可能な場合があります。利用前にライセンスを確認してください。
- **注意**: MusicGen が使えない環境（NumPy 2.x のまま・メモリ不足など）では、自動で手続き BGM にフォールバックします。

---

## 方法 3: その他の AI 音楽（手動）

より「曲らしい」BGM にしたい場合は、**Meta の MusicGen** などで BGM を生成し、手動でミックスする方法があります。

- **MusicGen (Meta AudioCraft)**  
  - テキストプロンプトから音楽を生成。  
  - **ライセンス**: CC-BY-NC（**非商用**）。個人用ポッドキャストであれば利用可能な場合がありますが、利用前にライセンスを確認してください。  
  - ローカル実行には PyTorch と GPU 推奨。Hugging Face の [MusicGen](https://huggingface.co/facebook/musicgen-melody) などで生成した WAV/MP3 を、本プロジェクトの `mix_voice_with_bgm` と同様の手順（pydub で音声と BGM を overlay）でミックスできます。

本プロジェクトのパイプラインには標準では組み込んでいません。BGM ファイルを別途用意し、pydub で音声と重ねるスクリプトを自作する形になります。

---

## まとめ

| 方法 | オプション | 著作権 | 手軽さ | 音のイメージ |
|------|-------------|--------|--------|----------------|
| MusicGen | （既定・オプション不要） | CC-BY-NC | △（要 torch） | 曲っぽいアンビエント |
| 手続き BGM | `--bgm-style procedural` | なし | ◎ | ローパス＋LFO の落ち着いたパッド |
| BGM なし | `--no-bgm` | - | - | - |

**デフォルトは MusicGen で BGM を追加します。** 著作権を気にしない場合は手続き BGM（`--bgm-style procedural`）も利用できます。
