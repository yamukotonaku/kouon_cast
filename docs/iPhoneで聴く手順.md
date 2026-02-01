# iPhone で法話ポッドキャストを聴く手順

現在の `feed.xml` は `file://` の URL のため、iPhone の「ポッドキャスト」アプリからは聴けません。  
**RSS と音声ファイルを HTTP/HTTPS の URL で公開する**必要があります。

---

## 方法 A: 静的ホスティングで公開する（推奨）

RSS と MP3 を Web 上に置き、iPhone の「ポッドキャスト」アプリでフィードを登録します。

### 1. output フォルダを公開する

次のいずれかで、`output` フォルダの中身を Web にアップロードします。

| 方法 | 例 | 備考 |
|------|-----|------|
| **Netlify Drop** | [app.netlify.com/drop](https://app.netlify.com/drop) に `output` フォルダをドラッグ | 無料。URL は毎回変わるので、更新のたびに同じサイトにデプロイする運用にする |
| **Netlify / Vercel** | リポジトリと連携して `output` を公開ディレクトリに | 更新のたびに git push で再デプロイ |
| **GitHub Pages** | リポジトリの `output` を `gh-pages` で公開 | 公開リポジトリなら無料 |
| **自宅サーバー / VPS** | `output` を nginx 等のドキュメントルートに配置 | 自分用ならローカル IP でも可（方法 B に近い） |

例: Netlify でデプロイした場合、  
`https://your-site-name.netlify.app/feed.xml` が RSS の URL、  
`https://your-site-name.netlify.app/満たされぬ渇きの正体.mp3` が各エピソードの URL になります。

### 2. .env で PODCAST_BASE_URL を設定する

音声の URL を正しく出すため、公開先の「ベース URL」を設定します。

```bash
# 例: Netlify のサイト URL が https://my-buddhist-podcast.netlify.app の場合
PODCAST_BASE_URL=https://my-buddhist-podcast.netlify.app
```

先頭の `https://` を忘れずに。末尾の `/` は不要です。

### 3. feed.xml を再生成する

`.env` に `PODCAST_BASE_URL` を設定したうえで、RSS だけ更新するコマンドを実行します。

```bash
# 説話生成はせず、既存の output で feed.xml のみ再生成
python main.py --update-feed
```

生成された `output/feed.xml` を、公開しているサーバーにアップロード（またはデプロイ）し直します。

### 4. iPhone でフィードを登録する

1. iPhone で「**ポッドキャスト**」アプリを開く  
2. 「**ライブラリ**」→ 右上の「**編集**」→「**フィードを登録...**」  
3. RSS の URL を入力する  
   - 例: `https://your-site-name.netlify.app/feed.xml`  
4. 「**登録**」をタップ  

登録後、エピソード一覧が表示され、タップして再生できます。

---

## 方法 B: 同じ Wi‑Fi の Mac でサーバーを立てる（簡易・自分用）

Mac と iPhone が**同じ Wi‑Fi** にいる場合、Mac で簡易 HTTP サーバーを立て、その URL を RSS に書く方法です。  
※ Apple の「ポッドキャスト」アプリは **https** や**公的な URL** を要求することがあるため、**http** や **ローカル IP** では登録できない場合があります。そのときは Castro や Overcast など、カスタム URL 対応のアプリを試してください。

### 1. Mac で output を公開する

ターミナルで:

```bash
cd /Users/yamukotonaku/projects/kouon_cast/output
python3 -m http.server 8000
```

このままにしておくと、Mac の IP アドレス `192.168.x.x` に対して  
`http://192.168.x.x:8000/feed.xml` で RSS にアクセスできます。

### 2. .env でベース URL を設定する

```bash
# Mac の IP は ifconfig や「システム設定 → ネットワーク」で確認
PODCAST_BASE_URL=http://192.168.x.x:8000
```

### 3. feed.xml を再生成する

`.env` に `PODCAST_BASE_URL=http://192.168.x.x:8000` を設定したうえで、次を実行します。

```bash
python main.py --update-feed
```

生成された `output/feed.xml` は、そのまま Mac の http.server から `http://192.168.x.x:8000/feed.xml` で配信されます。

### 4. iPhone で聴く

- **Castro** や **Overcast** など、URL 入力でフィードを追加できるアプリをインストール  
- 「フィードを追加」などで `http://192.168.x.x:8000/feed.xml` を入力  
- 同じ Wi‑Fi 内で再生  

「ポッドキャスト」アプリで http やローカル URL が弾かれる場合は、上記サードパーティアプリを使う必要があります。

---

## まとめ

| やりたいこと | おすすめ |
|--------------|----------|
| 外出先でも聴きたい・iPhone 純正アプリで聴きたい | 方法 A（Netlify 等で HTTPS 公開） |
| 自宅の Wi‑Fi だけで聴ければよい | 方法 B（Mac で http.server + Castro/Overcast 等） |

いずれも、

1. **RSS と MP3 を URL で配る**  
2. **`.env` の `PODCAST_BASE_URL` をその URL に合わせる**  
3. **feed.xml をその設定で再生成する**  
4. **iPhone でその feed.xml の URL を登録する**  

という流れになります。
