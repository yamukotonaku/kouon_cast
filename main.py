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
from datetime import datetime
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
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"  # 仏教の知識（Markdown）を置くディレクトリ
OUTPUT_DIR = PROJECT_ROOT / "output"
FEED_PATH = OUTPUT_DIR / "feed.xml"
# VOICEVOX ユーザー辞書 CSV（未指定時はこのファイルがあれば読み込んで API で登録）
VOICEVOX_USER_DICT_CSV = PROJECT_ROOT / "voicevox_user_dict.csv"

# テーマ未指定時にランダムで選ぶ候補（大テーマ × 小テーマの組み合わせ）
MAJOR_THEMES = [
    "慈悲",
    "忍辱",
    "知足",
    "無常",
    "因果",
    "布施",
    "智慧",
    "精進",
    "正念",
    "捨",
    "無我",
    "縁起",
    "中道",
    "欲と知足",
    "執着を手放す",
    "倹約と施し",
    "嫉妬と歓喜",
    "別離と受け入れ",
    "師弟と継承",
    "最期と遺訓",
    "不殺生と許し",
    "誠実と嘘",
    "貪りと足るを知る",
    "瞋恚と平静",
    "愚痴と感謝",
    "謙遜と傲慢",
    "忍耐と突破",
    "施しと受け取る",
    "生死と覚醒",
    "苦と解脱",
    "煩悩と菩提",
    "迷いと悟り",
    "業と報い",
    "因縁と果報",
    "空と仮",
    "方便と真実",
    "在家と出家",
    "王と乞食",
    "富と貧",
    "戒律と自由",
    "瞑想と気づき",
    "托鉢と供養",
    "無言と説法",
    "孤独とつながり",
    "老いと若さ",
    "病と癒し",
    "死と再生",
    "過去と現在",
    "希望と絶望",
    "疑いと確信",
    "争いと和合",
    "奪うと与える",
    "隠すと明かす",
    "逃げると向き合う",
    "諦めと願い",
    "言葉と沈黙",
    "形と心",
    "量と質",
    "速さとゆっくり",
    "多数と少数",
    "表と裏",
    "始まりと終わり",
    "原因と結果",
    "自力と他力",
    "在家の徳",
    "出家の覚悟",
    "俗世と聖域",
    "日常と非日常",
    "習慣と変革",
    "伝統と新しさ",
    "師と弟子",
    "親と子",
    "敵と味方",
    "主と従",
    "強者と弱者",
]
# 小テーマ: シチュエーション・状況（抽象的で多様な説話に展開しやすい）
MINOR_THEMES = [
    "旅の途中で見知らぬ者に出会う",
    "雨の日、誰かに傘を差す／差される",
    "川の向こう岸に渡りたいが舟がない",
    "灯りを消した部屋で一人、考える",
    "一粒の米を誰かと分ける",
    "老いた者と若い者が同じ問いを抱える",
    "沈黙のうちに何かが伝わる",
    "子供に「なぜ？」と問われる",
    "病に伏した者を傍で看る",
    "財を失い、何も持たずに旅立つ",
    "裏切った者、あるいは裏切られた者",
    "許しを乞う側と許す側",
    "別れの時、言い残したことがある",
    "再会の時、相手はもう別人だった",
    "決断を迫られ、一夜考える",
    "最後の一膳を分けるか独りで食うか",
    "誰も見ていないところで手を差し伸べる",
    "群衆の中にいて、ふと孤独を覚える",
    "一人、荒野や川辺で足を止める",
    "木陰で休んでいると声をかけられる",
    "門の前で待ち続ける",
    "扉を叩く者と、開けるか開けないか",
    "招かれざる客が訪ねてくる",
    "忘れていた約束を誰かが覚えていた",
    "やり直しのきかない一言を吐いてしまう",
    "遅すぎた気づき",
    "見返りを求めずに与える",
    "受け取ることに罪悪感を覚える",
    "争いの仲裁を頼まれる",
    "王の前に立つ／乞食の隣に座る",
    "市場で値切る、あるいは値切られる",
    "夜明け前に起き、誰も起きていない",
    "嵐の前の静けさ",
    "収穫の秋、取り損ねた実",
    "種をまいたが芽が出ない",
    "冬の夜、炉辺で昔話を聞く",
    "死者を送り、残された者たち",
    "盗みを働いた者が自ら名乗り出る",
    "嘘が露見する瞬間",
    "恩返しをしようとして、逆に恩を着せる",
    "取り返しのつかない過ちを犯した者",
    "初めて後悔を知る",
    "最後のチャンスだと言われる",
    "「もう遅い」と言われてなお動く",
    "空の茶碗を差し出される",
    "壊れたものを直すか、捨てるか",
    "道に迷い、誰かに道を聞く",
    "川は流れ続ける、自分は止まっている",
    "火事から逃げるように家を出る",
    "井戸の底から見上げる空",
    "二本の道、どちらを選ぶか",
    "名もなき者として通り過ぎる",
    "役目を終えた者が去っていく",
    "新しい役目を押し付けられる",
    "手放したはずのものが手元に残る",
    "届かない声に耳を澄ます",
    "同じ過ちを繰り返す者",
    "初めての施し／初めての乞い",
    "最後の言葉を言い残せなかった",
    "誰かの死の床で問われる",
    "一人でいるときに訪れる気づき",
    "朝、最初に口にする言葉",
    "夕暮れ、帰る場所がない",
    "橋の上で行き交う者と目が合う",
    "祭りの翌朝、静まり返った町",
    "借りたものを返しに行く",
    "届けたい手紙を握りしめたまま",
    "断りきれずに引き受けた頼み",
    "笑顔で嘘をついている自分に気づく",
    "誰かの涙を拭う／拭ってもらう",
    "同じ釜の飯を食った者と再会する",
    "恩人に会いたいが、すでにいない",
    "言い訳を考えているうちに時が過ぎる",
    "土壇場で選択を迫られる",
    "逃げ道を塞がれ、正面から向き合う",
    "褒められて戸惑う",
    "批判されて初めて気づく",
    "無視された痛み",
    "たった一人が味方でいてくれた",
    "群れから外れた一匹",
    "先頭を歩く重さ",
    "最後尾で見送る役目",
    "鍵をなくす／鍵を渡される",
    "扉が開いたままになっている",
    "消えかけた灯りをともし続ける",
    "名前を呼ばれて振り向く",
    "名前を忘れられていた",
    "約束の場所に誰もいない",
    "遅れてきた者がすべてを知っている",
    "早すぎた訪問",
    "断られ続けて、なお扉を叩く",
    "中から鍵をかけて、出てこない",
    "外から鍵をかけられ、中にいる",
    "壁に耳あり、と知ってから話す",
    "誰もいないと思って本音を漏らす",
    "見ているつもりが、見られていた",
    "助けを求める声が届かない",
    "助けを求めずに倒れる",
    "与えすぎて、自分が空になる",
    "受け取りすぎて、重荷に気づく",
    "分かち合うべきものを独り占めした",
    "分け与えたつもりが、奪っていた",
    "正しいことをしたと信じていた",
    "間違っていたと認める瞬間",
    "謝罪を待っている側と、言えない側",
    "許すと言いながら、忘れられない",
    "忘れたころに、報いが訪れる",
    "期待せずに蒔いた種が実る",
    "大切にしたものが、形を変えて返る",
    "手放したものが、別の形で手元に",
    "失ったものの重さを、初めて知る",
    "持っていたことすら忘れていた",
    "探していたものが、最初からそこにあった",
    "遠くを歩いて、元の場所に戻る",
    "同じ日を繰り返している気がする",
    "一日だけ、すべてが変わる",
    "朝起きたら、世界が違って見えた",
    "眠れない夜、窓の外を見つめる",
    "夢うつつで、誰かの声を聞く",
    "目覚めて、誰もいない",
    "最後に残った者が、灯りを消す",
    "最初に来た者が、席を温める",
    "順番を待っている間に、番が過ぎる",
    "譲った席を、誰かが埋める",
    "空いた席に、座るか座らないか",
    "隣に誰かが座ってくる",
    "隣の席が、ずっと空いている",
    "声をかけるか、見ないふりをするか",
    "声をかけられて、答えに困る",
    "答えを探しているうちに、問いが変わる",
]


