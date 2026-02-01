# GitHub Pages に自動ホスティングする手順

ポッドキャストの `output/`（feed.xml と MP3）を GitHub Pages に自動デプロイし、iPhone などから RSS で聴けるようにする手順です。

---

## 前提

- プロジェクトを **GitHub のリポジトリ** に push していること
- ローカルで `python main.py --theme "〇〇"` を実行し、`output/` に feed.xml と MP3 ができていること
- **output をリポジトリに含める**（`.gitignore` で `output/` を除外していないこと）

---

## 1. リポジトリの用意

まだの場合:

```bash
cd /Users/yamukotonaku/projects/kouon_cast
git init
git remote add origin https://github.com/あなたのユーザー名/kouon_cast.git
```

`.gitignore` で `output/` を無視している場合は、**output をコミット対象にする**必要があります。  
（現在の `.gitignore` は output をコメントアウトしているため、output はコミットされます。）

---

## 2. PODCAST_BASE_URL を GitHub Pages の URL に合わせる

デプロイ後の URL は次の形式です。

- **ユーザー/組織サイト**: `https://ユーザー名.github.io/`
- **プロジェクトサイト**: `https://ユーザー名.github.io/リポジトリ名/`

このプロジェクトでは **output をそのままサイトルートにする**ので、**プロジェクトサイト**なら:

- サイトのルート = `https://ユーザー名.github.io/kouon_cast/`
- feed.xml = `https://ユーザー名.github.io/kouon_cast/feed.xml`
- 音声 = `https://ユーザー名.github.io/kouon_cast/〇〇.mp3`

`.env` に以下を設定します（リポジトリ名は自分のものに置き換え）:

```bash
PODCAST_BASE_URL=https://あなたのユーザー名.github.io/kouon_cast
```

設定したうえで、**一度だけ** feed.xml を再生成します。

```bash
python main.py --update-feed
```

これで `output/feed.xml` 内の音声 URL が、GitHub Pages のアドレスになります。

---

## 3. GitHub で Pages の公開元を「GitHub Actions」にする

1. GitHub でリポジトリを開く
2. **Settings** → 左の **Pages**
3. **Build and deployment** の **Source** で **GitHub Actions** を選ぶ

これで、ワークフローからデプロイする前提になります。

---

## 4. output をコミットして push する

```bash
git add output/
git status   # feed.xml と .mp3, .txt が含まれることを確認
git commit -m "Add podcast output for GitHub Pages"
git push -u origin main
```

`main` ではなく `master` を使っている場合は、`.github/workflows/deploy-pages.yml` の `branches: [main]` を `branches: [master]` に変更してください。

---

## 5. 自動デプロイの動き

- **トリガー**: `main` ブランチへの push のうち、**`output/` 以下が変わったとき**だけワークフローが動きます
- **やっていること**: `output/` をそのまま GitHub Pages の公開用アーティファクトとしてアップロードし、Pages にデプロイします
- **手動実行**: リポジトリの **Actions** タブ → 「Deploy Podcast to GitHub Pages」→ **Run workflow** でも実行できます

数分後、次の URL でサイトが公開されます。

- **https://あなたのユーザー名.github.io/kouon_cast/feed.xml**

---

## 6. 今後の更新の流れ

1. ローカルで説話を生成・音声化する  
   ```bash
   python main.py --theme "慈悲"
   ```
2. `PODCAST_BASE_URL` がすでに GitHub Pages の URL になっていれば、そのまま `output/feed.xml` も正しい URL で更新されます
3. output をコミットして push  
   ```bash
   git add output/
   git commit -m "Update podcast: 新しいエピソード"
   git push
   ```
4. 上記のワークフローが動き、数分後に GitHub Pages が更新されます

---

## 注意点

- **API キー**: `.env` は `.gitignore` に入っているため、push されません。GitHub には一切上げないでください
- **公開範囲**: output をコミットすると **feed.xml と音声ファイルがリポジトリに含まれます**。リポジトリが public なら誰でも URL を知ればアクセスできます。個人用のままにしたい場合はリポジトリを Private にし、GitHub Pages の「Private リポジトリでも Pages を有効にする」設定を利用できます（アカウントのプランによる）
- **日本語ファイル名**: feed.xml や MP3 の URL に日本語が含まれる場合、ブラウザによってはエンコードされた URL になります。多くのポッドキャストアプリは問題なく扱えます

---

## まとめ

| ステップ | 内容 |
|----------|------|
| 1 | リポジトリを用意し、output をコミット対象にする |
| 2 | `.env` に `PODCAST_BASE_URL=https://ユーザー名.github.io/リポジトリ名` を設定し、`python main.py --update-feed` で feed を更新 |
| 3 | GitHub の Settings > Pages で Source を **GitHub Actions** に設定 |
| 4 | `output/` をコミットして `main` に push |
| 5 | 数分後に `https://ユーザー名.github.io/リポジトリ名/feed.xml` で公開される |

以降は、説話を追加したら `output/` をコミットして push するだけで、自動で GitHub Pages に反映されます。
