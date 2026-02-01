#!/usr/bin/env python3
"""
AI仏教説話自動生成・Podcast配信システム

- /stories 内の .txt を学習コンテキストとして Gemini で新説話を生成
- VOICEVOX (localhost:50021) で音声化
- podgen で feed.xml を更新
"""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# ステップ1: テキスト集約
# ステップ2: Gemini 連携
# ステップ3: VOICEVOX 連携
# ステップ4: Podcast RSS 更新
# ステップ5: メインフロー統合

load_dotenv()

# デフォルトパス
PROJECT_ROOT = Path(__file__).resolve().parent
STORIES_DIR = PROJECT_ROOT / "stories"
OUTPUT_DIR = PROJECT_ROOT / "output"
FEED_PATH = OUTPUT_DIR / "feed.xml"


# ---------------------------------------------------------------------------
# 1. テキスト集約ロジック
# ---------------------------------------------------------------------------


def load_stories_text(stories_dir: Path | str) -> str:
    """
    /stories フォルダ内のすべての .txt ファイルを読み込み、
    一つの大きなテキストブロックとして結合する。
    """
    stories_dir = Path(stories_dir)
    if not stories_dir.is_dir():
        return ""

    blocks: list[str] = []
    for path in sorted(stories_dir.glob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                blocks.append(text)
        except Exception as e:
            print(f"警告: {path} の読み込みに失敗しました: {e}")

    return "\n\n---\n\n".join(blocks) if blocks else ""


# ---------------------------------------------------------------------------
# 2. Gemini 連携ロジック
# ---------------------------------------------------------------------------


def generate_story(api_key: str, context: str, theme: str) -> dict[str, str]:
    """
    仏教説話の編纂者として、コンテキストとテーマから新説話を生成する。
    戻り値: {"title": "タイトル", "body": "本文"}
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    system_instruction = """あなたは仏教説話の編纂者です。
与えられた既存の説話集を踏まえ、同じトーン・文体・教訓の流れで新しい説話を創作してください。
出力は音声合成（TTS）に適するよう、ルビや振り仮名は一切付けず、句読点を適切に打ってください。
必ず「タイトル」と「本文」の2つだけを、以下の形式で出力してください。余計な説明は不要です。

【分量】本文はたっぷりの長さで書いてください。目安として2000字以上3500字程度（音声で約15分〜20分になる分量。短い説話の2〜2.5倍の長さ）とし、情景・登場人物の心の動き・対話・教訓が伝わるよう、丁寧にゆったりと展開してください。エピソードを増やしたり、会話や内心描写を厚くして、読み応えのある説話にしてください。

形式:
タイトル: （ここに説話のタイトルを1行で）
本文:
（ここに説話の本文を書く。段落は空行で区切る）
"""

    prompt = f"""【既存の説話集（参考コンテキスト）】
{context[:500000] if context else "（説話がまだ登録されていません。一般的な仏教説話のスタイルで創作してください。）"}

【今回のテーマ】
{theme}

上記テーマに沿った新しい説話を1本、創作してください。説話の本文は、音声で約15分〜20分になる長さ（目安: 2000字〜3500字）で、情景・対話・教訓が伝わるよう丁寧にゆったりと書いてください。短い説話の2〜2.5倍の分量にしてください。"""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.8,
            max_output_tokens=16384,
        ),
    )

    text = _get_response_text(response)
    if not text or not text.strip():
        finish_reason = (
            getattr(response.candidates[0], "finish_reason", None)
            if response.candidates
            else None
        )
        msg = "Gemini が空の応答を返しました。"
        if finish_reason == 2:
            msg += " （出力トークン上限に達した可能性があります。max_output_tokens を増やすか、コンテキストを短くしてください。）"
        raise RuntimeError(msg)
    return _parse_story_response(text)


def _get_response_text(response) -> str:
    """応答からテキストを安全に取得する。Part が無い場合も ValueError を避ける。"""
    # google.genai の response.text（空でも安全に取得）
    if hasattr(response, "text") and response.text is not None:
        return response.text if isinstance(response.text, str) else ""
    if not getattr(response, "candidates", None):
        return ""
    candidate = response.candidates[0]
    if not getattr(candidate, "content", None) or not getattr(candidate.content, "parts", None):
        return ""
    return "".join(
        getattr(p, "text", "") or ""
        for p in candidate.content.parts
    )


def _parse_story_response(text: str) -> dict[str, str]:
    """Gemini の応答から「タイトル」と「本文」を抽出する。"""
    title = ""
    body = ""
    lines = text.strip().split("\n")
    in_body = False
    body_lines: list[str] = []

    for line in lines:
        if line.startswith("タイトル:") or line.startswith("タイトル："):
            title = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            continue
        if line.startswith("本文:") or line.startswith("本文："):
            in_body = True
            rest = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            if rest:
                body_lines.append(rest)
            continue
        if in_body:
            body_lines.append(line)

    body = "\n".join(body_lines).strip()
    if not title:
        title = "説話"
    if not body:
        body = text.strip()
    return {"title": title, "body": body}


# ---------------------------------------------------------------------------
# 3. VOICEVOX 連携ロジック
# ---------------------------------------------------------------------------


def list_speakers(base_url: str = "http://localhost:50021") -> list[dict]:
    """利用可能なスピーカー一覧を取得する。"""
    import requests

    r = requests.get(f"{base_url}/speakers", timeout=10)
    r.raise_for_status()
    return r.json()


def text_to_speech(
    text: str,
    output_path: Path | str,
    speaker_id: int = 1,
    base_url: str = "http://localhost:50021",
) -> Path:
    """
    テキストを VOICEVOX API で音声合成し、分割 WAV を結合して 1 つの MP3 に保存する。
    長文の場合は句点で分割して複数リクエストし、pydub で結合して MP3 出力する。
    """
    import io

    import requests
    from pydub import AudioSegment

    output_path = Path(output_path)
    # 出力は常に MP3
    if output_path.suffix.lower() != ".mp3":
        output_path = output_path.with_suffix(".mp3")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 長文は句点で分割（1リクエストあたりの目安: 約300文字）
    max_chars = 300
    parts: list[str] = []
    buf = ""
    for c in text:
        buf += c
        if len(buf) >= max_chars and c in "。．\n":
            parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    if not parts:
        parts = [text]

    wav_chunks: list[bytes] = []
    for part in parts:
        if not part.strip():
            continue
        query_url = f"{base_url}/audio_query"
        synthesis_url = f"{base_url}/synthesis"
        params = {"text": part, "speaker": speaker_id}
        q = requests.post(query_url, params=params, timeout=30)
        q.raise_for_status()
        audio_query = q.json()
        syn = requests.post(
            synthesis_url,
            params={"speaker": speaker_id},
            json=audio_query,
            timeout=60,
        )
        syn.raise_for_status()
        wav_chunks.append(syn.content)

    if not wav_chunks:
        raise ValueError("音声データが生成されませんでした。")

    # 全 WAV チャンクを結合して MP3 に出力
    segments = [
        AudioSegment.from_file(io.BytesIO(chunk), format="wav")
        for chunk in wav_chunks
    ]
    combined = sum(segments, AudioSegment.empty())
    combined.export(str(output_path), format="mp3")
    if len(wav_chunks) > 1:
        print(f"   {len(wav_chunks)} 区間を結合して 1 つの MP3 にしました。")
    return output_path


def merge_wav_to_mp3(stem: str, output_dir: Path | str) -> Path:
    """
    既存の分割 WAV（stem.wav, stem_part2.wav, ...）を 1 つの MP3 に結合する。
    stem: 拡張子なしのベース名（例: 乾いた心に降る雨）
    """
    from pydub import AudioSegment

    output_dir = Path(output_dir)
    # stem.wav と stem_partN.wav を収集し、順序でソート
    pattern = re.compile(r"^" + re.escape(stem) + r"(?:_part(\d+))?\.wav$", re.IGNORECASE)
    wav_files: list[tuple[int, Path]] = []
    for f in output_dir.glob("*.wav"):
        m = pattern.match(f.name)
        if m:
            part_num = int(m.group(1)) if m.group(1) else 0
            wav_files.append((part_num, f))
    wav_files.sort(key=lambda x: x[0])
    paths = [p for _, p in wav_files]

    if not paths:
        raise FileNotFoundError(f"'{stem}' に一致する WAV が {output_dir} に見つかりません。")

    segments = [AudioSegment.from_file(str(p), format="wav") for p in paths]
    combined = sum(segments, AudioSegment.empty())
    out_path = output_dir / f"{stem}.mp3"
    combined.export(str(out_path), format="mp3")
    print(f"   {len(paths)} ファイルを結合して {out_path.name} を保存しました。")
    return out_path


def generate_procedural_bgm(
    duration_sec: float,
    sample_rate: int = 44100,
    loop_sec: float = 24.0,
) -> "AudioSegment":
    """
    著作権フリーの手続きBGMを生成する。
    静かなアンビエントパッド（低音の正弦波の重ね合わせ）をループで延長する。
    """
    import numpy as np
    from pydub import AudioSegment

    # 落ち着いた和音（A1, E2, A2, E3 に近い周波数）
    freqs = [55.0, 82.5, 110.0, 165.0]
    amps = [0.12, 0.08, 0.06, 0.04]
    fade_sec = 2.0
    n_loop = int(sample_rate * loop_sec)
    n_fade = int(sample_rate * fade_sec)
    t_loop = np.arange(n_loop) / sample_rate
    envelope = np.ones(n_loop)
    envelope[:n_fade] = np.linspace(0, 1, n_fade)
    envelope[-n_fade:] = np.linspace(1, 0, n_fade)
    wave = np.zeros(n_loop)
    for f, a in zip(freqs, amps):
        wave += a * envelope * np.sin(2 * np.pi * f * t_loop)
    peak = np.abs(wave).max()
    if peak > 0:
        wave = wave / peak * 0.35
    n_total = int(sample_rate * duration_sec)
    n_repeat = (n_total // n_loop) + 1
    full = np.tile(wave, n_repeat)[:n_total]
    samples = (np.clip(full, -1, 1) * 32767).astype(np.int16)
    return AudioSegment(
        data=samples.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )


def mix_voice_with_bgm(
    voice_path: Path | str,
    output_path: Path | str,
    bgm_volume_db: float = -20.0,
) -> Path:
    """
    音声ファイルに手続き生成BGMを重ねて出力する。
    BGM は著作権フリーの自動生成を使用する。
    """
    from pydub import AudioSegment

    voice_path = Path(voice_path)
    output_path = Path(output_path)
    voice = AudioSegment.from_file(str(voice_path))
    duration_ms = len(voice)
    duration_sec = duration_ms / 1000.0
    bgm = generate_procedural_bgm(duration_sec, sample_rate=voice.frame_rate)
    if voice.frame_rate != bgm.frame_rate:
        bgm = bgm.set_frame_rate(voice.frame_rate)
    if voice.channels != bgm.channels:
        bgm = bgm.set_channels(voice.channels)
    bgm = bgm[:duration_ms]
    bgm = bgm.apply_gain(bgm_volume_db)
    mixed = voice.overlay(bgm)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mixed.export(str(output_path), format="mp3")
    return output_path


def merge_all_split_wavs_in_dir(output_dir: Path | str) -> None:
    """
    output_dir 内の分割 WAV（stem.wav, stem_part2.wav, ...）を検出し、
    それぞれ 1 本の MP3 に結合する。パイプラインのデフォルト処理として呼ぶ。
    """
    output_dir = Path(output_dir)
    if not output_dir.is_dir():
        return
    # _partN.wav を持つ stem を収集（N は 2 以上；part1 は stem.wav として扱う）
    stem_has_parts: set[str] = set()
    for f in output_dir.glob("*.wav"):
        m = re.match(r"^(.+)_part(\d+)\.wav$", f.name, re.IGNORECASE)
        if m:
            stem_has_parts.add(m.group(1))
    if stem_has_parts:
        print("0. 分割 WAV を 1 本の MP3 に結合しています...")
    for stem in stem_has_parts:
        try:
            merge_wav_to_mp3(stem, output_dir)
        except FileNotFoundError:
            pass
        except Exception:
            pass  # 既に MP3 化済みなどは無視


# ---------------------------------------------------------------------------
# 4. Podcast RSS 更新ロジック
# ---------------------------------------------------------------------------


def update_podcast_feed(
    output_dir: Path | str,
    feed_path: Path | str,
    podcast_title: str = "仏教説話ポッドキャスト",
    podcast_description: str = "AIが生成する仏教説話を毎日お届けします。",
    podcast_website: str = "",
    podcast_base_url: str = "",
) -> Path:
    """
    /output 内の音声ファイルをエピソードとして feed.xml を生成・更新する。
    podcast_base_url: 音声ファイルの公開URLのベース（例: https://example.com/podcast）
    """
    from datetime import datetime, timezone

    from podgen import Media, Podcast

    output_dir = Path(output_dir)
    feed_path = Path(feed_path)
    feed_path.parent.mkdir(parents=True, exist_ok=True)

    # 既存の feed があれば読み込み、なければ新規作成
    p = Podcast()
    p.name = podcast_title
    p.description = podcast_description
    p.website = podcast_website or "https://example.com"
    p.explicit = False

    # output 内の音声ファイルを新しい順にエピソードとして追加（feed.xml 自体は除外）
    audio_extensions = {".wav", ".mp3"}
    audio_files: list[Path] = []
    for f in output_dir.iterdir():
        if f.suffix.lower() in audio_extensions and f.name != "feed.xml":
            audio_files.append(f)
    audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # podgen は .wav を標準で扱わないため、MIME タイプを明示する
    mime_by_ext = {".wav": "audio/wav", ".mp3": "audio/mpeg"}
    for i, audio_path in enumerate(audio_files):
        size = audio_path.stat().st_size
        # ファイル名からタイトルを推測（拡張子除去）
        title = audio_path.stem.replace("_", " ").replace("-", " ")
        media_url = f"{podcast_base_url.rstrip('/')}/{audio_path.name}" if podcast_base_url else f"file://{audio_path.resolve()}"
        media_type = mime_by_ext.get(audio_path.suffix.lower(), "audio/mpeg")
        e = p.add_episode()
        e.title = title
        e.media = Media(media_url, size=size, type=media_type)
        e.publication_date = datetime.fromtimestamp(audio_path.stat().st_mtime, tz=timezone.utc)

    p.rss_file(str(feed_path), minimize=False)
    return feed_path


# ---------------------------------------------------------------------------
# 5. メインフロー統合（CLI）
# ---------------------------------------------------------------------------


def run_pipeline(
    theme: str,
    stories_dir: Path | str = STORIES_DIR,
    output_dir: Path | str = OUTPUT_DIR,
    feed_path: Path | str = FEED_PATH,
    speaker_id: int = 1,
    voicevox_url: str = "http://localhost:50021",
    add_bgm: bool = False,
    bgm_volume_db: float = -20.0,
) -> None:
    """説話生成 → 音声化 → RSS 更新まで一括実行する。"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("環境変数 GEMINI_API_KEY が設定されていません。.env を確認してください。", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # デフォルト: output 内の分割 WAV を 1 本の MP3 に結合する
    merge_all_split_wavs_in_dir(output_dir)

    print("1. 説話テキストを読み込んでいます...")
    context = load_stories_text(stories_dir)
    print(f"   読み込み: {len(context)} 文字")

    print("2. Gemini で説話を生成しています...")
    story = generate_story(api_key, context, theme)
    print(f"   タイトル: {story['title']}")

    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in story["title"])[:60]
    audio_path = output_dir / f"{safe_title}.mp3"

    # 法話テキストを .txt で保存
    text_path = output_dir / f"{safe_title}.txt"
    text_path.write_text(
        f"タイトル: {story['title']}\n\n{story['body']}",
        encoding="utf-8",
    )
    print(f"   テキスト保存: {text_path}")

    print("3. VOICEVOX で音声化しています...")
    text_to_speech(
        story["body"],
        audio_path,
        speaker_id=speaker_id,
        base_url=voicevox_url,
    )
    print(f"   保存: {audio_path}")

    if add_bgm:
        print("3.5. BGM を追加しています...")
        mix_voice_with_bgm(audio_path, audio_path, bgm_volume_db=bgm_volume_db)
        print(f"   BGM 付きで上書き: {audio_path}")

    podcast_title = os.environ.get("PODCAST_TITLE", "仏教説話ポッドキャスト")
    podcast_description = os.environ.get("PODCAST_DESCRIPTION", "AIが生成する仏教説話を毎日お届けします。")
    podcast_website = os.environ.get("PODCAST_WEBSITE", "")
    podcast_base_url = os.environ.get("PODCAST_BASE_URL", "")

    print("4. Podcast RSS を更新しています...")
    update_podcast_feed(
        output_dir,
        feed_path,
        podcast_title=podcast_title,
        podcast_description=podcast_description,
        podcast_website=podcast_website,
        podcast_base_url=podcast_base_url,
    )
    print(f"   保存: {feed_path}")

    print("完了しました。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI仏教説話自動生成・Podcast配信システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python main.py --theme "慈悲"
  python main.py --theme "欲と知足" --speaker 3
  python main.py --theme "忍辱" --voicevox-url http://127.0.0.1:50021
  python main.py --list-speakers
  python main.py --merge-wav "乾いた心に降る雨"  # 分割 WAV を 1 つの MP3 に結合
  python main.py --update-feed  # feed.xml のみ再生成（PODCAST_BASE_URL 反映・iPhone 用）
  python main.py --theme "慈悲" --add-bgm  # 手続き生成BGMを追加（著作権フリー）
        """,
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="",
        help="今回の説話のテーマ（例: 慈悲、忍辱、知足）",
    )
    parser.add_argument(
        "--speaker",
        type=int,
        default=1,
        help="VOICEVOX のスピーカーID（デフォルト: 1）",
    )
    parser.add_argument(
        "--voicevox-url",
        type=str,
        default="http://localhost:50021",
        help="VOICEVOX Engine の URL（デフォルト: http://localhost:50021）",
    )
    parser.add_argument(
        "--stories-dir",
        type=Path,
        default=STORIES_DIR,
        help=f"既存説話 .txt のディレクトリ（デフォルト: {STORIES_DIR}）",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"音声と feed.xml の出力先（デフォルト: {OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--list-speakers",
        action="store_true",
        help="VOICEVOX のスピーカー一覧を表示して終了",
    )
    parser.add_argument(
        "--merge-wav",
        type=str,
        metavar="STEM",
        default="",
        help="既存の分割 WAV（STEM.wav, STEM_part2.wav, ...）を 1 つの MP3 に結合する。例: --merge-wav \"乾いた心に降る雨\"",
    )
    parser.add_argument(
        "--update-feed",
        action="store_true",
        help="output 内の分割 WAV を結合し、feed.xml のみ再生成する（.env の PODCAST_BASE_URL を反映）。iPhone 用 URL 更新時に使用",
    )
    parser.add_argument(
        "--add-bgm",
        action="store_true",
        help="音声に手続き生成BGMを重ねる（著作権フリー・自動生成）。",
    )
    parser.add_argument(
        "--bgm-volume",
        type=float,
        default=-20.0,
        metavar="DB",
        help="BGM の音量（dB）。小さいほど小さい。デフォルト: -20",
    )

    args = parser.parse_args()

    if args.update_feed:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        merge_all_split_wavs_in_dir(output_dir)
        print("feed.xml を更新しています...")
        update_podcast_feed(
            output_dir,
            output_dir / "feed.xml",
            podcast_title=os.environ.get("PODCAST_TITLE", "仏教説話ポッドキャスト"),
            podcast_description=os.environ.get("PODCAST_DESCRIPTION", "AIが生成する仏教説話を毎日お届けします。"),
            podcast_website=os.environ.get("PODCAST_WEBSITE", ""),
            podcast_base_url=os.environ.get("PODCAST_BASE_URL", ""),
        )
        print(f"保存: {output_dir / 'feed.xml'}")
        print("完了しました。")
        return

    if args.merge_wav.strip():
        output_dir = Path(args.output_dir)
        try:
            out_path = merge_wav_to_mp3(args.merge_wav.strip(), output_dir)
            print("RSS を更新しています...")
            update_podcast_feed(
                output_dir,
                output_dir / "feed.xml",
                podcast_title=os.environ.get("PODCAST_TITLE", "仏教説話ポッドキャスト"),
                podcast_description=os.environ.get("PODCAST_DESCRIPTION", "AIが生成する仏教説話を毎日お届けします。"),
                podcast_website=os.environ.get("PODCAST_WEBSITE", ""),
                podcast_base_url=os.environ.get("PODCAST_BASE_URL", ""),
            )
            print("完了しました。")
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"WAV の結合に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.list_speakers:
        try:
            speakers = list_speakers(args.voicevox_url)
            for s in speakers:
                name = s.get("name", "?")
                for style in s.get("styles", []):
                    print(f"  ID {style['id']}: {name} - {style.get('name', '')}")
        except Exception as e:
            print(f"スピーカー一覧の取得に失敗しました: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.theme.strip():
        parser.error("--theme を指定してください。例: --theme 慈悲")

    run_pipeline(
        theme=args.theme.strip(),
        stories_dir=args.stories_dir,
        output_dir=args.output_dir,
        feed_path=args.output_dir / "feed.xml",
        speaker_id=args.speaker,
        voicevox_url=args.voicevox_url,
        add_bgm=args.add_bgm,
        bgm_volume_db=args.bgm_volume,
    )


if __name__ == "__main__":
    main()