def pick_random_theme() -> str:
    """テーマ未指定時に、大テーマと小テーマを組み合わせたランダムなテーマを返す。"""
    major = random.choice(MAJOR_THEMES)
    minor = random.choice(MINOR_THEMES)
    return f"{major} — {minor}"


# MusicGen の --bgm-prompt 未指定時にランダムで選ぶ候補（説話BGM向け・落ち着いた雰囲気）
BGM_PROMPTS = [
    "soft piano gentle strings meditation",
    "calm ambient meditation peaceful pad no drums",
    "harp and flute peaceful contemplative",
    "soft strings pad ambient meditation",
    "gentle piano ambient calm no percussion",
    "bells and pad soft meditation",
    "acoustic guitar fingerpicking calm peaceful",
    "soft synth pad ambient contemplative",
    "flute and strings peaceful meditation",
    "piano and cello gentle contemplative",
    "wind chimes soft pad ambient",
    "ethnic bamboo flute calm meditation",
    "soft organ pad peaceful no drums",
    "marimba and strings gentle ambient",
    "kalimba and pad calm meditation",
]


def pick_random_bgm_prompt() -> str:
    """--bgm-prompt 未指定時に使うランダムな MusicGen プロンプトを返す。"""
    return random.choice(BGM_PROMPTS)


