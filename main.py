#!/usr/bin/env python3
"""
AI仏教説話自動生成・Podcast配信システム

- /stories 内の .txt を学習コンテキストとして Gemini で新説話を生成
- VOICEVOX (localhost:50021) で音声化
- podgen で feed.xml を更新
"""

import argparse
import os
import random
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

# テーマ未指定時にランダムで選ぶ候補（古典的な徳目＋少し意外なテーマ）
RANDOM_THEMES = [
    "慈悲",
    "忍辱",
    "知足",
    "無常",
    "因果",
    "布施",
    "智慧",
    "欲と知足",
    "執着を手放す",
    "落ち葉と掃除僧",
    "泥棒とお坊さん",
    "一輪の花",
    "空の茶碗",
    "雨の日の托鉢",
    "名前のない修行者",
    "象と蟻の教え",
    "壊れた鐘の音",
    "旅の途中の出会い",
    "川を渡る渡し守",
    "灯りを消した部屋",
    "一粒の米",
    "老いた木と若い芽",
    "沈黙の功徳",
    "問わず語り",
]


def pick_random_theme() -> str:
    """テーマ未指定時に使うランダムなテーマを返す。"""
    return random.choice(RANDOM_THEMES)


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

【意外性】説話には、聞き手が「なるほど」「意外だ」と感じるようなひねりや視点の転換を織り交ぜてください。型通りの教訓だけでなく、予想外の登場人物（泥棒、子ども、動物、名もなき老人など）、逆説的な結末、身近な比喩や意外な対比を使うと、印象に残りやすくなります。古典の枠を守りつつ、少し意外性のある展開を心がけてください。

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


def generate_story_summary(api_key: str, title: str, body: str) -> str:
    """
    説話のタイトルと本文から、Podcast エピソード説明用の短いサマリーを Gemini で生成する。
    戻り値: 2〜3文の要約（失敗時は空文字）
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = f"""以下の仏教説話の要約を、2〜3文で書いてください。
Podcast のエピソード説明（ショート説明）に使うため、聞き手が「どんな話か」を一目で分かるようにしてください。
余計な前置きや「要約は以下の通りです」などの説明は不要です。要約文だけを出力してください。

【タイトル】
{title}

