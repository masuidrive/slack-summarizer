# ChatGPT を使って Slack の Public channel をまとめて要約するスクリプト

by [masuidrive](https://twitter.com/masuidrive) @ [Bloom&Co., Inc.](https://www.bloom-and-co.com/) 2023-
[APACHE LICENSE, 2.0](https://www.apache.org/licenses/LICENSE-2.0)

![](https://raw.githubusercontent.com/masuidrive/slack-summarizer/main/images/slack-summarized.png)

Slack の Public channel の要約を作って投稿するスクリプトです。

チャンネルが増えた組織では読むのが追いつかないことが多いため、要約を作って投稿することで、チャンネルの活動を把握しやすくすることができます。

このコードの大半も ChatGPT を使って書きました。とりあえず動くように書いただけなので、コードは雑然としています。

誰かキレイにしたら Pull Request ください。機能追加なども大歓迎です。

## How to set it up

GitHub Actions で毎日午前 5 時に動くようになっています。これ以外の環境で動かす場合は適当に頑張ってください。

### 自分の GitHub アカウントに fork する

- 右上の"Fork"ボタンを押して、自分のリポジトリに fork します
- 有料プランにするなどして GitHub Actions が実行できるようにしておきます

### 環境変数を設定する

- "Settings"タブを開き、左の"Secrets and variables"→"Actions"を開きます。
- 右上の緑の"New Repository Secret"をクリックすると環境変数が設定できるので、次の 3 つの変数を設定します。

![](https://raw.githubusercontent.com/masuidrive/slack-summarizer/main/images/github-settings.png)

#### OPEN_AI_TOKEN

- OpenAI の認証トークン
- [OpenAI の Web サイト](https://openai.com/)にアクセスしてください。
- 右上の"Sign In"ボタンをクリックし、アカウントにログインしてください。
- ページ上部の"API"メニューから、"API Key"をクリックして、API キーを生成します。
- "API Key"ページにアクセスすると、API キーが表示されます。これをコピーして Value に貼り付けます。

#### SLACK_BOT_TOKEN

- Slack の API 認証トークン
- [Slack API の Web サイト](https://api.slack.com/)にアクセスし、ログインしてください。
- "Create a new app"をクリックして、"From an app manifest"を選択し manifest に下記の内容をコピーします。

```
{"display_information":{"name":"Summary","description":"Public channelのサマリーを作る","background_color":"#d45f00"},"features":{"bot_user":{"display_name":"Summary","always_online":false}},"oauth_config":{"scopes":{"bot":["channels:history","channels:join","channels:read","chat:write","users:read"]}},"settings":{"org_deploy_enabled":true,"socket_mode_enabled":false,"token_rotation_enabled":false}}
```

- 画面左の"Install App"をクリックし、右に出る"Install App to Workspace"をクリックして、アプリをワークスペースにインストールします。インストールが完了すると、bot の OAuth アクセストークンが表示されます。
- この`xoxb-`で始まるトークンをコピーして Value に貼り付けます。

#### SLACK_POST_CHANNEL_ID

- 要約結果を投稿する Slack の channel_id
- Slack で要約結果を投稿したいチャンネルを開きます。
- 上部のチャンネル名をクリックし、出てきた Popup の最下部にある Channel ID を Value に貼り付けます。
- 次に Integrations タブを開いて、画面中段の"Add apps"を押し"Summary"を検索してインストールします。

### 実行

これらの設定をすると、毎日午前 5 時に Slack の Public channel の要約結果が投稿されます。

手動で実行してみる場合には"Actions" タブを開き、左の"Summarizer"をクリックして、右の"Run workflow"をおしてください。