# ---------------------------------------------------------------------------
# 1. テキスト集約ロジック
# ---------------------------------------------------------------------------


def load_stories_text(stories_dir: Path | str) -> str:
    """
    /stories フォルダ内のすべての .txt ファイルを読み込み、
    一つの大きなテキストブロックとして結合する。
    （下位互換用。説話生成のコンテキストは load_story_context を使用する。）
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


def load_story_context(
    stories_dir: Path | str,
    output_dir: Path | str,
    output_random_n: int = 5,
    stories_random_n: int = 5,
) -> str:
    """
    説話生成用のコンテキストを組み立てる。
    - output_dir 内の .txt からランダムに最大 output_random_n 個
    - stories_dir 内の .txt からランダムに最大 stories_random_n 個
    を読み、結合して返す。
    """
    output_dir = Path(output_dir)
    stories_dir = Path(stories_dir)
    blocks: list[str] = []

    # output/*.txt からランダムに output_random_n 個
    if output_dir.is_dir():
        output_list = list(output_dir.glob("*.txt"))
        if output_list:
            n = min(output_random_n, len(output_list))
            output_txts = random.sample(output_list, n)
        else:
            output_txts = []
        for path in output_txts:
            try:
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    blocks.append(text)
            except Exception as e:
                print(f"警告: {path} の読み込みに失敗しました: {e}")

    # stories/*.txt からランダムに stories_random_n 個
    if stories_dir.is_dir():
        stories_list = list(stories_dir.glob("*.txt"))
        if stories_list:
            n = min(stories_random_n, len(stories_list))
            for path in random.sample(stories_list, n):
                try:
                    text = path.read_text(encoding="utf-8").strip()
                    if text:
                        blocks.append(text)
                except Exception as e:
                    print(f"警告: {path} の読み込みに失敗しました: {e}")

    return "\n\n---\n\n".join(blocks) if blocks else ""


def load_knowledge_text(knowledge_dir: Path | str) -> str:
    """
    knowledge/ フォルダ内のすべての .md ファイルを読み込み、
    一つのテキストブロックとして結合する。説話生成時に仏教の知識としてプロンプトに渡す。
    """
    knowledge_dir = Path(knowledge_dir)
    if not knowledge_dir.is_dir():
        return ""

    blocks: list[str] = []
    for path in sorted(knowledge_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                blocks.append(text)
        except Exception as e:
            print(f"警告: {path} の読み込みに失敗しました: {e}")

    return "\n\n---\n\n".join(blocks) if blocks else ""


# ---------------------------------------------------------------------------
# 2. 説話生成ロジック（Gemini / Ollama 共通プロンプト）
# ---------------------------------------------------------------------------

STORY_SYSTEM_INSTRUCTION = """あなたは仏教説話の編纂者です。
与えられた既存の説話集と仏教の知識を踏まえ、同じトーン・文体・教訓の流れで新しい説話を創作してください。仏教の知識（教義・用語・故事など）を活用し、説話に深みと教養を反映してください。
出力は音声合成（TTS）に適するよう、ルビや振り仮名は一切付けず、句読点を適切に打ってください。
必ず「タイトル」と「本文」の2つだけを、以下の形式で出力してください。余計な説明は不要です。

【意外性・構成の多様化】説話には、聞き手が「なるほど」「意外だ」と感じるようなひねりや視点の転換を織り交ぜてください。参考コンテキストに載っている説話と似た展開・結末・構成にならないよう、予想外の登場人物（泥棒、子ども、動物、名もなき老人、異なる職業の者など）、逆説的な結末、身近な比喩や意外な対比を選び、印象に残る意外性を出してください。話の構成も大胆に変えてよく、例えば「冒頭で結末を匂わせる」「悪役や傍観者が気づきの中心になる」「修行が寺ではなく路上や労働の場で行われる」など、既存説話と被らない流れにしてください。古典の枠を守りつつ、毎回ワンパターンにならないよう心がけてください。

