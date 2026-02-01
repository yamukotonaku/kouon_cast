# BGM の追加について

音声に BGM を重ねる方法は次のとおりです。**著作権に触れない**よう、自動生成の BGM を利用しています。

---

## 方法 1: 手続き生成 BGM（標準・軽量）

**著作権フリー**の BGM をプログラムで自動生成し、音声に重ねます。

- **仕組み**: 低音の正弦波を重ねたパッドに、**scipy** でローパスフィルタ（温かみ）とゆっくりした振幅のうねり（LFO）をかけ、落ち着いたアンビエントにしています。
- **著作権**: コードで生成するため **著作権は発生しません**。個人利用・配信ともに利用可能です。
- **使い方**（デフォルト）:
  ```bash
  python main.py --theme "慈悲" --add-bgm
  ```
- **音量**: BGM を小さくしたい場合は `--bgm-volume` で指定（単位は dB）。
  ```bash
  python main.py --theme "慈悲" --add-bgm --bgm-volume -24
  ```
  デフォルトは `-20` dB です。

---

## 方法 2: AI 音楽生成（MusicGen）

より「曲らしい」BGM にしたい場合は、**--bgm-style musicgen** で Meta の MusicGen を使えます。

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

- **使い方**:
  ```bash
  python main.py --theme "慈悲" --add-bgm --bgm-style musicgen
  ```
- **初回**: MusicGen のモデル（facebook/musicgen-small、約 2.4GB）が Hugging Face から自動ダウンロードされます。2 回目以降はキャッシュを使用します。
- **プロンプト**: デフォルトは "calm ambient meditation peaceful soft pad no drums" です。コード内で変更可能です。
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
| 手続き BGM | `--add-bgm`（既定） | なし | ◎ | ローパス＋LFO の落ち着いたパッド |
| MusicGen | `--add-bgm --bgm-style musicgen` | CC-BY-NC | △（要 torch） | 曲っぽいアンビエント |

**自分用ポッドキャストで安全に使うなら、`--add-bgm` の手続き BGM を推奨します。** より良い感じにしたい場合は `--bgm-style musicgen` を試してください（要 transformers / torch）。