【本文（抜粋）】
{body[:8000] if len(body) > 8000 else body}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=512,
            ),
        )
        text = _get_response_text(response)
        summary = (text or "").strip()
        # 1行にまとめて改行をスペースに（Podcast 説明向け）
        if summary:
            summary = " ".join(summary.split())
        return summary[:1000] if summary else ""
    except Exception:
        return ""


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
    複数層の正弦波にデチューン・2段LFO・ローパスをかけ、
    落ち着いたアンビエントパッドにする。numpy/scipy のみ使用。
    """
    import numpy as np
    from pydub import AudioSegment
    from scipy.signal import butter, sosfiltfilt

    # 基音＋ややデチューンした倍音で厚みとうねり（うなり）
    freqs = [55.0, 82.5, 110.0, 164.0, 220.0]
    amps = [0.12, 0.08, 0.06, 0.04, 0.02]
    fade_sec = 3.0
    n_loop = int(sample_rate * loop_sec)
    n_fade = int(sample_rate * fade_sec)
    t_loop = np.arange(n_loop, dtype=np.float64) / sample_rate
    envelope = np.ones(n_loop)
    envelope[:n_fade] = np.linspace(0, 1, n_fade)
    envelope[-n_fade:] = np.linspace(1, 0, n_fade)
    wave = np.zeros(n_loop)
    for f, a in zip(freqs, amps):
        # 中心周波数とわずかにずらした2本でうなり・厚み
        wave += a * envelope * np.sin(2 * np.pi * f * t_loop)
        wave += 0.4 * a * envelope * np.sin(2 * np.pi * (f * 1.004) * t_loop)
        wave += 0.35 * a * envelope * np.sin(2 * np.pi * (f * 0.996) * t_loop)
    # 2段LFOでゆっくりした振幅のうねり（有機的な動き）
    lfo1 = 0.92 + 0.08 * np.sin(2 * np.pi * 0.028 * t_loop)
    lfo2 = 0.96 + 0.04 * np.sin(2 * np.pi * 0.019 * t_loop + 0.5)
    wave = wave * lfo1 * lfo2
    peak = np.abs(wave).max()
    if peak > 0:
        wave = wave / peak * 0.36
    n_total = int(sample_rate * duration_sec)
    n_repeat = (n_total // n_loop) + 1
    full = np.tile(wave, n_repeat)[:n_total].astype(np.float64)
    # ローパスで温かみ（カットオフ 約 750 Hz）
    nyq = sample_rate / 2.0
    cutoff = min(750.0 / nyq, 0.99)
    sos = butter(4, cutoff, btype="low", output="sos")
    full = sosfiltfilt(sos, full)
    peak = np.abs(full).max()
    if peak > 0:
        full = full / peak * 0.35
    samples = (np.clip(full, -1, 1) * 32767).astype(np.int16)
    return AudioSegment(
        data=samples.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=1,
    )


def generate_musicgen_bgm(
    duration_sec: float,
    prompt: str = "soft piano gentle strings meditation",
    model_id: str = "facebook/musicgen-small",
    sample_rate: int = 32000,
) -> "AudioSegment | None":
    """
    MusicGen（transformers）でBGMを生成する。オプション。
    利用には transformers, torch のインストールが必要。CC-BY-NC（非商用）。
    NumPy 2.x と PyTorch の互換性問題などで失敗した場合は None を返し、呼び出し元で手続き BGM にフォールバックする。
    """
    try:
        import numpy as np
        from transformers import AutoProcessor, MusicgenForConditionalGeneration
        import torch
    except ImportError:
        return None
    # NumPy 2.x と PyTorch の互換性: .numpy() が使えないと後段で RuntimeError になるため事前チェック
    try:
        torch.tensor([1.0]).numpy()
    except (RuntimeError, Exception):
        print("   MusicGen: PyTorch と NumPy の互換性がないためスキップします（numpy<2 で利用可）。")
        return None
    try:
        processor = AutoProcessor.from_pretrained(model_id)
        model = MusicgenForConditionalGeneration.from_pretrained(model_id)
        if torch.cuda.is_available():
            model = model.to("cuda")
        inputs = processor(
            text=[prompt],
            padding=True,
            return_tensors="pt",
        )
        if next(model.parameters()).is_cuda:
            inputs = {k: v.cuda() if hasattr(v, "cuda") else v for k, v in inputs.items()}
        # 約 30 秒生成（50 Hz × 30 = 1500 トークン）
        max_tokens = min(1503, int(50 * min(30, duration_sec)))
        with torch.no_grad():
            audio_values = model.generate(
                **inputs,
                do_sample=True,
                guidance_scale=3.0,
                max_new_tokens=max_tokens,
            )
        sr = model.config.audio_encoder.sampling_rate
        wav = audio_values[0, 0].float().cpu().numpy()
        wav = wav / max(np.abs(wav).max(), 1e-8) * 0.4
        n_total = int(sr * duration_sec)
        if len(wav) < n_total:
            n_rep = (n_total // len(wav)) + 1
            wav = np.tile(wav, n_rep)[:n_total]
        else:
            wav = wav[:n_total]
        from pydub import AudioSegment

        samples = (np.clip(wav, -1, 1) * 32767).astype(np.int16)
        seg = AudioSegment(
            data=samples.tobytes(),
            sample_width=2,
            frame_rate=sr,
            channels=1,
        )
        if sr != sample_rate:
            seg = seg.set_frame_rate(sample_rate)
        return seg
    except RuntimeError as e:
        if "Numpy is not available" in str(e) or "numpy" in str(e).lower():
            print("   MusicGen: PyTorch と NumPy の互換性がないためスキップします（numpy<2 で利用可）。")
        else:
            print(f"   MusicGen の生成に失敗しました: {e}")
        return None
    except Exception as e:
        print(f"   MusicGen の初期化・生成に失敗しました: {e}")
        return None


def mix_voice_with_bgm(
    voice_path: Path | str,
    output_path: Path | str,
    bgm_volume_db: float = -18.0,
    bgm_style: str = "procedural",
    bgm_prompt: str | None = None,
) -> Path:
    """
    音声ファイルにBGMを重ねて出力する。
    bgm_style: "procedural"（手続き・著作権フリー） or "musicgen"（AI・要 transformers/torch、CC-BY-NC）
    bgm_prompt: MusicGen 用のテキストプロンプト（デフォルト: soft piano gentle strings meditation）
    """
    from pydub import AudioSegment

    voice_path = Path(voice_path)
    output_path = Path(output_path)
    voice = AudioSegment.from_file(str(voice_path))
    duration_ms = len(voice)
    duration_sec = duration_ms / 1000.0
    bgm = None
    if bgm_style == "musicgen":
        bgm = generate_musicgen_bgm(
            duration_sec,
            sample_rate=voice.frame_rate,
            prompt=bgm_prompt or "soft piano gentle strings meditation",
        )
        if bgm is not None:
            print("   BGM: MusicGen で生成しました。")
    if bgm is None:
        bgm = generate_procedural_bgm(duration_sec, sample_rate=voice.frame_rate)
        if bgm_style == "musicgen":
            print("   BGM: MusicGen が使えなかったため、手続きBGMを使用しました。")
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
    podcast_image_url: str = "",
) -> Path:
    """
    /output 内の音声ファイルをエピソードとして feed.xml を生成・更新する。
    podcast_base_url: 音声ファイルの公開URLのベース（例: https://example.com/podcast）
    podcast_image_url: アートワーク画像のURL（未設定時は itunes:image を出力しない）。推奨 1400x1400 px。
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
    if podcast_image_url.strip():
        p.image = podcast_image_url.strip()

    # output 内の音声ファイルを新しい順にエピソードとして追加（feed.xml 自体は除外）
    audio_extensions = {".wav", ".mp3"}
    audio_files: list[Path] = []
    for f in output_dir.iterdir():
        if f.suffix.lower() in audio_extensions and f.name != "feed.xml":
            audio_files.append(f)
    audio_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # エピソードのサマリー用: 同一 stem の .txt があれば本文の先頭を利用（最大文字数）
    summary_max_chars = 500

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

        # 同一名の .txt から物語サマリーを設定（Podcast アプリで表示される）
        txt_path = output_dir / f"{audio_path.stem}.txt"
        if txt_path.is_file():
            try:
                raw = txt_path.read_text(encoding="utf-8")
                header = raw.split("\n\n", 1)[0] if "\n\n" in raw else raw
                body = raw.split("\n\n", 1)[1].strip() if "\n\n" in raw else raw.strip()
                summary = None
                for line in header.split("\n"):
                    line = line.strip()
                    if line.startswith("サマリー:") or line.startswith("サマリー："):
                        summary = (line.split(":", 1)[-1].split("：", 1)[-1].strip())
                        break
                if not summary:
                    summary = body[:summary_max_chars] + ("…" if len(body) > summary_max_chars else "")
                e.summary = summary
            except Exception:
                pass  # 読み込み失敗時はサマリーなしのまま

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
    speaker_id: int = 84,
    voicevox_url: str = "http://localhost:50021",
    add_bgm: bool = True,
    bgm_volume_db: float = -18.0,
    bgm_style: str = "musicgen",
    bgm_prompt: str | None = None,
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

    # サマリーを Gemini で生成（Podcast エピソード説明用）
    summary = generate_story_summary(api_key, story["title"], story["body"])
    if summary:
        print(f"   サマリー: {summary[:60]}…" if len(summary) > 60 else f"   サマリー: {summary}")

    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in story["title"])[:60]
    audio_path = output_dir / f"{safe_title}.mp3"

    # 法話テキストを .txt で保存（サマリーがあれば「サマリー:」行を追加）
    text_path = output_dir / f"{safe_title}.txt"
    header_lines = [f"タイトル: {story['title']}"]
    if summary:
        header_lines.append(f"サマリー: {summary}")
    text_path.write_text(
        "\n".join(header_lines) + "\n\n" + story["body"],
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
        mix_voice_with_bgm(
            audio_path,
            audio_path,
            bgm_volume_db=bgm_volume_db,
            bgm_style=bgm_style,
            bgm_prompt=bgm_prompt,
        )
        print(f"   BGM 付きで上書き: {audio_path}")

    podcast_title = os.environ.get("PODCAST_TITLE", "仏教説話ポッドキャスト")
    podcast_description = os.environ.get("PODCAST_DESCRIPTION", "AIが生成する仏教説話を毎日お届けします。")
    podcast_website = os.environ.get("PODCAST_WEBSITE", "")
    podcast_base_url = os.environ.get("PODCAST_BASE_URL", "")
    podcast_image_url = os.environ.get("PODCAST_IMAGE_URL", "")

    print("4. Podcast RSS を更新しています...")
    update_podcast_feed(
        output_dir,
        feed_path,
        podcast_title=podcast_title,
        podcast_description=podcast_description,
        podcast_website=podcast_website,
        podcast_base_url=podcast_base_url,
        podcast_image_url=podcast_image_url,
    )
    print(f"   保存: {feed_path}")

    print("完了しました。")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI仏教説話自動生成・Podcast配信システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python main.py  # テーマをランダムに選択
  python main.py --theme "慈悲"
  python main.py --theme "欲と知足"  # デフォルト speaker 84
  python main.py --theme "忍辱" --voicevox-url http://127.0.0.1:50021
  python main.py --list-speakers
  python main.py --merge-wav "乾いた心に降る雨"  # 分割 WAV を 1 つの MP3 に結合
  python main.py --update-feed  # feed.xml のみ再生成（PODCAST_BASE_URL 反映・iPhone 用）
  python main.py --theme "慈悲"  # デフォルトで MusicGen BGM を追加
  python main.py --theme "慈悲" --no-bgm  # BGM なし
  python main.py --theme "慈悲" --bgm-style procedural  # 手続き BGM（軽量・著作権フリー）
  python main.py --theme "慈悲" --bgm-prompt "soft piano gentle strings"  # MusicGen の雰囲気を変更
        """,
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="",
        help="今回の説話のテーマ（未指定時はランダムに選択。例: 慈悲、忍辱、知足）",
    )
    parser.add_argument(
        "--speaker",
        type=int,
        default=84,
        help="VOICEVOX のスピーカーID（デフォルト: 84）",
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
        "--no-bgm",
        action="store_true",
        help="BGM を追加しない（デフォルトは MusicGen で BGM を追加）",
    )
    parser.add_argument(
        "--bgm-volume",
        type=float,
        default=-18.0,
        metavar="DB",
        help="BGM の音量（dB）。小さいほど小さい。デフォルト: -18",
    )
    parser.add_argument(
        "--bgm-style",
        type=str,
        choices=["procedural", "musicgen"],
        default="musicgen",
        help="BGM の生成方法: musicgen=AI（デフォルト）, procedural=手続き（軽量・著作権フリー）",
    )
    parser.add_argument(
        "--bgm-prompt",
        type=str,
        default=None,
        metavar="TEXT",
        help="MusicGen 用プロンプト。未指定時は soft piano gentle strings meditation",
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
            podcast_image_url=os.environ.get("PODCAST_IMAGE_URL", ""),
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
                podcast_image_url=os.environ.get("PODCAST_IMAGE_URL", ""),
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

    theme = args.theme.strip()
    if not theme:
        theme = pick_random_theme()
        print(f"テーマ未指定のため、ランダムに選びました: 「{theme}」")

    run_pipeline(
        theme=theme,
        stories_dir=args.stories_dir,
        output_dir=args.output_dir,
        feed_path=args.output_dir / "feed.xml",
        speaker_id=args.speaker,
        voicevox_url=args.voicevox_url,
        add_bgm=not args.no_bgm,
        bgm_volume_db=args.bgm_volume,
        bgm_style=args.bgm_style,
        bgm_prompt=args.bgm_prompt,
    )


if __name__ == "__main__":
    main()