【職業・固有名詞の重複回避】参考コンテキスト（既存の説話集）にすでに登場している職業・立場・人名・地名は極力使わないでください。木工師・陶工・書記官・染物師・石工などが既出なら、農民、漁師、船頭、樵、鍛冶屋、楽師、医者、旅の商人、托鉢僧、王の側近、孤児、病人、名もなき老婆、猟師、筆写生、庭師、香商人など、まだ出ていない職業・立場を選んでください。人名・地名も既出と重複しないよう、インド風以外の名前や架空の国名・町名を交え、多様にしてください。

【仏教知識の重複回避】説話で用いる仏教の教義・用語・故事は、参考コンテキストの既存説話で既に使われているものと重複させないでください。知識リストから、今回まだ誰も取り上げていない概念・用語（例：縁起、四諦、六波羅蜜、無常、無我、慈悲、忍辱、布施、禅定、不浄観、白骨観、因縁、業、中道、空、 etc.）を選び、その説話ならではの教えとして深く掘り下げてください。毎回「同じ教えの言い換え」にならないよう、大胆に別の切り口を選んでください。

【修行内容の重複回避・大胆なアレンジ】説話には必ず修行のパートを含めますが、修行の「中身」は既存説話と被らせないでください。参考コンテキストで既に描かれた修行（例：坐禅、念仏、観想だけ）を繰り返さず、今回だけの修行を選んでください。例：写経、歩行禅（経行）、托鉢、施食・給仕、礼拝・巡礼、読経、作務（掃除・炊事・農作業）、懺悔、不浄観・白骨観、慈悲の観想（慈悲观）、無常観、因縁の観察、断食、沈黙修行、問答・公案、難行苦行、日常労働そのものを修行とする等。舞台も「寺で坐禅」に頼らず、路上・市場・牢・王宮・旅の途中・病人の傍らなど大胆に変え、僧侶が一人の師であっても複数であったり、老婆や子どもが「師」の役を果たすような逆転も可とします。

【ブッダの登場】ブッダを直接的であるにせよ間接的であるにせよ、必ず登場させてください。直接の対話・説法、あるいは弟子や教えを通じた言及・逸話の形でも構いません。

【分量】本文はたっぷりの長さで書いてください。目安として2000字以上3500字程度（音声で約15分〜20分になる分量。短い説話の2〜2.5倍の長さ）とし、情景・登場人物の心の動き・対話・教訓が伝わるよう、丁寧にゆったりと展開してください。エピソードを増やしたり、会話や内心描写を厚くして、読み応えのある説話にしてください。

【タイトル】説話のタイトルは、聞き手が「この話を聴くと何に役立つか」「どう心が変わるか」が端的に伝わるようにしてください。how-to 的・ベネフィット重視で、多少煽り気味でも構いません。抽象的・詩的な表現より、「〇〇が軽くなる」「〇〇を手放す」「〇〇が変わる」のように、得られる効果や変化が分かる表現を選んでください。長すぎず、15字〜25字程度を目安に。例：「嫉妬が消える、一粒の米」「怒りを手放す、最後の一椀」「聴くだけで心が軽くなる、旅人の選択」「欲ばりが報われない、三人の願い」。

形式:
タイトル: （ここに説話のタイトルを1行で。上記【タイトル】の指示に従う）
本文:
（ここに説話の本文を書く。段落は空行で区切る）
"""


def _build_story_prompt(
    context: str,
    theme: str,
    knowledge_context: str = "",
    context_max: int = 400000,
    knowledge_max: int = 100000,
) -> str:
    """説話生成用のユーザープロンプトを組み立てる。Gemini / Ollama 共通。"""
    context_truncated = (context[:context_max] if context else "（説話がまだ登録されていません。一般的な仏教説話のスタイルで創作してください。）")
    knowledge_truncated = (knowledge_context[:knowledge_max] if knowledge_context else "")
    return f"""【既存の説話集（参考コンテキスト）】
{context_truncated}

【仏教の知識（参考・活用すること）】
{knowledge_truncated if knowledge_truncated else "（追加の知識はありません。一般的な仏教の教えを踏まえて創作してください。）"}

【今回のテーマ】
{theme}

上記テーマに沿い、説話集と仏教の知識を活用した新しい説話を1本、創作してください。必ず「修行パート」と「ブッダの登場」（直接・間接どちらでも可）を含めてください。

重要（重複回避・大胆なアレンジ）:
- 職業・人名・地名は既存説話と被らせないこと。
- 用いる仏教の教え・用語・故事は、既存説話で既に使われているものと重複させず、知識リストから別の概念を選ぶこと。
- 修行の「内容」と「舞台」を既存説話と変えること（坐禅・念仏・観想の繰り返しにせず、写経・歩行禅・托鉢・作務・慈悲観・巡礼・問答など、今回だけの修行を選び、場所も寺以外に広げてよい）。
- 話の流れや登場人物の役割に大胆なアレンジを加え、ワンパターンにならないこと。

説話の本文は、音声で約15分〜20分になる長さ（目安: 2000字〜3500字）で、情景・対話・教訓が伝わるよう丁寧にゆったりと書いてください。タイトルは【タイトル】の指示に従い、「聴くと何に役立つか」が伝わるベネフィット重視の表現にしてください。"""


def generate_story(
    api_key: str,
    context: str,
    theme: str,
    knowledge_context: str = "",
) -> dict[str, str]:
    """
    仏教説話の編纂者として、コンテキスト・テーマ・仏教の知識から新説話を生成する（Gemini 使用）。
    戻り値: {"title": "タイトル", "body": "本文"}
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = _build_story_prompt(context, theme, knowledge_context)

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=STORY_SYSTEM_INSTRUCTION,
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


def generate_story_ollama(
    base_url: str = "http://localhost:11434",
    model: str = "llama3.2",
    context: str = "",
    theme: str = "",
    knowledge_context: str = "",
    context_max: int = 100000,
    knowledge_max: int = 50000,
    connect_timeout: int = 15,
    read_timeout: int = 600,
) -> dict[str, str]:
    """
    仏教説話の編纂者として、コンテキスト・テーマ・仏教の知識から新説話を生成する（Ollama 使用）。
    戻り値: {"title": "タイトル", "body": "本文"}
    """
    import requests

    prompt = _build_story_prompt(
        context, theme, knowledge_context,
        context_max=context_max,
        knowledge_max=knowledge_max,
    )
    url = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": STORY_SYSTEM_INSTRUCTION,
        "stream": False,
        "options": {"temperature": 0.8, "num_predict": 8192},
    }
    try:
        r = requests.post(
            url,
            json=payload,
            timeout=(connect_timeout, read_timeout),
        )
    except requests.exceptions.ConnectTimeout as e:
        raise RuntimeError(
            f"Ollama への接続がタイムアウトしました（{connect_timeout}秒）。"
            f" --ollama-url のホストが起動しているか、ファイアウォールやネットワークを確認してください。URL: {url}"
        ) from e
    except requests.exceptions.ConnectionError as e:
        msg = (
            f"Ollama に接続できません（接続拒否）。URL: {url}\n"
            "  - Ollama を起動していますか？（例: ターミナルで ollama serve）\n"
            "  - ポートは合っていますか？Ollama の既定は 11434 です（--ollama-url http://localhost:11434）"
        )
        raise RuntimeError(msg) from e
    r.raise_for_status()
    data = r.json()
    text = (data.get("response") or "").strip()
    if not text:
        raise RuntimeError("Ollama が空の応答を返しました。モデルやコンテキスト長を確認してください。")
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
    """Gemini / Ollama の応答から「タイトル」と「本文」を抽出する。"""
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
    if not body:
        body = text.strip()

    # 「タイトル:」行が無い場合（Ollama が ## 【…】 形式で返す場合）、先頭行からタイトルを抽出
    if not title and body:
        first_line = body.split("\n")[0].strip()
        if first_line.startswith("## ") and "【" in first_line and "】" in first_line:
            title = first_line.replace("## ", "", 1).strip()
            rest_lines = body.split("\n")[1:]
            body = "\n".join(rest_lines).strip()
        elif first_line.startswith("## "):
            title = first_line.replace("## ", "", 1).strip()
            rest_lines = body.split("\n")[1:]
            body = "\n".join(rest_lines).strip()

    if not title:
        title = "説話"
    return {"title": title, "body": body}


def generate_story_summary(api_key: str, title: str, body: str) -> str:
    """
    説話のタイトルと本文から、Podcast エピソード説明用の短いサマリーを Gemini で生成する。
    戻り値: 2〜3文の要約（失敗時は空文字）
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    prompt = f"""以下の仏教説話の「導入・状況説明」だけを、2〜3文で書いてください。

【条件】
- 物語の結末・オチは一切含めないでください。
- 誰がどんな状況にいるか、何が問われているかだけを簡潔に書き、聴き手が「続きが気になる」ような仕上がりにしてください。
- Podcast のエピソード説明に使うため、ネタバレせず興味を引く書き方にしてください。
- 余計な前置きや「要約は以下の通りです」などの説明は不要です。要約文だけを出力してください。

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


def load_and_register_voicevox_user_dict(
    csv_path: Path | str | None,
    base_url: str = "http://localhost:50021",
) -> int:
    """
    voicevox_user_dict.csv を読み、VOICEVOX Engine API のユーザー辞書に一括登録する。
    CSV 形式: 表記,読み(カタカナ/ひらがな),アクセント型[,優先度]
    区切りはカンマまたはパイプ。1 行目はヘッダー可（表示名,読み仮名,アクセント型 など）。
    ファイルが存在しない場合は何もせず 0 を返す。
    登録できた単語数を返す。
    """
    import csv as csv_module
    import requests

    path = Path(csv_path) if csv_path else None
    if not path or not path.is_file():
        return 0

    # 区切りを推定（最初の行でカンマかパイプか）
    raw = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        return 0

    delimiter = "|" if "|" in lines[0] else ","
    reader = csv_module.reader(lines, delimiter=delimiter)
    rows = list(reader)
    if not rows:
        return 0

    # ヘッダー行なら飛ばす（表示名 / surface / 読み仮名 などで判定）
    start = 0
    if len(rows[0]) >= 3 and rows[0][0].strip() in ("表示名", "surface", "表記", "単語"):
        start = 1

    count = 0
    for i in range(start, len(rows)):
        row = [c.strip() for c in rows[i]]
        if len(row) < 3:
            continue
        surface, pronunciation, accent_s = row[0], row[1], row[2]
        if not surface or not pronunciation:
            continue
        try:
            accent_type = int(accent_s)
        except ValueError:
            continue
        priority = 5
        if len(row) >= 4 and row[3].strip().isdigit():
            priority = max(1, min(10, int(row[3].strip())))

        try:
            r = requests.post(
                f"{base_url}/user_dict_word",
                params={
                    "surface": surface,
                    "pronunciation": pronunciation,
                    "accent_type": accent_type,
                    "priority": priority,
                },
                timeout=10,
            )
            if r.status_code in (200, 201):
                count += 1
            else:
                print(f"   辞書登録スキップ: {surface} ({r.status_code})", file=sys.stderr)
        except requests.RequestException as e:
            print(f"   ユーザー辞書登録でエラー: {e}", file=sys.stderr)
            break
    return count


def _apply_voicevox_speed(audio_query: dict, speed_scale: float) -> None:
    """
    audio_query を破壊的に編集する。speedScale で読み上げ速度を調整する。
    speed_scale: 1.0 が標準。0.87 で約15%遅く。
    """
    key_speed = "speedScale" if "speedScale" in audio_query else "speed_scale"
    if key_speed in audio_query:
        audio_query[key_speed] = speed_scale


def text_to_speech(
    text: str,
    output_path: Path | str,
    speaker_id: int = 1,
    base_url: str = "http://localhost:50021",
    speed_scale: float = 0.87,
    sentence_break_ms: float = 500.0,
) -> Path:
    """
    テキストを VOICEVOX API で音声合成し、分割 WAV を結合して 1 つの MP3 に保存する。
    長文の場合は句点で分割して複数リクエストし、pydub で結合して MP3 出力する。
    speed_scale: 1.0 が標準。0.87 で約15%遅く。
    sentence_break_ms: 句点「。」で区切った区間のあいだに挿入する無音の長さ（ミリ秒）。「、」のポーズは変更しない。
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
    try:
        for part in parts:
            if not part.strip():
                continue
            query_url = f"{base_url}/audio_query"
            synthesis_url = f"{base_url}/synthesis"
            params = {"text": part, "speaker": speaker_id}
            q = requests.post(query_url, params=params, timeout=30)
            q.raise_for_status()
            audio_query = q.json()
            _apply_voicevox_speed(audio_query, speed_scale=speed_scale)
            syn = requests.post(
                synthesis_url,
                params={"speaker": speaker_id},
                json=audio_query,
                timeout=60,
            )
            syn.raise_for_status()
            wav_chunks.append(syn.content)
    except requests.exceptions.ConnectionError as e:
        msg = (
            f"VOICEVOX に接続できません（接続拒否）。\n"
            f"  VOICEVOX Engine は起動していますか？ 既定のポートは 50021 です。\n"
            f"  指定している URL: {base_url}\n"
            f"  ネットワークや --voicevox-url の設定を確認してください。"
        )
        print(msg, file=sys.stderr)
        raise SystemExit(1) from e

    if not wav_chunks:
        raise ValueError("音声データが生成されませんでした。")

    # 全 WAV チャンクを結合。区間のあいだ（句点の後）に無音を挿入して「。」のブレークを長くする
    segments = [
        AudioSegment.from_file(io.BytesIO(chunk), format="wav")
        for chunk in wav_chunks
    ]
    if len(segments) == 1:
        combined = segments[0]
    else:
        silence = AudioSegment.silent(duration=int(sentence_break_ms))
        combined = segments[0]
        for seg in segments[1:]:
            combined = combined + silence + seg
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
    bgm_volume_db: float = -14.0,
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
    podcast_title: str = "香音キャスト 〜聴くだけで心が整う。仏教説話を音で〜",
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

    # エピソード説明用: 「サマリー:」が無い場合は本文冒頭をフォールバック（description を必ず出す）
    summary_fallback_chars = 500

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

        # 同一名の .txt から物語サマリーを設定（Podcast の description に表示される）
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
                # Gemini 要約を優先。無い場合は本文冒頭をフォールバックして description を必ず出す
                if not summary and body:
                    summary = body[:summary_fallback_chars] + ("…" if len(body) > summary_fallback_chars else "")
                if summary:
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
    knowledge_dir: Path | str = KNOWLEDGE_DIR,
    output_dir: Path | str = OUTPUT_DIR,
    feed_path: Path | str = FEED_PATH,
    speaker_id: int = 9,
    voicevox_url: str = "http://localhost:50021",
    user_dict_csv: Path | str | None = None,
    story_llm: str = "gemini",
    ollama_url: str = "http://localhost:11434",
    ollama_model: str = "llama3.2",
    add_bgm: bool = True,
    bgm_volume_db: float = -14.0,
    bgm_style: str = "musicgen",
    bgm_prompt: str | None = None,
) -> None:
    """説話生成 → 音声化 → RSS 更新まで一括実行する。"""
    if story_llm == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("環境変数 GEMINI_API_KEY が設定されていません。.env を確認してください。", file=sys.stderr)
            sys.exit(1)
    else:
        api_key = None

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # デフォルト: output 内の分割 WAV を 1 本の MP3 に結合する
    merge_all_split_wavs_in_dir(output_dir)

    print("1. 説話テキストと仏教の知識を読み込んでいます...")
    context = load_story_context(
        stories_dir,
        output_dir,
        output_random_n=5,
        stories_random_n=5,
    )
    knowledge_context = load_knowledge_text(knowledge_dir)
    print(f"   説話: {len(context)} 文字 / 知識: {len(knowledge_context)} 文字")

    if story_llm == "ollama":
        print(f"2. Ollama（{ollama_model}）で説話を生成しています...")
        story = generate_story_ollama(
            base_url=ollama_url,
            model=ollama_model,
            context=context,
            theme=theme,
            knowledge_context=knowledge_context,
        )
        summary = (story["body"][:400].strip() + ("…" if len(story["body"]) > 400 else "")) if story.get("body") else ""
    else:
        print("2. Gemini で説話を生成しています...")
        story = generate_story(api_key, context, theme, knowledge_context=knowledge_context)
        summary = generate_story_summary(api_key, story["title"], story["body"])
        if not summary and story["body"]:
            summary = story["body"][:400].strip() + ("…" if len(story["body"]) > 400 else "")

    print(f"   タイトル: {story['title']}")
    if summary:
        print(f"   サマリー: {summary[:60]}…" if len(summary) > 60 else f"   サマリー: {summary}")

    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in story["title"])[:60]
    date_str = datetime.now().strftime("%Y.%m.%d")
    base_name = f"{date_str}_{safe_title}"
    audio_path = output_dir / f"{base_name}.mp3"

    # 法話テキストを .txt で保存（要約を「サマリー:」行として埋め込み → feed.xml の description に出力）
    text_path = output_dir / f"{base_name}.txt"
    header_lines = [f"タイトル: {story['title']}"]
    if summary:
        header_lines.append(f"サマリー: {summary}")
    text_path.write_text(
        "\n".join(header_lines) + "\n\n" + story["body"],
        encoding="utf-8",
    )
    print(f"   テキスト保存: {text_path}")

    # ユーザー辞書 CSV があれば VOICEVOX に登録（音声化の直前に実行）
    csv_to_load = Path(user_dict_csv) if user_dict_csv is not None else VOICEVOX_USER_DICT_CSV
    n = load_and_register_voicevox_user_dict(csv_to_load, base_url=voicevox_url)
    if n > 0:
        print(f"   VOICEVOX ユーザー辞書: {n} 語を登録しました。")

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
        if bgm_style == "musicgen" and bgm_prompt is None:
            bgm_prompt = pick_random_bgm_prompt()
            print(f"   BGM プロンプト: {bgm_prompt}")
        mix_voice_with_bgm(
            audio_path,
            audio_path,
            bgm_volume_db=bgm_volume_db,
            bgm_style=bgm_style,
            bgm_prompt=bgm_prompt,
        )
        print(f"   BGM 付きで上書き: {audio_path}")

    podcast_title = os.environ.get("PODCAST_TITLE", "香音キャスト 〜聴くだけで心が整う。仏教説話を音で〜")
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
  python main.py --theme "欲と知足"  # デフォルト speaker 9
  python main.py --theme "忍辱" --voicevox-url http://127.0.0.1:50021
  python main.py --list-speakers
  python main.py --merge-wav "乾いた心に降る雨"  # 分割 WAV を 1 つの MP3 に結合
  python main.py --update-feed  # feed.xml のみ再生成（PODCAST_BASE_URL 反映・iPhone 用）
  python main.py --theme "慈悲"  # デフォルトで MusicGen BGM を追加
  python main.py --theme "慈悲" --no-bgm  # BGM なし
  python main.py --theme "慈悲" --bgm-style procedural  # 手続き BGM（軽量・著作権フリー）
  python main.py --theme "慈悲" --bgm-prompt "soft piano gentle strings"  # MusicGen の雰囲気を変更
  python main.py --story-llm ollama --ollama-model llama3.2  # 説話生成をローカル Ollama で実行
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
        default=9,
        help="VOICEVOX のスピーカーID（デフォルト: 9）",
    )
    parser.add_argument(
        "--voicevox-url",
        type=str,
        default="http://localhost:50021",
        help="VOICEVOX Engine の URL（デフォルト: http://localhost:50021）",
    )
    parser.add_argument(
        "--voicevox-user-dict",
        type=Path,
        default=None,
        metavar="CSV",
        help="VOICEVOX ユーザー辞書用 CSV（表記,読み,アクセント型[,優先度]）。未指定時は voicevox_user_dict.csv があれば使用",
    )
    parser.add_argument(
        "--story-llm",
        type=str,
        choices=["gemini", "ollama"],
        default="gemini",
        help="説話生成に使う LLM: gemini（デフォルト）, ollama（ローカル）",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Ollama API の URL（--story-llm ollama 時。デフォルト: http://localhost:11434）",
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="llama3.2",
        metavar="MODEL",
        help="Ollama のモデル名（--story-llm ollama 時。デフォルト: llama3.2）",
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
        default=-14.0,
        metavar="DB",
        help="BGM の音量（dB）。小さいほど小さい。デフォルト: -14",
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
        help="MusicGen 用プロンプト。未指定時は候補からランダムに選択",
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
            podcast_title=os.environ.get("PODCAST_TITLE", "香音キャスト 〜聴くだけで心が整う。仏教説話を音で〜"),
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
                podcast_title=os.environ.get("PODCAST_TITLE", "香音キャスト 〜聴くだけで心が整う。仏教説話を音で〜"),
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
        knowledge_dir=getattr(args, "knowledge_dir", KNOWLEDGE_DIR),
        output_dir=args.output_dir,
        feed_path=args.output_dir / "feed.xml",
        speaker_id=args.speaker,
        voicevox_url=args.voicevox_url,
        user_dict_csv=args.voicevox_user_dict,
        story_llm=args.story_llm,
        ollama_url=args.ollama_url,
        ollama_model=args.ollama_model,
        add_bgm=not args.no_bgm,
        bgm_volume_db=args.bgm_volume,
        bgm_style=args.bgm_style,
        bgm_prompt=args.bgm_prompt,
    )


if __name__ == "__main__":
    main()
